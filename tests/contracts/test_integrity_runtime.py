import subprocess
import sys
from pathlib import Path


def test_integrity_scripts_fail_closed_when_assertions_are_disabled():
    root = Path(__file__).parents[2]
    completed = subprocess.run(
        [sys.executable, "-O", "scripts/verify_location_search.py"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode != 0
    assert "Integrity verification is disabled" in completed.stderr
