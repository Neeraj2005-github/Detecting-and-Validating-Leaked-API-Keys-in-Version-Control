"""One-command O2.4-O2.6 reproduction."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.benchmark_engine import run_benchmark
from backend.services.fixture_generator import generate_fixture


def main() -> int:
    generate_fixture()
    test = subprocess.run([sys.executable, "-m", "pytest", "tests/test_cp1_complete.py", "-q"], check=False)
    report = run_benchmark()
    print(f"Benchmark approaches: {len(report['approaches'])}")
    return test.returncode


if __name__ == "__main__":
    raise SystemExit(main())
