"""Check build and run tests for Rust extension"""

import subprocess
from pathlib import Path

rust_dir: Path = Path(__file__).parent.parent / "rust" / "_photidy"
subprocess.check_call(args=["cargo", "test"], cwd=rust_dir)
