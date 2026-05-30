"""MCP server for isolated container execution via Docker/Podman."""

from argparse import ArgumentParser
from shutil import which
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4, uuid5
from pathlib import Path
from inspect import cleandoc

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.lifespan import Lifespan
from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException

_parser = ArgumentParser(prog="mcp-cmd-sandbox")
_ = _parser.add_argument(
    "container_binary",
    nargs="*",
    default=["podman"],
    help="e.g. 'podman' or '-- docker --remote'",
)
_args = _parser.parse_args()

_SERVER_ID = uuid4()
_IS_PODMAN = "podman" in _args.container_binary[0]

# krun microVM runtime support — full kernel enables docker-compose, loop/FUSE mounts, etc.
# libkrunfw.so ships as package data in lib/; the wrapper sets LD_LIBRARY_PATH before execing krun.
_KRUN_PATH = which("krun")
_KRUN_AVAILABLE = _KRUN_PATH is not None

# The wrapper must be generated at runtime with the absolute krun path baked in because:
# - the OCI runtime is invoked with a minimal PATH.
# - there is no way to pass data to the wrapper script.
if _KRUN_AVAILABLE:
    _lib_dir = Path(__file__).parent / "lib"

    with NamedTemporaryFile(
        mode="w", prefix="krun-wrapper-", delete=False
    ) as wrapper_file:
        _ = wrapper_file.write(
            cleandoc(f"""
            #!/bin/sh
            export LD_LIBRARY_PATH="{_lib_dir}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}"
            exec '{_KRUN_PATH}' "$@"
            """)
        )
        _KRUN_WRAPPER = Path(wrapper_file.name)
    _KRUN_WRAPPER.chmod(0o755)

volumes: dict[UUID, str] = {}
client = DockerClient(client_call=_args.container_binary)


# This cleans up the anonymous volumes created during the runtime of the mcp server
@Lifespan
async def remove_sessions(_):
    # startup
    yield

    # shutdown
    # delete all created anonymous volumes
    for vol in volumes.values():
        try:
            client.volume.remove(vol)
        except Exception:
            pass

    # delete the krun wrapper
    if _KRUN_AVAILABLE:
        _KRUN_WRAPPER.unlink(missing_ok=True)


def get_session_volume(ctx: Context):
    id = uuid5(_SERVER_ID, ctx.session_id)
    volume_name = f"mcp-cmd-sandbox-persistant-{id}"

    if id not in volumes.keys():
        _ = client.volume.create(volume_name)
        volumes[id] = volume_name

    return volume_name


mcp = FastMCP("mcp-cmd-sandbox", lifespan=remove_sessions)


def _run_cmd(
    command: str, image: str, writable: bool, vm: bool, ctx: Context
) -> dict[str, str | int]:
    assert not vm or _KRUN_AVAILABLE, (
        "`vm=True` should only be used when krun is available"
    )

    volume = get_session_volume(ctx)
    # TODO: this is sketchy af.
    # this should be the pwd of the agent tool, not the mcp server
    cwd = str(Path.cwd())

    try:
        with client.run(
            image,
            ["-c", command],
            entrypoint="/bin/sh",
            volumes=[
                (
                    cwd,
                    "/workspace",
                    "rw" if writable else ("O" if _IS_PODMAN else "ro"),
                ),
                (volume, "/persistent", "rw"),
            ],
            workdir="/workspace",
            detach=True,
            runtime=str(_KRUN_WRAPPER) if vm else None,
        ) as container:
            exit_code = client.wait(container)
            return {"output": container.logs(), "exit_code": exit_code}

    except DockerException as e:
        return {"error": str(e)}


# Tool call descriptions embed runtime values (_IS_PODMAN, _KRUN_AVAILABLE) only known at startup,
# so they're module-level strings rather than docstrings.
_workspace_mount_mode = (
    "overlay mount, writes discarded on exit" if _IS_PODMAN else "read-only"
)
_vm_note = (
    cleandoc("""
        `vm=True` runs the container in a microVM (full kernel available).
        Only use this to run tasks a standard (rootless) container couldn't:
          - docker compose
          - loop/FUSE mounts
          - k8s

        Do not use for ordinary tasks.
    """)
    if _KRUN_AVAILABLE
    else ""
)


_execute_desc = cleandoc(f"""
    Run a command in an isolated container.

    - /workspace (active working directory, no cd necessary): project directory ({_workspace_mount_mode})
    - /persistent: writable volume that survives across calls

    Pick an image appropriate for the task:
      debian (default), rust, python, gcc, node,
      astral/uv, alpine/git, golang, maven

    Use /persistent for build caches or artifacts across multiple calls.
    See the execute_writable call for a writable workspace.

    {_vm_note}
""")

_writable_desc = cleandoc("""
    Run a command with write access to /workspace in an isolated container.

    Only use this when the modification of project files is the main goal (sed -i, applying a patch, etc).
    Do not use this when certain commands try to write as a side effect (cargo build, uv publish, etc).

    Keep commands as small as possible — only the write operation itself. Move any reads, builds, or
    checks into a separate execute call so the user can easily review what was actually modified.
""")

if _KRUN_AVAILABLE:

    @mcp.tool(description=_execute_desc)
    def execute(  # pyright: ignore[reportRedeclaration]
        command: str,
        image: str = "debian:latest",
        vm: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict[str, str | int]:
        return _run_cmd(command, image, writable=False, vm=vm, ctx=ctx)

    @mcp.tool(description=_writable_desc)
    def execute_writable(  # pyright: ignore[reportRedeclaration]
        command: str,
        image: str = "debian:latest",
        vm: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict[str, str | int]:
        return _run_cmd(command, image, writable=True, vm=vm, ctx=ctx)
else:

    @mcp.tool(description=_execute_desc)
    def execute(
        command: str, image: str = "debian:latest", ctx: Context = CurrentContext()
    ) -> dict[str, str | int]:
        return _run_cmd(command, image, writable=False, vm=False, ctx=ctx)

    @mcp.tool(description=_writable_desc)
    def execute_writable(
        command: str, image: str = "debian:latest", ctx: Context = CurrentContext()
    ) -> dict[str, str | int]:
        return _run_cmd(command, image, writable=True, vm=False, ctx=ctx)
