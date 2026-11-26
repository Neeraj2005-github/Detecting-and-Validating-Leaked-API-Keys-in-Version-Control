from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.resource_profile import cpu_model_name, profile_child_process, repo_size_bytes
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "artifacts" / "resource_profile.json"
COUNTS = (100, 1000, 10000)
RUNS = 5


def gitleaks_binary() -> str | None:
    return shutil.which("gitleaks")


def run_one(binary: str, repo: Path, run: int, timeout_seconds: int) -> dict:
    report = repo.parent / f"{repo.name}-run-{run}.json"
    command = [
        binary,
        "detect",
        "--source",
        str(repo),
        "--config",
        str(ROOT / "gitleaks.toml"),
        "--report-format",
        "json",
        "--report-path",
        str(report),
        "--no-banner",
    ]
    try:
        profile = profile_child_process(
            command,
            ROOT,
            timeout_seconds=timeout_seconds,
        )
        profile.pop("stdout", None)
        profile.pop("stderr", None)
        return profile
    finally:
        report.unlink(missing_ok=True)


def summary(values: list[float]) -> dict:
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", nargs="+", type=int, default=list(COUNTS))
    parser.add_argument("--runs", type=int, default=RUNS)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    binary = gitleaks_binary()
    if not binary:
        payload = {
            "status": "NOT MEASURED",
            "reason": "native gitleaks not found on PATH",
            "cpu_model": cpu_model_name(),
            "runs": [],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 2
    repos = ROOT / "artifacts" / "scaling-repos"
    runs_output = []
    for count in args.counts:
        repo = repos / f"repo-{count}"
        if not repo.exists():
            runs_output.append({
                "commits": "NOT MEASURED",
                "repo_size_bytes": "NOT MEASURED",
                "runs": [],
                "median_min_max": {
                    "wall_time_seconds": "NOT MEASURED",
                    "cpu_time_seconds": "NOT MEASURED",
                    "peak_rss_mb": "NOT MEASURED",
                },
                "reason": f"MISSING_SCALING_REPO:{repo}",
            })
            continue
        commit_count = len(subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--all"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines())
        if commit_count != count:
            runs_output.append({
                "commits": commit_count,
                "repo_size_bytes": repo_size_bytes(repo),
                "runs": [],
                "median_min_max": {
                    "wall_time_seconds": "NOT MEASURED",
                    "cpu_time_seconds": "NOT MEASURED",
                    "peak_rss_mb": "NOT MEASURED",
                },
                "reason": f"INCOMPLETE_SCALING_REPO: expected {count}",
            })
            continue
        samples = []
        for run in range(1, args.runs + 1):
            try:
                samples.append(
                    run_one(binary, repo, run, args.timeout_seconds)
                )
            except RuntimeError as exc:
                samples.append({
                    "status": "NOT MEASURED",
                    "reason": str(exc),
                })
                break
        measured = [sample for sample in samples if "wall_time_seconds" in sample]
        if not measured:
            runs_output.append({
                "commits": commit_count,
                "repo_size_bytes": repo_size_bytes(repo),
                "runs": samples,
                "median_min_max": {
                    "wall_time_seconds": "NOT MEASURED",
                    "cpu_time_seconds": "NOT MEASURED",
                    "peak_rss_mb": "NOT MEASURED",
                },
                "reason": "NO_COMPLETED_PROFILE_RUN",
            })
            continue
        wall = [sample["wall_time_seconds"] for sample in measured]
        cpu = [sample["cpu_time_seconds"] for sample in measured]
        rss = [sample["peak_rss_mb"] for sample in measured if sample["peak_rss_mb"] is not None]
        runs_output.append({
            "commits": commit_count,
            "repo_size_bytes": repo_size_bytes(repo),
            "runs": samples,
            "status": "MEASURED" if len(measured) == args.runs else "PARTIAL",
            "median_min_max": {
                "wall_time_seconds": summary(wall),
                "cpu_time_seconds": summary(cpu),
                "peak_rss_mb": summary(rss) if rss else "NOT MEASURED",
            },
        })
    payload = {
        "status": (
            "MEASURED"
            if all(item.get("status") == "MEASURED" for item in runs_output)
            else "PARTIAL"
        ),
        "cpu_model": cpu_model_name(),
        "gitleaks_version": subprocess.run(
            [binary, "version"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip(),
        "runs": runs_output,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
