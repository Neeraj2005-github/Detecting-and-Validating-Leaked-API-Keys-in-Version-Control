from __future__ import annotations

import re

from detect_secrets.core import scan
from detect_secrets.settings import default_settings

from .models import BlobRecord, RawFinding


_SECRET_TYPE_MAP = {
    "AWS Access Key": "aws_access_key",
    "GitHub Token": "github_token",
    "Slack Token": "slack_token",
    "Base64 High Entropy String": "high_entropy_string",
    "Hex High Entropy String": "high_entropy_string",
}
_ENTROPY_TYPES = {"Base64 High Entropy String", "Hex High Entropy String"}
_GITHUB_TOKEN_PATTERN = re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}", re.IGNORECASE)
_UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


def _is_ignored_entropy_value(value: str) -> bool:
    return bool(_UUID_PATTERN.fullmatch(value) or _COMMIT_PATTERN.fullmatch(value))


def match(blob_record: BlobRecord) -> list[RawFinding]:
    """Run detect-secrets independently against one blob."""
    findings: list[RawFinding] = []

    with default_settings():
        for line_number, line in enumerate(blob_record.blob_content.splitlines(), start=1):
            secrets = list(scan.scan_line(line))
            typed_values = {
                secret.secret_value
                for secret in secrets
                if secret.type not in _ENTROPY_TYPES and secret.secret_value
            }

            for secret in secrets:
                value = secret.secret_value
                if not value or secret.type not in _SECRET_TYPE_MAP:
                    continue
                if secret.type == "GitHub Token":
                    value = _GITHUB_TOKEN_PATTERN.search(line).group(0) if _GITHUB_TOKEN_PATTERN.search(line) else value
                if secret.type in _ENTROPY_TYPES:
                    if len(value) < 20 or _is_ignored_entropy_value(value) or typed_values:
                        continue

                findings.append(
                    RawFinding(
                        commit_hash=blob_record.commit_hash,
                        file_path=blob_record.file_path,
                        line_number=line_number,
                        matched_string=value,
                        secret_type=_SECRET_TYPE_MAP[secret.type],
                        detector_confidence=0.5 if secret.type in _ENTROPY_TYPES else 1.0,
                        detector_source="detect-secrets",
                    ),
                )

    return findings