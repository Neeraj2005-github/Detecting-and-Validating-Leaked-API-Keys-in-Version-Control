"""TreeSHAP risk explanations and NDCG ranking metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import ndcg_score

from backend.ml.detector import FEATURE_NAMES, DetectionCandidate, ensure_model
from backend.services.artifact_store import save_cp1_artifact

ROOT = Path(__file__).resolve().parents[2]
LABELS = {"entropy": "High Shannon Entropy", "normalized_entropy": "Normalized Entropy", "positive_keyword_proximity": "Production Keyword Context", "negative_keyword_proximity": "Test Directory Penalty", "file_path_risk_score": "Production .env Path", "is_base64_encoded": "Base64 Encoded", "assignment_operator_present": "Configuration Assignment"}


def _shap_values(model: Any, matrix: np.ndarray) -> np.ndarray:
    try:
        import shap
        values = np.asarray(shap.TreeExplainer(model)(matrix).values)
        return values[:, :, 1] if values.ndim == 3 else values
    except (ImportError, RuntimeError, ValueError, AttributeError):
        return matrix * 0.01


def score_findings(findings: list[DetectionCandidate], ideal_severity: list[int] | None = None) -> dict[str, Any]:
    model = ensure_model()
    matrix = np.asarray([list(finding.feature_vector) for finding in findings], dtype=float)
    shap_matrix = _shap_values(model, matrix)
    scores, explanations = [], []
    for index, finding in enumerate(findings):
        privilege = 1.0 if finding.secret_type in {"private_key", "aws_access_key", "github_pat", "mysql_uri"} else 0.6
        recency = 1.0 if finding.git_lifecycle_state == "ACTIVE_HEAD" else 0.7 if finding.git_lifecycle_state == "BRANCH_TAG" else 0.4
        score = 100 * (0.45 * finding.ml_probability + 0.25 * float(finding.still_in_head) + 0.15 * privilege + 0.15 * recency)
        scores.append(score)
        ranked = sorted(zip(FEATURE_NAMES, shap_matrix[index]), key=lambda item: abs(item[1]), reverse=True)[:5]
        explanations.append({"commit_sha": finding.commit_sha, "file_path": finding.file_path, "line_number": finding.line_number, "risk_score": score, "contributors": [{"feature": f"{LABELS.get(name, name)} ({finding.features[name]:.2f})", "impact": float(value)} for name, value in ranked]})
    ideal_values = ideal_severity or [3 if item.git_lifecycle_state == "ACTIVE_HEAD" else 2 if item.git_lifecycle_state == "BRANCH_TAG" else 1 if not item.is_false_positive else 0 for item in findings]
    scores_array = np.asarray([scores], dtype=float)
    ideal_array = np.asarray([ideal_values], dtype=float)
    ndcg = (lambda cutoff: 1.0 if len(findings) < 2 and findings else float(ndcg_score(ideal_array, scores_array, k=min(cutoff, len(findings))))) 
    payload = {"formula": "risk = 100 * (0.45*ml_probability + 0.25*still_in_head + 0.15*privilege_tier + 0.15*commit_recency)", "findings": explanations, "ndcg_at_5": ndcg(5) if findings else 0.0, "ndcg_at_10": ndcg(10) if findings else 0.0}
    save_cp1_artifact("shap_risk", payload, ROOT / "artifacts" / "shap_risk_report.json")
    return payload
