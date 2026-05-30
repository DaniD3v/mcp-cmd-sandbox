"""
krun microVM runtime support — full kernel enables docker-compose, loop/FUSE mounts, etc.
libkrunfw.so ships as package data in lib/; the wrapper sets LD_LIBRARY_PATH before execing krun.
"""

from inspect import cleandoc
from pathlib import Path
from shutil import which
from tempfile import NamedTemporaryFile

_KRUN_PATH = which("krun")
AVAILABLE = _KRUN_PATH is not None

# The wrapper must be generated at runtime with the absolute krun path baked in because:
# - the OCI runtime is invoked with a minimal PATH.
# - there is no way to pass data to the wrapper script.
if AVAILABLE:
    _lib_dir = Path(__file__).parent / "lib"

    with NamedTemporaryFile(mode="w", prefix="krun-wrapper-", delete=False) as f:
        _ = f.write(
            cleandoc(f"""
                #!/bin/sh
                export LD_LIBRARY_PATH="{_lib_dir}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}"
                exec '{_KRUN_PATH}' "$@"
            """)
        )
        WRAPPER: Path = Path(f.name)
    WRAPPER.chmod(0o755)
