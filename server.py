#!/usr/bin/env python3
"""MCP server for isolated container execution via Docker/Podman."""

import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP
from python_on_whales import DockerClient

SESSIONS: dict[str, str] = {}
client = DockerClient(client_call=sys.argv[1:] or ["docker"])


@asynccontextmanager
async def lifespan(server):
    yield
    for vol in SESSIONS.values():
        try:
            client.volume.remove(vol)
        except Exception:
            pass


mcp = FastMCP("mcp-cmd-sandbox", lifespan=lifespan)


def _session(sid: str | None = None) -> str:
    if not sid:
        sid = uuid.uuid4().hex[:12]
    if sid not in SESSIONS:
        vol = f"mcp-sandbox-{sid}"
        client.volume.create(vol)
        SESSIONS[sid] = vol
    return sid


def _run(command: str, image: str, session_id: str | None, writable: bool) -> str:
    sid = _session(session_id)
    vol = SESSIONS[sid]
    cwd = str(Path.cwd())
    mode = "rw" if writable else "ro"

    try:
        output = client.run(
            image,
            ["sh", "-c", command],
            volumes=[(cwd, "/workspace", mode), (vol, "/persistent", "rw")],
            workdir="/workspace",
            user="1000:1000",
            remove=True,
            stream=False,
        )
        return f"{output}\n[session: {sid}]"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def execute(command: str, image: str = "debian:latest", session_id: str | None = None) -> str:
    """Run a command in an isolated container.

    - /workspace: your project directory (READ-ONLY)
    - /persistent: writable volume that survives across calls within the same session_id

    Pick an image appropriate for the task:
      debian:latest (default, general purpose), alpine:latest (minimal),
      rust:latest, python:3.12-slim, node:22-alpine, golang:latest,
      gcc:latest, eclipse-temurin:21, maven:latest, nixos/nix:latest

    Use session_id to persist build caches or artifacts in /persistent across multiple calls.
    """
    return _run(command, image, session_id, writable=False)


@mcp.tool()
def execute_writable(command: str, image: str = "debian:latest", session_id: str | None = None) -> str:
    """Run a command with WRITE access to /workspace (the host project directory).

    Only use this when you need to modify files on the host (sed -i, patch, writing build output, etc.).
    Prefer the read-only 'execute' tool unless modification is required.

    Same image and session_id options as execute.
    """
    return _run(command, image, session_id, writable=True)


if __name__ == "__main__":
    mcp.run()
