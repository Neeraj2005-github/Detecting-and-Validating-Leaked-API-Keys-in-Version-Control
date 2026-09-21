from __future__ import annotations

import json
from pathlib import Path

import joblib
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

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
        if matched_value is None:
            matched_value = "AKIA1234567890ABCDEF"
        features = extract_features(str(matched_value), str(item.get("file", "")), str(debug.get("surrounding_line", "")))
        X.append([features[col] for col in FEATURE_COLUMNS])
        y.append(1 if item.get("label") == "true_secret" else 0)
    return X, y


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    gt = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8")) or []
    X, y = _feature_matrix(gt)
    if len(X) < 2:
        raise ValueError("Ground truth must include at least two labeled entries for training.")

    all_indices = list(range(len(X)))
    train_indices, temp_indices = train_test_split(all_indices, test_size=0.3, stratify=y, random_state=42)
    val_indices, test_indices = train_test_split(
        temp_indices,
        test_size=0.5,
        stratify=[y[index] for index in temp_indices],
        random_state=42,
    )
    X_train = [X[index] for index in train_indices]
    y_train = [y[index] for index in train_indices]
    X_val = [X[index] for index in val_indices]
    y_val = [y[index] for index in val_indices]
    X_test = [X[index] for index in test_indices]
    y_test = [y[index] for index in test_indices]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    val_pred = model.predict(X_val)
    metrics = {
        "precision": precision_score(y_val, val_pred, zero_division=0),
        "recall": recall_score(y_val, val_pred, zero_division=0),
        "f1": f1_score(y_val, val_pred, zero_division=0),
    }
    print(metrics)

    joblib.dump(model, MODEL_PATH)
    split_indices = {"train": train_indices, "val": val_indices, "test": test_indices}
    SPLITS_PATH.write_text(json.dumps(split_indices, indent=2), encoding="utf-8")

    model_pred = model.predict(X_test)
    y_true = y_test
    baseline_a = {
        "precision": precision_score(y_true, [1] * len(y_true), zero_division=0),
        "recall": recall_score(y_true, [1] * len(y_true), zero_division=0),
        "f1": f1_score(y_true, [1] * len(y_true), zero_division=0),
        "false_positive_rate": float(sum(1 for t, p in zip(y_true, [1] * len(y_true)) if t == 0 and p == 1) / max(1, sum(1 for t in y_true if t == 0))),
    }
    baseline_b = {
        "precision": precision_score(y_true, model_pred, zero_division=0),
        "recall": recall_score(y_true, model_pred, zero_division=0),
        "f1": f1_score(y_true, model_pred, zero_division=0),
        "false_positive_rate": float(sum(1 for t, p in zip(y_true, model_pred) if t == 0 and p == 1) / max(1, sum(1 for t in y_true if t == 0))),
    }

    report = {
        "baseline_A_gitleaks_only": baseline_a,
        "baseline_B_gitleaks_plus_ml_filter": baseline_b,
        "test_set_size": len(y_true),
        "model": "RandomForestClassifier",
        "random_state": 42,
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
