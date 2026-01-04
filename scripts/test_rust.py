"""Check build and run tests for Rust extension"""

import subprocess
from pathlib import Path

rust_dir = Path(__file__).parent.parent / "rust" / "_photidy"
subprocess.check_call(["cargo", "test"], cwd=rust_dir)
