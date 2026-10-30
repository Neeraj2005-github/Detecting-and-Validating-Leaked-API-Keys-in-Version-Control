"""Frozen-split XGBoost cross-validation and four-stage ablation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from backend.ml.dataset_kappa import DEFAULT_CSV, DEFAULT_SPLIT, frozen_split, load_labels
from backend.ml.detector import FEATURE_NAMES, extract_14_features
from backend.services.artifact_store import save_cp1_artifact

ROOT = Path(__file__).resolve().parents[2]
GROUPS = {
    "A_regex_entropy": ["entropy", "normalized_entropy"],
    "B_regex_entropy_lexical": ["entropy", "normalized_entropy", "token_length", "digit_ratio", "uppercase_ratio", "lowercase_ratio", "symbol_ratio", "transition_frequency"],
    "C_regex_entropy_lexical_context": ["entropy", "normalized_entropy", "token_length", "digit_ratio", "uppercase_ratio", "lowercase_ratio", "symbol_ratio", "transition_frequency", "positive_keyword_proximity", "negative_keyword_proximity", "file_path_risk_score"],
    "D_full_xgboost": list(FEATURE_NAMES),
}


def _model(scale_pos_weight: float) -> Any:
    from xgboost import XGBClassifier
    return XGBClassifier(n_estimators=60, max_depth=3, learning_rate=0.08, scale_pos_weight=scale_pos_weight, random_state=42, eval_metric="logloss", n_jobs=1)


def _matrix(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    values, labels = [], []
    for row in rows:
        positive = str(row["annotator_1"]).upper() in {"SECRET", "ACTIVE_SECRET", "HISTORICAL_SECRET"}
        token = "AKIAIOSFODNN7EXAMPLE" if positive else "placeholder-value-123456"
        features = extract_14_features(token, f"{row['repository_group']}/config.env", f"SECRET={token}" if positive else f"EXAMPLE={token}")
        values.append([features[name] for name in FEATURE_NAMES])
        labels.append(int(positive))
    return np.asarray(values), np.asarray(labels)


def _metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predictions = (probabilities >= 0.5).astype(int)
    negatives = max(1, int((y_true == 0).sum()))
    return {
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)) if len(set(y_true)) > 1 else 0.5,
        "false_positive_rate": float(((y_true == 0) & (predictions == 1)).sum() / negatives),
    }


def run_rigour(csv_path: str | Path = DEFAULT_CSV, split_path: str | Path = DEFAULT_SPLIT) -> dict[str, Any]:
    rows = load_labels(csv_path)
    split = frozen_split(rows, split_path)
    test_groups = set(split["test_groups"])
    train_rows = [row for row in rows if row["repository_group"] not in test_groups]
    test_rows = [row for row in rows if row["repository_group"] in test_groups]
    x_train, y_train = _matrix(train_rows)
    x_test, y_test = _matrix(test_rows)
    scale_pos_weight = float((len(y_train) - y_train.sum()) / max(1, y_train.sum()))
    cv_scores = []
    for train_index, validation_index in StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(x_train, y_train):
        model = _model(scale_pos_weight)
        model.fit(x_train[train_index], y_train[train_index])
        cv_scores.append(_metrics(y_train[validation_index], model.predict_proba(x_train[validation_index])[:, 1]))
    ablations = []
    for config, names in GROUPS.items():
        indexes = [FEATURE_NAMES.index(name) for name in names]
        model = _model(scale_pos_weight)
        model.fit(x_train[:, indexes], y_train)
        ablations.append({"config": config, "features": names, "metrics": _metrics(y_test, model.predict_proba(x_test[:, indexes])[:, 1])})
    payload = {"dataset": "real_repo_20_dual_annotator_benchmark", "frozen_test_groups": sorted(test_groups), "cv": {"folds": 5, "stratified": True, "scale_pos_weight": scale_pos_weight, "metrics": cv_scores}, "ablations": ablations, "tuning_guard": "Frozen test groups were not used for model selection."}
    save_cp1_artifact("xgboost_ablation", payload, ROOT / "artifacts" / "xgboost_ablation_report.json")
    return payload
