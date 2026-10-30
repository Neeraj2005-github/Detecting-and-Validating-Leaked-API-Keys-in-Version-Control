from __future__ import annotations

import json
import tempfile
from pathlib import Path

import joblib
import git

from backend.classification.classifier import classify
from backend.detection.gitleaks_runner import run_gitleaks
from backend.detection.normalizer import normalize
from backend.ml_filter.features import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "o2_evaluation.json"
MODEL_PATH = ROOT / "backend" / "ml_filter" / "model.pkl"


def _metrics(labels: list[bool], predictions: list[bool]) -> dict[str, object]:
    tp = sum(label and prediction for label, prediction in zip(labels, predictions))
    fp = sum(not label and prediction for label, prediction in zip(labels, predictions))
    fn = sum(label and not prediction for label, prediction in zip(labels, predictions))
    tn = sum(not label and not prediction for label, prediction in zip(labels, predictions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
    }


def evaluate() -> dict[str, object]:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    examples = payload.get("examples", [])
    if not examples or any("expected_label" not in item for item in examples):
        raise ValueError("evaluation dataset has no ground-truth labels")

    with tempfile.TemporaryDirectory(prefix="shd_o2_eval_") as directory:
        root = Path(directory)
        for index, item in enumerate(examples):
            target = root / item["file_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item["text"] + "\n", encoding="utf-8")
        repository = git.Repo.init(root)
        with repository.config_writer() as config:
            config.set_value("user", "name", "SHD O2 Evaluation")
            config.set_value("user", "email", "shd-evaluation@example.test")
        repository.index.add([str(item["file_path"]) for item in examples])
        repository.index.commit("Create deterministic O2 evaluation examples")
        raw_findings = run_gitleaks(str(root))
        repository.close()

    normalized = normalize(raw_findings)
    by_path = {}
    for finding in normalized:
        path = finding.file.replace("\\", "/")
        for item in examples:
            if path.endswith(item["file_path"]):
                by_path[item["id"]] = finding
                break

    labels = [item["expected_label"] == "TRUE_SECRET" for item in examples]
    baseline_a_predictions = [item["id"] in by_path for item in examples]
    baseline_b_predictions = []
    model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
    for item in examples:
        finding = by_path.get(item["id"])
        if finding is None or model is None:
            baseline_b_predictions.append(False)
            continue
        classified = classify(finding)
        vector = [finding.features[column] for column in FEATURE_COLUMNS]
        probability = model.predict_proba([vector])[0]
        confidence = float(probability[1]) if len(probability) > 1 else float(probability[0])
        baseline_b_predictions.append(confidence >= 0.5)

    split = payload.get("split", {})
    test_ids = set(split.get("test", []))
    test_indices = [index for index, item in enumerate(examples) if item["id"] in test_ids]
    test_labels = [labels[index] for index in test_indices]
    test_a = [baseline_a_predictions[index] for index in test_indices]
    test_b = [baseline_b_predictions[index] for index in test_indices]
    return {
        "dataset": payload.get("dataset", DATASET_PATH.name),
        "dataset_path": str(DATASET_PATH.relative_to(ROOT)),
        "dataset_size": len(examples),
        "test_set_size": len(test_indices),
        "split_sizes": {name: len(ids) for name, ids in split.items()},
        "baseline_A_gitleaks_only": _metrics(test_labels, test_a),
        "baseline_B_gitleaks_plus_ml_filter": _metrics(test_labels, test_b),
        "evaluation_valid": True,
        "evaluation_error": None,
        "test_ids": [examples[index]["id"] for index in test_indices],
    }
