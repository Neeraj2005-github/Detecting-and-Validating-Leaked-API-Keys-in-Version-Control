from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if not (ROOT / "README.md").is_file():
        print("README.md is missing")
        return 2
    with tempfile.TemporaryDirectory(prefix="shd-baseline-") as directory:
        baseline = Path(directory)
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-recurse-submodules",
                "--",
                str(ROOT),
                str(baseline / "checkout"),
            ],
            check=True,
            timeout=120,
            capture_output=True,
        )
        checkout = baseline / "checkout"
        if not (checkout / "README.md").is_file():
            print("Fresh checkout lacks README.md")
            return 3
        completed = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            cwd=checkout,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        print(completed.stdout.strip())
        if completed.stderr:
            print(completed.stderr.strip())
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
