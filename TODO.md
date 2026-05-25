# Issues

overlayfs for default mount: `execute` currently mounts `/workspace` as `:ro`, which breaks tools that write temp files. The correct behaviour is an overlay mount — container sees a writable view of the workspace, but writes go to a tmpfs upper layer and are discarded on exit. Only `execute_writable` should persist changes to the host. Podman supports this via `--mount type=overlay,source=...,destination=...`.
dind/pinp: AIs frequently need to build or run containers from project Dockerfiles. A third tool (e.g. `execute_in_container`) should expose the host socket opt-in. This is a real privilege boundary so it must be a separate explicit tool, not a flag on the existing ones.
uid mapping: `execute_writable` is broken with rootless Podman. Container uid 1000 does not map to the host user. Needs `--userns=keep-id`.
podman/docker: the command line flag should be properly documented.
single command: The ai manually chains commands. this should be done in the tool.
session param: the ai should not specifically request a session. that makes no sense
pypi package & update & test commands in readme

