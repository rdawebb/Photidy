"""Build and install the Rust module using maturin"""

import subprocess
from pathlib import Path

rust_dir: Path = Path(__file__).parent.parent / "rust" / "_photidy"
subprocess.check_call(args=["maturin", "develop"], cwd=rust_dir)
