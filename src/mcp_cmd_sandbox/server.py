"""MCP server for isolated container execution via Docker/Podman."""

import sys
import uuid
from pathlib import Path

from fastmcp import Context, FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.lifespan import Lifespan
from python_on_whales import DockerClient

_SERVER_ID = uuid.uuid4()
VOLUMES: dict[uuid.UUID, str] = {}
client = DockerClient(
    client_call=sys.argv[1:] or ["docker"]
)  # TODO document this arg / error if its not passed


# This cleans up the anonymous volumes created during the runtime of the mcp server
@Lifespan
async def remove_sessions(_):
    # startup
    yield

    # shutdown
    for vol in VOLUMES.values():
        try:
            client.volume.remove(vol)
        except Exception:
            pass


def get_session_volume(ctx: Context):
    id = uuid.uuid5(_SERVER_ID, ctx.session_id)
    volume_name = f"mcp-cmd-sandbox-persistant-{id}"

    if id not in VOLUMES.keys():
        _ = client.volume.create(volume_name)
        VOLUMES[id] = volume_name

    return volume_name


mcp = FastMCP("mcp-cmd-sandbox", lifespan=remove_sessions)


def _run_cmd(command: str, image: str, writable: bool, ctx: Context) -> str:
    volume = get_session_volume(ctx)
    mode = "rw" if writable else "ro"

    # TODO: this is sketchy af.
    # this should be the pwd of the agent tool, not the mcp server
    cwd = str(Path.cwd())

    try:
        output = client.run(
            image,
            ["sh", "-c", command],
            volumes=[(cwd, "/workspace", mode), (volume, "/persistent", "rw")],
            workdir="/workspace",
            remove=True,
        )
        return f"{output}"

    except Exception as e:
        return f"Error: {e}"  # TODO: fix to show stderr instead of exception


@mcp.tool()
def execute(
    command: str, image: str = "debian:latest", ctx: Context = CurrentContext()
) -> str:
    """Run a command in an isolated container.

    - /workspace: your project directory (READ-ONLY, working directory)
    - /persistent: writable volume that survives across calls within the same session_id

    Pick an image appropriate for the task:
      debian:latest (default), rust:latest, python:3.12-slim,
      gcc:latest, node:22-alpine, golang:latest, maven:latest

    Use /persistent for build caches or artifacts across multiple calls.
    See the execute_writeable call for a writeable workspace.
    """
    return _run_cmd(command, image, writable=False, ctx=ctx)


@mcp.tool()
def execute_writable(
    command: str, image: str = "debian:latest", ctx: Context = CurrentContext()
) -> str:
    """Run a command with write access to /workspace in an isolated container.

    Only use this when you need to modify files on the host (sed -i, patch, writing build output, etc.).
    Prefer the read-only 'execute' tool unless modification is required.

    Same options as the execute mcp call.
    """
    return _run_cmd(command, image, writable=True, ctx=ctx)
