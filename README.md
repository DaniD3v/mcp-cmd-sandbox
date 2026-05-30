# mcp-cmd-sandbox
An MCP server that runs commands inside Docker/Podman containers.
It is supposed to replace the built-in bash tool with a more secure and usable alternative.

# Why
**Usability**: You don't need to click `Yes` for every single command.  
**Security**: Fully isolated environment.  
**No tokens wasted on setup**: Your agent won't waste tokens to setup build tools  

# Design:
**One command per container** - ephermal per design  
**Configurable permissions**: Separate tool call for write-access so you can set granular permissions  
**Persistance**: A per-session anonymous volume holds explicitly persisted data.  
**Runtime Agnostic**: Docker and Podman support  
**Security by design**:  
  - a library for docker/podman access -> no goofy command injections
  - no --privileged bs. the ai can only set the command and the image

# microVM support

When `krun` is in PATH, commands can be executed in vm-mode.
This allows the ai to run tasks a standard (rootless) container couldn't:
  - docker compose
  - loop/FUSE mounts
  - k8s

# Install

Requires the `docker`/`podman` command to be installed.

```
uvx mcp-cmd-sandbox
```

## Installing `krun`

Installing `krun` is optional, but recommended as it allows the ai to run commands like docker compose.
`krun` comes with `crun`. If it is not installed yet, update your crun package.

> You have to restart the mcp server for the changes to take effect.

## Integration

### OpenCode

Install the mcp server by running the command:
```
opencode mcp add
  > Name: cmd-sandbox
  > Type: Local
  > Command: uvx mcp-cmd-sandbox
```

or by editing your `opencode.json`:
```json
{
  "mcp": {
    "cmd-sandbox": {
      "type": "local",
      "command": [
        "uvx",
        "mcp-cmd-sandbox"
      ]
    }
  }
}
```

To replace the builtin Bash tool and set correct permissions, add this to your `opencode.json`:
```json
{
  "tools": {
    "bash": false
  },
  "permission": {
    "cmd-sandbox_execute_writable": "ask"
  }
}
```

### Claude Code

Install the mcp server with the command:
```
claude mcp add cmd-sandbox -- uvx mcp-cmd-sandbox
```

To replace the builtin Bash tool and set correct permissions, add this to your `.claude/settings.json`:
```json
{
  "permissions": {
    "allow": ["mcp__cmd-sandbox__execute"],
    "deny": ["Bash"]
  }
}
```

### Codex

Install the mcp server by running the command:
```
codex mcp add cmd-sandbox -- uvx mcp-cmd-sandbox
```

or by editing your `.codex/config.toml`:
```toml
[mcp_servers.cmd-sandbox]
command = "uvx"
args = ["mcp-cmd-sandbox"]
```

(TODO: add permission `execute` permission bypass once I can test with codex)
To replace the builtin Bash tool and set correct permissions, add this to your `.codex/config.toml`:  
```toml
[features]
shell_tool = false
```
