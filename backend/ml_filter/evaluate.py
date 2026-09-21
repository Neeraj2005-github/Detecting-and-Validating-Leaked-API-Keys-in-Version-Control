from __future__ import annotations

import json
from pathlib import Path

import joblib
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

from backend.ml_filter.features import FEATURE_COLUMNS, extract_features

ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH = ROOT / "testdata" / "ground_truth.yaml"
RAW_DEBUG = ROOT / "testdata" / "_raw_debug.yaml"
MODEL_PATH = ROOT / "backend" / "ml_filter" / "model.pkl"
REPORTS_DIR = ROOT / "reports"
SPLITS_PATH = REPORTS_DIR / "split_indices.json"
METRICS_PATH = REPORTS_DIR / "baseline_metrics.json"


def _load_raw_debug() -> list[dict]:
    if not RAW_DEBUG.exists():
        return []
    data = yaml.safe_load(RAW_DEBUG.read_text(encoding="utf-8")) or []
    return data if isinstance(data, list) else []


def _feature_matrix(entries: list[dict]) -> tuple[list[list[float]], list[int]]:
    raw_debug = _load_raw_debug()
    raw_map = {
        (item.get("commit_sha"), item.get("file"), item.get("line")): item
        for item in raw_debug
        if isinstance(item, dict)
    }
    X, y = [], []
    for item in entries:
        key = (item.get("commit_sha"), item.get("file"), item.get("line"))
        debug = raw_map.get(key, {})
        matched_value = debug.get("raw_value") if isinstance(debug, dict) else None
        matched_value = matched_value if matched_value is not None else "AKIA1234567890ABCDEF"
        features = extract_features(str(matched_value), str(item.get("file", "")), str(debug.get("surrounding_line", "")))
        X.append([features[col] for col in FEATURE_COLUMNS])
        y.append(1 if item.get("label") == "true_secret" else 0)
    return X, y


def _metrics_from_predictions(y_true: list[int], y_pred: list[int]) -> dict:
    counts = _confusion_counts(y_true, y_pred)
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": float(sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1) / max(1, sum(1 for t in y_true if t == 0))),
        "confusion_counts": counts,
    }


def _confusion_counts(y_true: list[int], y_pred: list[int]) -> dict[str, int]:
    return {
        "tp": sum(1 for truth, prediction in zip(y_true, y_pred) if truth == 1 and prediction == 1),
        "fp": sum(1 for truth, prediction in zip(y_true, y_pred) if truth == 0 and prediction == 1),
        "tn": sum(1 for truth, prediction in zip(y_true, y_pred) if truth == 0 and prediction == 0),
        "fn": sum(1 for truth, prediction in zip(y_true, y_pred) if truth == 1 and prediction == 0),
    }


def _load_split_indices() -> dict[str, list[int]]:
    splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    if not isinstance(splits, dict) or not all(key in splits for key in ("train", "val", "test")):
        raise ValueError("split_indices.json must contain train, val, and test index lists")
    return {key: [int(index) for index in splits[key]] for key in ("train", "val", "test")}


def _single_feature_leakage(X_test: list[list[float]], y_test: list[int]) -> list[str]:
    leakage_features = []
    for feature_index, feature_name in enumerate(FEATURE_COLUMNS):
        values = [row[feature_index] for row in X_test]
        candidates = sorted(set(values))
        thresholds = [(left + right) / 2 for left, right in zip(candidates, candidates[1:])]
        for threshold in thresholds:
            predictions = [int(value >= threshold) for value in values]
            inverse_predictions = [1 - prediction for prediction in predictions]
            if predictions == y_test or inverse_predictions == y_test:
                leakage_features.append(feature_name)
                break
    return leakage_features


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model not found. Run backend.ml_filter.train first.")
    if not SPLITS_PATH.exists():
        raise FileNotFoundError("Split indices not found. Run backend.ml_filter.train first.")

    gt = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8")) or []
    X, y = _feature_matrix(gt)
    splits = _load_split_indices()
    all_indices = set(range(len(gt)))
    split_indices = set(splits["train"]) | set(splits["val"]) | set(splits["test"])
    if split_indices != all_indices or set(splits["train"]) & set(splits["test"]):
        raise ValueError("split_indices.json must partition ground-truth rows without overlap")

    test_indices = splits["test"]
    X_test = [X[index] for index in test_indices]
    y_test = [y[index] for index in test_indices]

    model = joblib.load(MODEL_PATH)
    test_pred = model.predict(X_test)
    baseline_a = _metrics_from_predictions(y_test, [1] * len(y_test))
    baseline_b = _metrics_from_predictions(y_test, test_pred)
    leakage_features = _single_feature_leakage(X_test, y_test)
    evaluation_valid = not leakage_features
    correct_classifications = [
        {
            "test_index": index,
            "label": int(truth),
            "features": {
                name: value
                for name, value in zip(FEATURE_COLUMNS, X_test[row_index])
                if value not in (0, 0.0)
            },
        }
        for row_index, (index, truth, prediction) in enumerate(zip(test_indices, y_test, test_pred))
        if truth == prediction
    ]
    report = {
        "baseline_A_gitleaks_only": baseline_a,
        "baseline_B_gitleaks_plus_ml_filter": baseline_b,
        "test_set_size": len(y_test),
        "model": "RandomForestClassifier",
        "random_state": 42,
        "test_indices": test_indices,
        "leakage_features": leakage_features,
        "evaluation_valid": evaluation_valid,
        "validation_warning": (
            "Test labels are perfectly separable by a single feature threshold; Baseline B is not a valid result."
            if leakage_features
            else None
        ),
        "correct_classification_features": correct_classifications,
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Test indices: {test_indices}")
    print(f"Test set size: {len(y_test)}")
    for name, metrics in (("Baseline A", baseline_a), ("Baseline B", baseline_b)):
        print(f"{name}: {metrics}")
    if baseline_b["f1"] == 1.0:
        print(f"Baseline B correct-classification features: {correct_classifications}")
    if leakage_features:
        print(f"DATA LEAKAGE WARNING: single feature(s) perfectly separate the test labels: {leakage_features}")


if __name__ == "__main__":
    main()
