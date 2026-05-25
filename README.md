# mcp-cmd-sandbox
An MCP server that runs commands inside Docker/Podman containers.
It is supposed to replace the built-in bash tool with a more secure and usable alternative.

# Why
Usability: You don't need to click `Yes` for every single command.
Security: Fully isolated environment.
No tokens wasted on setup: Your agent won't waste tokens to setup build tools

# Design:
One command per container - ephermal per design
Configurable permissions: Separate tool call for write-access so you can set granular permissions
Persistance: A per-session anonymous volume holds explicitely persisted data.
Runtime Agnostic: Docker and Podman support
Security by design:
  - a library for docker/podman access -> no goofy command injections
  - no --privileged bs. the ai can only set the command and the image

## Install

Requires the docker or podman commands to be installed.

```
uv pip install -e .
```

## Integration

### OpenCode

```
opencode mcp add mcp-cmd-sandbox -- python /path/to/mcp-shell-sandbox/server.py
```

To disable the builtin shell tool, add to your `opencode.json`:

```json
{
  "mcp": {
    "mcp-cmd-sandbox": {
      "command": "python",
      "args": ["/path/to/mcp-shell-sandbox/server.py"]
    }
  },
  "permissions": {
    "deny": ["shell"]
  }
}
```

### Claude Code

```
claude mcp add mcp-cmd-sandbox -- python /path/to/mcp-shell-sandbox/server.py
```

To replace the builtin Bash tool, add to your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": ["Bash"]
  }
}
```

### Codex

```
codex mcp add mcp-cmd-sandbox -- python /path/to/mcp-shell-sandbox/server.py
```

To disable the builtin shell execution, set in your codex config:

```json
{
  "mcp": {
    "mcp-cmd-sandbox": {
      "command": "python",
      "args": ["/path/to/mcp-shell-sandbox/server.py"]
    }
  },
  "disableTools": ["shell"]
}
```
