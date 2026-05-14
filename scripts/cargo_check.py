"""Pre-commit hook to check Rust code"""

import subprocess
import sys
from pathlib import Path

rust_dir: Path = Path(__file__).parent.parent / "rust" / "_photidy"
try:
    subprocess.check_call(args=["cargo", "check"], cwd=rust_dir)
except subprocess.CalledProcessError as e:
    sys.exit(e.returncode)
