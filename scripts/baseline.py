from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_TIMEOUT_SECONDS = 1800


def _run(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Baseline command failed with exit code {completed.returncode}: "
            f"{Path(command[0]).name}"
        )
    return completed


def _require_clean_checkout() -> None:
    status = _run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        ROOT,
        timeout=20,
    )
    if status.stdout.strip():
        raise RuntimeError("Baseline requires a clean checkout")


def _baseline(sizes: list[int], runs: int) -> int:
    if runs < 5:
        raise ValueError("The baseline requires at least five runs per scanner")
    _require_clean_checkout()
    with tempfile.TemporaryDirectory(prefix="secretguard-baseline-") as directory:
        checkout = Path(directory) / "checkout"
        _run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-recurse-submodules",
                "--",
                str(ROOT),
                str(checkout),
            ],
            ROOT,
            timeout=120,
        )
        comparison = checkout / "scripts" / "comparison_benchmark.py"
        _run(
            [
                sys.executable,
                str(comparison),
                "--sizes",
                *[str(size) for size in sizes],
                "--runs",
                str(runs),
            ],
            checkout,
            timeout=BASELINE_TIMEOUT_SECONDS,
        )
        generated = (
            (checkout / "artifacts" / "comparison.json"),
            (checkout / "docs" / "comparison.md"),
        )
        for path in generated:
            if not path.is_file():
                raise RuntimeError(f"Baseline output is missing: {path.name}")
        shutil.copy2(generated[0], ROOT / "artifacts" / generated[0].name)
        shutil.copy2(generated[1], ROOT / "docs" / generated[1].name)
    print("Fixture generation, native/wrapper/detect-secrets scans, and reports completed.")
    print(f"Evidence: {ROOT / 'artifacts' / 'comparison.json'}")
    print(f"Evidence: {ROOT / 'docs' / 'comparison.md'}")
    return 0


def _task(task: str) -> int:
    if task == "baseline":
        return _baseline([100, 1000], 5)
    if task == "build":
        _run(["docker", "build", "-t", "secretguard-cp1", "."], ROOT, timeout=1800)
    elif task == "test":
        _run([sys.executable, "-m", "pytest", "-q"], ROOT, timeout=1800)
    elif task == "fixture":
        _run(
            [sys.executable, "-c", "from backend.services.fixture_generator import generate_fixture; generate_fixture()"],
            ROOT,
            timeout=600,
        )
    elif task == "scan":
        with tempfile.TemporaryDirectory(prefix="secretguard-scan-") as directory:
            report = Path(directory) / "gitleaks.json"
            command = [
                "gitleaks",
                "detect",
                "--source",
                str(ROOT),
                "--config",
                str((ROOT / "gitleaks.toml").resolve()),
                "--report-format",
                "json",
                "--report-path",
                str(report),
                "--no-banner",
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
                shell=False,
            )
            if completed.returncode not in (0, 1):
                raise RuntimeError("Gitleaks scan failed; diagnostics were suppressed")
    elif task == "clean":
        for path in (ROOT / ".pytest_cache", ROOT / "artifacts" / "_archive" / "runtime-test"):
            if path.is_dir():
                shutil.rmtree(path)
    print(f"Completed baseline task: {task}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "task",
        nargs="?",
        choices=("baseline", "build", "test", "fixture", "scan", "clean"),
        default="baseline",
    )
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000])
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    if args.task == "baseline":
        return _baseline(args.sizes, args.runs)
    return _task(args.task)


if __name__ == "__main__":
    raise SystemExit(main())
