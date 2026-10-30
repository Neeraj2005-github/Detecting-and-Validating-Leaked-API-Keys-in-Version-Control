"""Generate reproducible evaluation artifacts for the project poster.

Run from the repository root with ``python scripts/generate_poster_evaluation.py``.
All inputs are synthetic/versioned project fixtures; no secret plaintext is
written to the generated reports.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "fixtures" / "oracle_spec.yaml"
ARTIFACTS = ROOT / "artifacts"
MODEL_PATH = ROOT / "backend" / "ml" / "detector_model.pkl"
sys.path.insert(0, str(ROOT))

from backend.ml.detector import (  # noqa: E402
    FEATURE_NAMES,
    PATTERNS,
    ensure_model,
    extract_14_features,
)
from backend.ml.xgboost_rigour import run_rigour  # noqa: E402
from backend.services.oracle_loader import OracleEntry, load_oracle  # noqa: E402
from backend.services.rotation_state_machine import RotationStateMachine  # noqa: E402


def _write(name: str, payload: dict[str, Any]) -> Path:
    output = ARTIFACTS / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _line(entry: OracleEntry) -> str:
    labels = {
        "aws_access_key": "AWS_ACCESS_KEY_ID",
        "mysql_uri": "DATABASE_URL",
        "encoded_secret": "ENCODED_SECRET",
        "generic_token": "LEGACY_AUTH_TOKEN",
        "high_entropy_decoy": "EXAMPLE_DECOY",
    }
    return f"{labels.get(entry.secret_type, 'SECRET')}={entry.value}"


def _metrics(labels: list[bool], predictions: list[bool]) -> dict[str, Any]:
    tp = sum(actual and predicted for actual, predicted in zip(labels, predictions))
    fp = sum(not actual and predicted for actual, predicted in zip(labels, predictions))
    fn = sum(actual and not predicted for actual, predicted in zip(labels, predictions))
    tn = sum(not actual and not predicted for actual, predicted in zip(labels, predictions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
    }


def _regex_prediction(entry: OracleEntry) -> bool:
    return any(pattern.search(_line(entry)) for _, pattern in PATTERNS)


def _gitleaks_predictions(entries: tuple[OracleEntry, ...]) -> tuple[list[bool], str]:
    """Run Gitleaks on a temporary fixture, falling back to the same rule set.

    The temporary fixture keeps this evaluation independent of the developer's
    working tree and makes native-vs-emulator provenance explicit.
    """
    binary = shutil.which("gitleaks")
    if not binary:
        return [_regex_prediction(entry) for entry in entries], "emulator:backend.ml.detector.PATTERNS"

    with tempfile.TemporaryDirectory(prefix="poster-gitleaks-") as directory:
        root = Path(directory)
        for index, entry in enumerate(entries):
            target = root / f"entry_{index}.env"
            target.write_text(_line(entry) + "\n", encoding="utf-8")
        report = root / "report.json"
        result = subprocess.run(
            [binary, "detect", "--source", str(root), "--report-format", "json", "--report-path", str(report), "--no-banner"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode not in (0, 1) or not report.exists():
            return [_regex_prediction(entry) for entry in entries], f"emulator:native_failed_{result.returncode}"
        findings = json.loads(report.read_text(encoding="utf-8"))
        detected_files = {Path(str(item.get("File", ""))).name for item in findings if isinstance(item, dict)}
        return [f"entry_{index}.env" in detected_files for index in range(len(entries))], "gitleaks_native"


def _run_rq1(entries: tuple[OracleEntry, ...]) -> dict[str, Any]:
    labels = [entry.is_secret for entry in entries]
    start = time.perf_counter()
    regex_predictions = [_regex_prediction(entry) for entry in entries]
    regex_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    gitleaks_predictions, gitleaks_provenance = _gitleaks_predictions(entries)
    gitleaks_elapsed = time.perf_counter() - start

    model = ensure_model()
    vectors = [
        [extract_14_features(entry.value, f"config/{entry.id}.env", _line(entry))[name] for name in FEATURE_NAMES]
        for entry in entries
    ]
    start = time.perf_counter()
    probabilities = [float(value) for value in model.predict_proba(vectors)[:, 1]]
    model_elapsed = time.perf_counter() - start
    model_predictions = [value >= 0.5 for value in probabilities]

    def result(name: str, predictions: list[bool], elapsed: float) -> dict[str, Any]:
        metrics = _metrics(labels, predictions)
        metrics["scan_seconds_per_1000_commits"] = elapsed / max(1, len(entries)) * 1000
        return {"name": name, "metrics": metrics}

    return {
        "task": "RQ1 Detection on Held-Out Split",
        "oracle": str(ORACLE_PATH.relative_to(ROOT)),
        "held_out_entries": len(entries),
        "positive_entries": sum(labels),
        "methods": [
            result("Regex only", regex_predictions, regex_elapsed),
            result(f"Gitleaks ({gitleaks_provenance})", gitleaks_predictions, gitleaks_elapsed),
            result("Proposed 14-feature XGBoost", model_predictions, model_elapsed),
        ],
        "model": str(MODEL_PATH.relative_to(ROOT)),
        "measurement_note": "Wall-clock measurement covers prediction/rule evaluation over the eight oracle entries; the normalized speed is seconds per 1,000 entries labeled as commits.",
    }


def _dcg(values: list[float], cutoff: int) -> float:
    return sum(value / math.log2(index + 2) for index, value in enumerate(values[:cutoff]))


def _ndcg(relevance: list[int], scores: list[float], cutoff: int) -> float:
    ranked = [value for _, value in sorted(zip(scores, relevance), reverse=True)]
    ideal = sorted(relevance, reverse=True)
    ideal_dcg = _dcg(ideal, cutoff)
    return _dcg(ranked, cutoff) / ideal_dcg if ideal_dcg else 0.0


def _run_rq2(entries: tuple[OracleEntry, ...]) -> dict[str, Any]:
    model = ensure_model()
    vectors = np.asarray([
        [extract_14_features(entry.value, f"config/{entry.id}.env", _line(entry))[name] for name in FEATURE_NAMES]
        for entry in entries
    ])
    raw = model.predict_proba(vectors)[:, 1].astype(float).tolist()
    import shap

    shap_values = shap.TreeExplainer(model)(vectors).values
    if shap_values.ndim == 3:
        shap_values = shap_values[:, :, 1]
    shap_magnitude = np.abs(shap_values).sum(axis=1)
    span = float(shap_magnitude.max() - shap_magnitude.min())
    shap_signal = ((shap_magnitude - shap_magnitude.min()) / span if span else np.full(len(entries), 0.5)).tolist()
    lifecycle_recency = {
        "STILL_IN_HEAD": 1.0,
        "DELETED_IN_HISTORY": 0.4,
        "ORPHAN_BRANCH": 0.7,
        "GIT_TAG": 0.7,
        "BASE64_ENCODED": 1.0,
        "REWRITTEN_HISTORY": 0.4,
    }
    privilege = [1.0 if entry.secret_type in {"aws_access_key", "mysql_uri"} else 0.6 for entry in entries]
    recency = [lifecycle_recency[entry.expected_lifecycle] for entry in entries]
    head = [1.0 if entry.expected_lifecycle in {"STILL_IN_HEAD", "BASE64_ENCODED"} else 0.0 for entry in entries]
    composite = [
        100 * (0.45 * shap_value + 0.25 * head_value + 0.15 * privilege_value + 0.15 * recency_value)
        for shap_value, head_value, privilege_value, recency_value in zip(shap_signal, head, privilege, recency)
    ]
    relevance = [3 if entry.is_secret and head_value else 2 if entry.is_secret else 0 for entry, head_value in zip(entries, head)]

    def p_at(scores: list[float], cutoff: int) -> float:
        ranking = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)[:cutoff]
        return sum(relevance[index] > 0 for index in ranking) / max(1, len(ranking))

    return {
        "task": "RQ2 Prioritization Quality",
        "formula": "100 * (0.45*normalized_abs_SHAP + 0.25*HEAD + 0.15*privilege_tier + 0.15*recency)",
        "ranking_count": len(entries),
        "raw_confidence": {"ndcg_at_10": _ndcg(relevance, raw, 10), "precision_at_5": p_at(raw, 5)},
        "composite_risk_score": {"ndcg_at_10": _ndcg(relevance, composite, 10), "precision_at_5": p_at(composite, 5)},
        "entries": [
            {
                "id": entry.id,
                "raw_confidence": raw[index],
                "normalized_abs_shap": shap_signal[index],
                "composite_risk_score": composite[index],
                "relevance": relevance[index],
            }
            for index, entry in enumerate(entries)
        ],
    }


def _run_rq3(entries: tuple[OracleEntry, ...]) -> dict[str, Any]:
    secret_entries = [entry for entry in entries if entry.is_secret]
    runs = [RotationStateMachine(entry.id).run() for entry in secret_entries]
    mttr = [float(run["mttr_ms"]) for run in runs]
    return {
        "task": "RQ3 Rotation Tracking",
        "sandbox": "sqlite-in-memory-offline",
        "total_findings": len(secret_entries),
        "deleted_but_valid": sum(entry.expected_lifecycle == "DELETED_IN_HISTORY" for entry in secret_entries),
        "successfully_rotated_and_verified": sum(run["state"] == "VERIFIED_SAFE" for run in runs),
        "mean_mttr_ms": sum(mttr) / max(1, len(mttr)),
        "runs": [{"credential_id": run["credential_id"], "state": run["state"], "mttr_ms": run["mttr_ms"]} for run in runs],
    }


def _run_ablation_chart() -> dict[str, Any]:
    report = run_rigour()
    ablations = report["ablations"]
    labels = ["Regex only", "+ Entropy", "+ Context Keywords", "Full XGBoost"]
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    values = [float(item["metrics"]["f1"]) for item in ablations]
    figure, axis = plt.subplots(figsize=(8, 4.5), dpi=160)
    bars = axis.bar(labels, values, color=["#9ecae1", "#6baed6", "#3182bd", "#08519c"])
    axis.set_ylim(0, 1.05)
    axis.set_ylabel("F1-score")
    axis.set_title("Feature-group ablation on the frozen test split")
    axis.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.3f}", ha="center")
    figure.tight_layout()
    figure.savefig(ARTIFACTS / "ablation_f1_chart.png")
    plt.close(figure)
    return {"task": "Figure 4 Feature-group Ablation", "source": "backend.ml.xgboost_rigour.run_rigour", "ablations": ablations}


def _run_shap_plot(entries: tuple[OracleEntry, ...]) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    model = ensure_model()
    matrix = np.asarray([
        [extract_14_features(entry.value, f"config/{entry.id}.env", _line(entry))[name] for name in FEATURE_NAMES]
        for entry in entries
    ])
    explanation = shap.TreeExplainer(model)(matrix)
    values = explanation.values
    if values.ndim == 3:
        values = values[:, :, 1]
    shap.summary_plot(values, matrix, feature_names=FEATURE_NAMES, show=False, plot_size=(10, 6))
    figure = plt.gcf()
    figure.tight_layout()
    figure.savefig(ARTIFACTS / "shap_summary_plot.png", dpi=180, bbox_inches="tight")
    plt.close(figure)
    return {
        "task": "Figure 5 SHAP Explanation",
        "model": str(MODEL_PATH.relative_to(ROOT)),
        "explainer": "shap.TreeExplainer",
        "feature_names": FEATURE_NAMES,
        "sample_count": len(entries),
    }


def main() -> None:
    entries = load_oracle(ORACLE_PATH).entries
    rq1 = _run_rq1(entries)
    rq2 = _run_rq2(entries)
    rq3 = _run_rq3(entries)
    ablation = _run_ablation_chart()
    shap_plot = _run_shap_plot(entries)
    _write("rq1_table_metrics.json", rq1)
    _write("rq2_prioritization_metrics.json", rq2)
    _write("rq3_rotation_metrics.json", rq3)
    master = {
        "generated_by": "scripts/generate_poster_evaluation.py",
        "oracle": str(ORACLE_PATH.relative_to(ROOT)),
        "rq1": rq1,
        "rq2": rq2,
        "rq3": rq3,
        "figure_4_ablation": ablation,
        "figure_5_shap": shap_plot,
    }
    _write("poster_evaluation_master.json", master)
    print(json.dumps({"artifacts": sorted(path.name for path in ARTIFACTS.glob("rq*_*.json")) + ["ablation_f1_chart.png", "shap_summary_plot.png", "poster_evaluation_master.json"]}, indent=2))


if __name__ == "__main__":
    main()
