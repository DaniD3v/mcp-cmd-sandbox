from inspect import cleandoc

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext

from . import krun
from .server import IS_PODMAN, run_cmd, cleanup

mcp = FastMCP("mcp-cmd-sandbox", lifespan=cleanup)

# Tool call descriptions embed runtime values (IS_PODMAN, krun.AVAILABLE) only known at startup,
# so they're module-level strings rather than docstrings.
_workspace_mount_mode = (
    "overlay mount, writes discarded on exit" if IS_PODMAN else "read-only"
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
    if krun.AVAILABLE
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

if krun.AVAILABLE:

    @mcp.tool(description=_execute_desc)
    def execute(  # pyright: ignore[reportRedeclaration]
        command: str,
        image: str = "debian:latest",
        vm: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict[str, str | int]:
        return run_cmd(command, image, writable=False, vm=vm, ctx=ctx)

    @mcp.tool(description=_writable_desc)
    def execute_writable(  # pyright: ignore[reportRedeclaration]
        command: str,
        image: str = "debian:latest",
        vm: bool = False,
        ctx: Context = CurrentContext(),
    ) -> dict[str, str | int]:
        return run_cmd(command, image, writable=True, vm=vm, ctx=ctx)

else:

    @mcp.tool(description=_execute_desc)
    def execute(
        command: str, image: str = "debian:latest", ctx: Context = CurrentContext()
    ) -> dict[str, str | int]:
        return run_cmd(command, image, writable=False, vm=False, ctx=ctx)

    @mcp.tool(description=_writable_desc)
    def execute_writable(
        command: str, image: str = "debian:latest", ctx: Context = CurrentContext()
    ) -> dict[str, str | int]:
        return run_cmd(command, image, writable=True, vm=False, ctx=ctx)
