from __future__ import annotations

from pathlib import Path

from backend.ml.dataset_kappa import evaluate_kappa
from backend.ml.xgboost_rigour import run_rigour
from backend.services.rotation_state_machine import rotate


def test_kappa_and_frozen_group_split() -> None:
    report = evaluate_kappa()
    assert report["sample_count"] >= 20
    assert -1 <= report["cohen_kappa"] <= 1
    assert report["frozen_split"]["frozen"] is True
    assert set(report["frozen_split"]["test_groups"]).isdisjoint(report["frozen_split"]["train_groups"])


def test_xgboost_ablation_has_five_folds_and_four_configs() -> None:
    report = run_rigour()
    assert report["cv"]["folds"] == 5
    assert len(report["cv"]["metrics"]) == 5
    assert [item["config"] for item in report["ablations"]] == [
        "A_regex_entropy",
        "B_regex_entropy_lexical",
        "C_regex_entropy_lexical_context",
        "D_full_xgboost",
    ]
    for item in report["ablations"]:
        assert set(item["metrics"]) == {"precision", "recall", "f1", "roc_auc", "false_positive_rate"}


def test_rotation_success_and_rollback_are_terminal() -> None:
    assert rotate("test-success")["state"] == "VERIFIED_SAFE"
    assert rotate("test-failure", force_failure=True)["state"] == "FAILED_ROLLBACK"
