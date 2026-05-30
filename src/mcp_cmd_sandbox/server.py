"""MCP server for isolated container execution via Docker/Podman."""

from argparse import ArgumentParser
from pathlib import Path

from fastmcp import Context
from fastmcp.server.lifespan import Lifespan
from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException

from . import krun
from .session import Session, remove_all_sessions

_parser = ArgumentParser(prog="mcp-cmd-sandbox")
_ = _parser.add_argument(
    "container_binary",
    nargs="*",
    default=["podman"],
    help="e.g. 'podman' or '-- docker --remote'",
)
_args = _parser.parse_args()

client = DockerClient(client_call=_args.container_binary)
IS_PODMAN = "podman" in _args.container_binary[0]


def run_cmd(
    command: str, image: str, writable: bool, vm: bool, ctx: Context
) -> dict[str, str | int]:
    assert not vm or krun.AVAILABLE, (
        "`vm=True` should only be used when krun is available"
    )

    volume = Session.get(ctx, client).volume
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
                    "rw" if writable else ("O" if IS_PODMAN else "ro"),
                ),
                (volume, "/persistent", "rw"),
            ],
            workdir="/workspace",
            detach=True,
            runtime=str(krun.WRAPPER) if vm else None,
        ) as container:
            exit_code = client.wait(container)
            return {"output": container.logs().strip(), "exit_code": exit_code}

    except DockerException as e:
        return {"error": str(e)}


@Lifespan
async def cleanup(_):
    # startup
    yield

    # shutdown
    remove_all_sessions(client)

    if krun.AVAILABLE:
        krun.WRAPPER.unlink(missing_ok=True)
