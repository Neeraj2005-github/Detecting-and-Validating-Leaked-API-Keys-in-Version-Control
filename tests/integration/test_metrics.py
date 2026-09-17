import pytest

from src.shd.metrics import compute_metrics
from src.shd.models import DedupedFinding


def finding(secret_id: str, is_real: bool) -> DedupedFinding:
    return DedupedFinding(
        secret_id=secret_id,
        secret_type="aws_access_key",
        commit_hashes=[secret_id],
        first_seen_commit=secret_id,
        present_in_head=False,
        label_ground_truth=is_real,
        dataset_split="eval",
    )


def test_metrics_toy_example() -> None:
    result = compute_metrics(
        [finding("a", True), finding("b", True), finding("c", False)],
        {"eval": {"total_planted_secrets": 3}},
    )

    assert result["overall"]["true_positive"] == 2
    assert result["overall"]["false_positive"] == 1
    assert result["overall"]["false_negative"] == 1
    assert result["overall"]["precision"] == pytest.approx(2 / 3)
    assert result["overall"]["recall"] == pytest.approx(2 / 3)
    assert result["overall"]["f1"] == pytest.approx(2 / 3)
    assert result["overall"]["fpr"] == pytest.approx(1 / 3)


def test_metrics_zero_denominators_are_zero() -> None:
    result = compute_metrics([], {"eval": {"total_planted_secrets": 0}})

    assert result["overall"]["precision"] == 0.0
    assert result["overall"]["recall"] == 0.0
    assert result["overall"]["f1"] == 0.0
    assert result["overall"]["fpr"] == 0.0