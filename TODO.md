# Issues

dind/pinp: AIs frequently need to build or run containers from project Dockerfiles. A third tool (e.g. `execute_in_container`) should expose the host socket opt-in. This is a real privilege boundary so it must be a separate explicit tool, not a flag on the existing ones.
pypi package & update & test commands in readme
codex: try out the config properly

# Low Priority:

uid mapping: settings a specific uid wouldn't work on podman due to permissions
