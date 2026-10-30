from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import git
import joblib
import yaml
from sklearn.ensemble import RandomForestClassifier

from backend.classification.classifier import classify
from backend.detection.gitleaks_runner import run_gitleaks
from backend.detection.normalizer import normalize
from backend.evaluation import ValidationStatus, classify_path, criticality_level
from backend.ml_filter.features import FEATURE_COLUMNS

MODEL_PATH = Path(__file__).resolve().parent / "ml_filter" / "model.pkl"
GROUND_TRUTH = Path(__file__).resolve().parent.parent / "testdata" / "ground_truth.yaml"
RAW_DEBUG = Path(__file__).resolve().parent.parent / "testdata" / "_raw_debug.yaml"


def _load_raw_debug() -> list[dict]:
    if not RAW_DEBUG.exists():
        return []
    data = yaml.safe_load(RAW_DEBUG.read_text(encoding="utf-8")) or []
    return data if isinstance(data, list) else []


def _ensure_model() -> None:
    if MODEL_PATH.exists():
        return
    from backend.ml_filter.train import main as train_main
    train_main()


def _normalize_repo_path(repo_path: str) -> str:
    candidate = Path(repo_path).expanduser()
    if not candidate.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")
    return str(candidate.resolve())


def _prepare_repo_for_scan(repo_path: str) -> tuple[str, str | None]:
    value = repo_path.strip()
    if value.startswith(("http://", "https://", "git://", "git@", "ssh://")):
        temp_dir = tempfile.mkdtemp(prefix="secretguard_scan_")
        git.Repo.clone_from(value, temp_dir)
        return temp_dir, temp_dir

    if not value:
        raise ValueError("Repository path is empty")

    local_path = Path(value).expanduser()
    if not local_path.exists():
        raise ValueError(f"Repository path does not exist: {value}")
    return str(local_path.resolve()), None


def run_pipeline(repo_path: str) -> list[dict]:
    """M1 -> M2 -> M3 -> M3b in sequence. Returns final list of findings that
    survived the ML filter, each with: commit_sha, file, line, secret_type,
    criticality, ml_confidence (float 0-1 from model.predict_proba).
    Must NOT call any external network API — O2 is fully offline/read-only
    against the local seeded repo only."""
    worktree, temp_dir = _prepare_repo_for_scan(repo_path)
    repo = _normalize_repo_path(worktree)
    try:
        raw_findings = run_gitleaks(repo)
        findings = normalize(raw_findings)

        try:
            model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
        except Exception:
            model = None
        kept: list[dict] = []
        for finding in findings:
            classified = classify(finding)
            features = finding.features
            confidence = None
            verdict = "NOT_AVAILABLE"
            if model is not None:
                try:
                    vector = [features[col] for col in FEATURE_COLUMNS]
                    proba = model.predict_proba([vector])[0]
                    confidence = float(proba[1]) if len(proba) > 1 else float(proba[0])
                    verdict = "Likely real secret" if confidence >= 0.5 else "Likely false positive"
                except (AttributeError, KeyError, ValueError):
                    confidence = None
                    verdict = "NOT_AVAILABLE"
            classification = classify_path(finding.file)
            is_current = True
            is_historical = False
            kept.append({
                "commit_sha": classified.commit_sha,
                "file": classified.file,
                "line": classified.line,
                "rule_id": finding.rule_id,
                "secret_hash": classified.matched_string_hash,
                "masked_preview": finding.masked_preview,
                "secret_type": classified.secret_type,
                "criticality": classified.criticality,
                "ml_confidence": confidence,
                "classification": classification.value,
                "validation_status": ValidationStatus.NOT_CHECKED.value,
                "criticality_level": criticality_level(
                    secret_type=classified.secret_type,
                    confidence=confidence,
                    classification=classification,
                    is_current=is_current,
                    is_historical=is_historical,
                ),
                "ml_verdict": verdict,
                "detected": True,
                "is_current": is_current,
                "is_historical": is_historical,
                "features": features,
            })
        return kept
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_path")
    args = parser.parse_args()
    print(json.dumps(run_pipeline(args.repo_path), indent=2))
