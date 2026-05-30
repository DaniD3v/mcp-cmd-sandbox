from __future__ import annotations

from uuid import UUID, uuid4, uuid5

from fastmcp import Context
from python_on_whales import DockerClient

_SERVER_ID = uuid4()
_sessions: dict[UUID, Session] = {}


class Session:
    def __init__(self, ctx: Context, client: DockerClient) -> None:
        self.id: UUID = Session._generate_uuid(ctx)

        self.volume: str = f"mcp-cmd-sandbox-persistant-{self.id}"
        _ = client.volume.create(self.volume)

    @staticmethod
    def get(ctx: Context, client: DockerClient) -> Session:
        id = Session._generate_uuid(ctx)

        if id not in _sessions:
            _sessions[id] = Session(ctx, client)

        return _sessions[id]

    def remove(self, client: DockerClient):
        client.volume.remove(self.volume)

    @staticmethod
    def _generate_uuid(ctx: Context) -> UUID:
        return uuid5(_SERVER_ID, ctx.session_id)


def remove_all_sessions(client: DockerClient) -> None:
    for session in _sessions.values():
        session.remove(client)
