from __future__ import annotations

import pytest

from scripts.comparison_benchmark import _metrics, _summarize_scanner


@pytest.mark.parametrize(
    "category",
    [
        "unreachable-object-deleted-branch",
        "unreachable-object-force-push-dropped",
    ],
)
def test_unreachable_objects_are_not_scored_as_scanner_misses(category: str) -> None:
    for scanner in ("native-gitleaks", "wrapper", "detect-secrets"):
        result = _metrics(category, set(), scanner=scanner)
        assert "unreachable from every ref" in result["not_applicable_reason"]

        summary = _summarize_scanner(
            [{category: result}],
            [category],
            seed=1,
        )["categories"][category]
        assert summary["status"] == "NOT APPLICABLE"
        assert summary["recall"]["median"] is None


def test_worktree_scanner_does_not_get_history_only_false_negative() -> None:
    result = _metrics(
        "added-then-deleted",
        set(),
        scanner="detect-secrets",
    )

    assert "not Git history" in result["not_applicable_reason"]


def test_reachable_deleted_content_remains_measurable_for_history_scanners() -> None:
    result = _metrics(
        "added-then-deleted",
        {"cases/added-then-deleted.env"},
        scanner="wrapper",
    )

    assert result["recall"] == 1.0
    assert result["precision"] == 1.0
