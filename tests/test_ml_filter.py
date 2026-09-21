import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.ml_filter import evaluate as evaluate_module
from backend.ml_filter.features import extract_features

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_extract_features_returns_all_keys_for_sample():
    features = extract_features("AKIA1234567890ABCDEF", "src/test_example.py", "example: placeholder secret")

    assert set(features.keys()) == {
        "entropy",
        "length",
        "char_class_count",
        "digit_ratio",
        "is_test_path",
        "has_example_keyword",
        "repeated_char_ratio",
    }
    assert features["length"] == len("AKIA1234567890ABCDEF")

    for value in ["", "A"]:
        res = extract_features(value, "path.py", "")
        assert set(res.keys()) == set(features.keys())


def test_extract_features_handles_empty_and_short_inputs_without_exception():
    for value in ["", "A"]:
        result = extract_features(value, "path.py", "")
        assert set(result.keys()) == {
            "entropy",
            "length",
            "char_class_count",
            "digit_ratio",
            "is_test_path",
            "has_example_keyword",
            "repeated_char_ratio",
        }
        assert all(isinstance(result[key], (int, float)) for key in result)


def test_train_script_generates_model_and_metrics():
    model_path = REPO_ROOT / "backend" / "ml_filter" / "model.pkl"
    metrics_path = REPO_ROOT / "reports" / "baseline_metrics.json"

    subprocess.run([sys.executable, "-m", "backend.ml_filter.train"], cwd=REPO_ROOT, check=True)

    assert model_path.exists()
    assert model_path.stat().st_size > 0
    assert metrics_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    baseline_b = metrics["baseline_B_gitleaks_plus_ml_filter"]
    assert isinstance(baseline_b["f1"], float)
    assert 0.0 <= baseline_b["f1"] <= 1.0

    base_a = metrics["baseline_A_gitleaks_only"]["false_positive_rate"]
    base_b_fpr = baseline_b["false_positive_rate"]
    assert base_b_fpr <= base_a


def test_evaluate_main_generates_report_and_metrics():
    model_path = REPO_ROOT / "backend" / "ml_filter" / "model.pkl"
    if not model_path.exists():
        subprocess.run([sys.executable, "-m", "backend.ml_filter.train"], cwd=REPO_ROOT, check=True)

    evaluate_module.main()

    metrics_path = REPO_ROOT / "reports" / "baseline_metrics.json"
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert "baseline_A_gitleaks_only" in metrics
    assert "baseline_B_gitleaks_plus_ml_filter" in metrics
    assert isinstance(metrics["baseline_B_gitleaks_plus_ml_filter"]["f1"], float)
    assert 0.0 <= metrics["baseline_B_gitleaks_plus_ml_filter"]["f1"] <= 1.0


def test_baseline_b_false_positive_rate_is_not_worse():
    metrics_path = REPO_ROOT / "reports" / "baseline_metrics.json"
    if not metrics_path.exists():
        pytest.skip("report not built yet")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    base_a = metrics["baseline_A_gitleaks_only"]["false_positive_rate"]
    base_b = metrics["baseline_B_gitleaks_plus_ml_filter"]["false_positive_rate"]
    assert base_b <= base_a
