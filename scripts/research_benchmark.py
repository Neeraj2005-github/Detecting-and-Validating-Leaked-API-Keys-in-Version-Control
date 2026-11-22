from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import Iterable

import psutil


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "research_benchmark.json"


def run_with_resources(command: list[str], cwd: Path, timeout: int = 600) -> dict[str, object]:
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    peak_rss = 0
    cpu_seconds = 0.0
    try:
        proc = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                peak_rss = max(peak_rss, proc.memory_info().rss)
                cpu = proc.cpu_times()
                cpu_seconds = cpu.user + cpu.system
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            time.sleep(0.01)
        stdout, stderr = process.communicate(timeout=timeout)
        try:
            proc = psutil.Process(process.pid)
            peak_rss = max(peak_rss, proc.memory_info().rss)
            cpu = proc.cpu_times()
            cpu_seconds = cpu.user + cpu.system
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        raise RuntimeError("Benchmark child process timed out")
    wall = time.perf_counter() - started
    return {
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "peak_rss_bytes": peak_rss,
        "cpu_seconds": cpu_seconds,
        "wall_seconds": wall,
    }


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"median": 0.0, "min": 0.0, "max": 0.0, "ci95_low": 0.0, "ci95_high": 0.0}
    rng = random.Random(1704067200)
    bootstraps = []
    for _ in range(1000):
        sample = [rng.choice(values) for _ in values]
        bootstraps.append(sum(sample) / len(sample))
    return {
        "median": percentile(values, 0.5),
        "min": min(values),
        "max": max(values),
        "ci95_low": percentile(bootstraps, 0.025),
        "ci95_high": percentile(bootstraps, 0.975),
    }


def native_scan(repo: Path, run: int) -> tuple[list[str], dict[str, object]]:
    report = repo.parent / f".gitleaks-{repo.name}-{run}.json"
    result = run_with_resources(
        [
            "gitleaks",
            "detect",
            "--source",
            str(repo),
            "--report-format",
            "json",
            "--report-path",
            str(report),
            "--no-banner",
        ],
        cwd=repo,
        timeout=600,
    )
    findings: list[str] = []
    if report.exists():
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = []
        for item in payload:
            file = str(item.get("File") or "")
            findings.append(file.replace("\\", "/"))
        report.unlink(missing_ok=True)
    return findings, result


def detect_secrets_scan(repo: Path) -> tuple[list[str], dict[str, object]]:
    result = run_with_resources(
        ["detect-secrets", "scan", "--all-files", str(repo)],
        cwd=repo,
        timeout=600,
    )
    findings: list[str] = []
    if result["returncode"] == 0:
        try:
            payload = json.loads(str(result["stdout"]))
        except json.JSONDecodeError:
            payload = {}
        for file, records in payload.get("results", {}).items():
            if records:
                findings.append(str(file).replace("\\", "/"))
    return findings, result


def category_metrics(files: Iterable[str]) -> dict[str, dict[str, float]]:
    found = {file.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for file in files}
    categories = {
        "added-then-deleted": {"expected": {"config.env"}, "negative": set()},
        "documentation-false-positive": {"expected": set(), "negative": {"README.md"}},
        "clean-negative": {"expected": set(), "negative": {"evidence.txt"}},
    }
    output: dict[str, dict[str, float]] = {}
    for name, spec in categories.items():
        expected = set(spec["expected"])
        negatives = set(spec["negative"])
        tp = len(found & expected)
        fp = len(found & negatives)
        fn = len(expected - found)
        tn = len(negatives - found)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        fpr = fp / (fp + tn) if fp + tn else 0.0
        output[name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "false_positive_rate": fpr,
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "tn": float(tn),
        }
    return output


def aggregate_runs(repo: Path, scanner: str, runs: int) -> dict[str, object]:
    per_run_metrics: list[dict[str, dict[str, float]]] = []
    resources: list[dict[str, object]] = []
    for run in range(1, runs + 1):
        if scanner == "gitleaks":
            files, resource = native_scan(repo, run)
        else:
            files, resource = detect_secrets_scan(repo)
        per_run_metrics.append(category_metrics(files))
        resources.append(resource)

    categories = ["added-then-deleted", "documentation-false-positive", "clean-negative"]
    metric_names = ["precision", "recall", "f1", "false_positive_rate"]
    metrics_output: dict[str, object] = {}
    for category in categories:
        metrics_output[category] = {}
        for metric_name in metric_names:
            values = [float(run[category][metric_name]) for run in per_run_metrics]
            metrics_output[category][metric_name] = summary(values)

    return {
        "runs": runs,
        "metrics": metrics_output,
        "resources": {
            "peak_rss_bytes": summary([float(item["peak_rss_bytes"]) for item in resources]),
            "cpu_seconds": summary([float(item["cpu_seconds"]) for item in resources]),
            "wall_seconds": summary([float(item["wall_seconds"]) for item in resources]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000])
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    output: dict[str, object] = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gitleaks_version": "8.18.4",
        "detect_secrets_version": "1.5.0",
        "fixtures": {},
    }
    for size in args.sizes:
        repo = ROOT / "artifacts" / "scaling-repos" / f"benchmark-{size}"
        if not repo.exists():
            print(f"Fixture missing: {repo}")
            continue
        commit_count = len(subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--all", "--count"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip())
        output["fixtures"][str(size)] = {
            "measured_commits": int(subprocess.run(
                ["git", "-C", str(repo), "rev-list", "--all", "--count"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()),
            "gitleaks": aggregate_runs(repo, "gitleaks", args.runs),
            "detect-secrets": aggregate_runs(repo, "detect-secrets", args.runs),
        }
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Benchmark report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
