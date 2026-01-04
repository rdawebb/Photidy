"""Build and install the Rust module using maturin"""

import subprocess
from pathlib import Path

rust_dir = Path(__file__).parent.parent / "rust" / "_photidy"
subprocess.check_call(["maturin", "develop"], cwd=rust_dir)
