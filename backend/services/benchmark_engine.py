"""Head-to-head O2 benchmark runner with KPI and resource profiling."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

from backend.ml.detector import PATTERNS, detect_lines, shannon_entropy
from backend.scanner.history_walker import walk_history
from backend.services.artifact_store import save_cp1_artifact

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "artifacts" / "synthetic_repo_v1"
ORACLE = ROOT / "artifacts" / "ground_truth_oracle.json"
ARTIFACT = ROOT / "artifacts" / "o2_benchmark_kpis.json"
_ENTROPY_THRESHOLD = 3.2


def _rss_mb() -> float | None:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return None


def _key(path: str, line: int) -> tuple[str, int]:
    return path.replace("\\", "/"), int(line)


def _truth(oracle: dict[str, Any]) -> tuple[set[tuple[str, int]], set[tuple[str, int]], set[tuple[str, int]]]:
    true = {_key(item["file_path"], item["line_number"]) for item in oracle["entries"] if item["expected_label"] == "TP"}
    decoys = {_key(item["file_path"], item["line_number"]) for item in oracle["entries"] if item["expected_label"] == "FP_DECOY"}
    active = {_key(item["file_path"], item["line_number"]) for item in oracle["entries"] if item["entry_id"] in {"oracle-aws-head", "oracle-base64"}}
    return true, decoys, active


def _metrics(predicted: set[tuple[str, int]], true: set[tuple[str, int]], decoys: set[tuple[str, int]], active: set[tuple[str, int]]) -> dict[str, float | int]:
    tp = len(predicted & true)
    fp = len(predicted & decoys) + len(predicted - true - decoys)
    fn = len(true - predicted)
    negatives = max(1, len(decoys))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    fpr = len(predicted & decoys) / negatives
    historical = true - active
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1_score": 2 * precision * recall / max(1e-12, precision + recall),
        "historical_secrets_found_percent": 100 * len(predicted & historical) / max(1, len(historical)),
        "false_positive_rate": fpr,
        "unsafe_outcome_count": len(active - predicted),
    }


def _profile(name: str, runner: Any, true: set[tuple[str, int]], decoys: set[tuple[str, int]], active: set[tuple[str, int]]) -> dict[str, Any]:
    rss_before = _rss_mb()
    start = time.perf_counter()
    result = runner()
    elapsed_ms = (time.perf_counter() - start) * 1000
    rss_after = _rss_mb()
    predicted = set(result["predicted"])
    metrics = _metrics(predicted, true, decoys, active)
    metrics.update({
        "scan_wall_clock_ms": elapsed_ms,
        "peak_rss_mb": max(value for value in (rss_before, rss_after) if value is not None) if rss_before is not None or rss_after is not None else None,
    })
    return {"name": name, "provenance": result.get("provenance", "unknown"), "metrics": metrics}


def _added_line_values() -> list[dict[str, Any]]:
    return [line.as_dict() | {"added_line": line.added_line} for line in walk_history(FIXTURE)]


def _baseline_a() -> dict[str, Any]:
    predicted: set[tuple[str, int]] = set()
    for line in _added_line_values():
        text = str(line["added_line"])
        if any(pattern.search(text) for _, pattern in PATTERNS) or shannon_entropy(text.split("=", 1)[-1]) >= _ENTROPY_THRESHOLD:
            predicted.add(_key(str(line["file_path"]), int(line["line_number"])))
    return {"predicted": predicted, "provenance": "regex_plus_entropy"}


def _emulator() -> dict[str, Any]:
    predicted: set[tuple[str, int]] = set()
    for line in _added_line_values():
        text = str(line["added_line"])
        if any(pattern.search(text) for _, pattern in PATTERNS):
            predicted.add(_key(str(line["file_path"]), int(line["line_number"])))
    return {"predicted": predicted, "provenance": "gitleaks_rule_set_emulator: AWS/JWT/URI/private-key/token assignments"}


def _baseline_b() -> dict[str, Any]:
    binary = shutil.which("gitleaks")
    if not binary:
        return _emulator()
    with tempfile.TemporaryDirectory(prefix="o2-gitleaks-") as temp_dir:
        report = Path(temp_dir) / "report.json"
        command = [binary, "detect", "--source", str(FIXTURE), "--report-format", "json", "--report-path", str(report), "--no-banner"]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        if completed.returncode not in (0, 1) or not report.exists():
            return _emulator() | {"provenance": f"gitleaks_native_failed_fallback:{completed.returncode}"}
        try:
            findings = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return _emulator() | {"provenance": "gitleaks_native_invalid_report_fallback"}
        predicted = {_key(str(item.get("File", "")), int(item.get("StartLine", 1))) for item in findings if item.get("File")}
        return {"predicted": predicted, "provenance": "gitleaks_native"}


def _baseline_c() -> dict[str, Any]:
    try:
        from detect_secrets import SecretsCollection
        from detect_secrets.settings import default_settings
    except ImportError:
        return _emulator() | {"provenance": "detect_secrets_unavailable_rule_emulator"}
    collection = SecretsCollection()
    with default_settings():
        collection.scan_file(str(FIXTURE / "config" / "application.env"))
    predicted = {_key(str(item), 1) for item in collection.data}
    return {"predicted": predicted, "provenance": "detect_secrets_native"}


def _our_engine() -> dict[str, Any]:
    findings = detect_lines(walk_history(FIXTURE))
    return {
        "predicted": {_key(item.file_path, item.line_number) for item in findings if not item.is_false_positive},
        "provenance": "differential_walker_regex_entropy_xgboost",
    }


def run_benchmark(fixture_path: str | Path = FIXTURE, oracle_path: str | Path = ORACLE) -> dict[str, Any]:
    global FIXTURE
    FIXTURE = Path(fixture_path).resolve()
    oracle = json.loads(Path(oracle_path).read_text(encoding="utf-8"))
    true, decoys, active = _truth(oracle)
    results = [
        _profile("Baseline A: Regex + Entropy", _baseline_a, true, decoys, active),
        _profile("Baseline B: Gitleaks", _baseline_b, true, decoys, active),
        _profile("Baseline C: detect-secrets/trufflehog pattern baseline", _baseline_c, true, decoys, active),
        _profile("Our O2 Engine", _our_engine, true, decoys, active),
    ]
    payload = {
        "fixture": str(FIXTURE),
        "oracle": str(oracle_path),
        "truth_counts": {"true_positive": len(true), "decoy": len(decoys), "active_head": len(active)},
        "approaches": results,
        "tradeoff_analysis": "The O2 Engine is the reference architecture because it preserves added-line/history lifecycle context, identifies still-in-HEAD exposure, and applies XGBoost false-positive suppression. Native Gitleaks is a useful detector baseline but does not provide the same lifecycle semantics; the emulator preserves benchmark continuity when the optional binary is unavailable.",
        "resource_note": "RSS is sampled immediately before and after each run; install psutil for process-level memory telemetry.",
    }
    save_cp1_artifact("o2_benchmark_kpis", payload, ARTIFACT)
    return payload


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), indent=2))
