from datetime import datetime, timezone

from src.shd.matcher import match
from src.shd.models import BlobRecord


def make_blob(content: str) -> BlobRecord:
    return BlobRecord(
        commit_hash="a" * 40,
        commit_timestamp=datetime.now(timezone.utc),
        file_path="config.py",
        blob_content=content,
        is_head=True,
    )


def test_detects_aws_key() -> None:
    findings = match(make_blob("AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'"))

    assert len(findings) == 1
    assert findings[0].secret_type == "aws_access_key"
    assert findings[0].matched_string == "AKIAIOSFODNN7EXAMPLE"


def test_detects_github_token_value() -> None:
    token = "ghp_" + "123456789012345678901234567890123456"

    findings = match(make_blob(f"GITHUB_TOKEN = '{token}'"))

    assert len(findings) == 1
    assert findings[0].secret_type == "github_token"
    assert findings[0].matched_string == token


def test_ignores_uuid() -> None:
    assert match(make_blob("request_id = 'f47ac10b-58cc-4372-a567-0e02b2c3d479'")) == []


def test_ignores_git_commit_hash() -> None:
    assert match(make_blob("commit = '0123456789abcdef0123456789abcdef01234567'")) == []


def test_empty_content_returns_no_findings() -> None:
    assert match(make_blob("")) == []


def test_garbled_content_does_not_crash() -> None:
    assert match(make_blob("value = '\ufffd\ufffd\ufffd'")) == []


def test_detects_aws_and_slack_with_line_numbers() -> None:
    slack_token = "xoxb-" + "111111111111-222222222222-aaaaaaaaaaaaaaaaaaaaaaaa"
    findings = match(make_blob(
        "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
        f"SLACK_TOKEN = '{slack_token}'",
    ))

    assert [(finding.secret_type, finding.line_number) for finding in findings] == [
        ("aws_access_key", 1),
        ("slack_token", 2),
    ]


def test_duplicate_secret_on_two_lines_is_not_deduplicated() -> None:
    findings = match(make_blob(
        "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
        "OTHER_KEY = 'AKIAIOSFODNN7EXAMPLE'",
    ))

    assert len(findings) == 2
    assert [finding.line_number for finding in findings] == [1, 2]


def test_high_entropy_string_is_reported() -> None:
    findings = match(make_blob("value = 'A9f3K2m8Q1r7T4y6P0w5N8c2L6s4D7h9'"))

    assert any(finding.secret_type == "high_entropy_string" for finding in findings)