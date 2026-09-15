from datetime import datetime, timezone

from src.shd.dedup import compute_secret_id, deduplicate, normalize_secret
from src.shd.models import RawFinding


def make_finding(
    secret: str,
    commit_hash: str,
    timestamp: datetime,
    *,
    file_path: str = "config.py",
    secret_type: str = "aws_access_key",
    is_head: bool = False,
) -> RawFinding:
    return RawFinding(
        commit_hash=commit_hash,
        file_path=file_path,
        line_number=1,
        matched_string=secret,
        secret_type=secret_type,
        detector_confidence=1.0,
        detector_source="test",
        commit_timestamp=timestamp,
        is_head=is_head,
    )


def test_normalization_strips_whitespace_without_changing_case() -> None:
    assert normalize_secret("  SecretValue  ") == "SecretValue"
    assert compute_secret_id(" SecretValue") != compute_secret_id(" secretvalue")


def test_same_secret_across_commits_is_merged_deterministically() -> None:
    findings = [
        make_finding("  SAME  ", "commit-2", datetime(2024, 2, 1, tzinfo=timezone.utc)),
        make_finding("SAME", "commit-1", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        make_finding("SAME", "commit-3", datetime(2024, 3, 1, tzinfo=timezone.utc)),
    ]

    result = deduplicate(findings)

    assert len(result) == 1
    assert result[0].commit_hashes == ["commit-1", "commit-2", "commit-3"]
    assert result[0].first_seen_commit == "commit-1"


def test_different_secrets_are_not_merged() -> None:
    findings = [
        make_finding("FIRST", "commit-1", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        make_finding("SECOND", "commit-1", datetime(2024, 1, 1, tzinfo=timezone.utc)),
    ]

    assert len(deduplicate(findings)) == 2


def test_present_in_head_is_true_when_any_finding_is_head() -> None:
    findings = [
        make_finding("SAME", "commit-1", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        make_finding("SAME", "commit-2", datetime(2024, 2, 1, tzinfo=timezone.utc), is_head=True),
    ]

    assert deduplicate(findings)[0].present_in_head is True


def test_empty_input_returns_empty_output() -> None:
    assert deduplicate([]) == []