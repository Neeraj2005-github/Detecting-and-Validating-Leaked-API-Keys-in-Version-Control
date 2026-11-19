from __future__ import annotations

import json
import shutil
import sys
import statistics
import subprocess
from pathlib import Path

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


def run_one(binary: str, repo: Path, run: int) -> dict:
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
    profile = profile_child_process(command, ROOT)
    return profile


def summary(values: list[float]) -> dict:
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> int:
    binary = gitleaks_binary()
    if not binary:
        payload = {
            "status": "NOT MEASURED",
            "reason": "native gitleaks not found on PATH",
            "cpu_model": cpu_model_name(),
            "runs": [],
        }
        OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 2
    repos = ROOT / "artifacts" / "scaling-repos"
    runs_output = []
    for count in COUNTS:
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
        samples = [run_one(binary, repo, run) for run in range(1, RUNS + 1)]
        wall = [sample["wall_time_seconds"] for sample in samples]
        cpu = [sample["cpu_time_seconds"] for sample in samples]
        rss = [sample["peak_rss_mb"] for sample in samples if sample["peak_rss_mb"] is not None]
        runs_output.append({
            "commits": commit_count,
            "repo_size_bytes": repo_size_bytes(repo),
            "runs": samples,
            "median_min_max": {
                "wall_time_seconds": summary(wall),
                "cpu_time_seconds": summary(cpu),
                "peak_rss_mb": summary(rss) if rss else "NOT MEASURED",
            },
        })
    payload = {
        "status": "MEASURED",
        "cpu_model": cpu_model_name(),
        "gitleaks_version": subprocess.run(
            [binary, "version"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip(),
        "runs": runs_output,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
