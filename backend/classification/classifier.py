from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from backend.detection.normalizer import RawFinding


class ClassifiedFinding(BaseModel):
    commit_sha: str
    file: str
    line: int
    secret_type: str
    criticality: int
    matched_string_hash: str


RULE_MAP = {
    "aws-access-key": "aws_access_key",
    "aws-access-token": "aws_access_key",
    "aws-secret-key": "aws_secret_key",
    "aws-secret-access-key": "aws_secret_key",
    "github-pat": "github_pat",
    "stripe": "stripe_key",
    "stripe-access-token": "stripe_key",
    "slack-token": "slack_token",
    "slack-access-token": "slack_token",
    "sendgrid-api-key": "sendgrid_key",
    "twilio-api-key": "twilio_key",
    "jwt": "jwt",
    "generic-high-entropy": "generic_high_entropy",
    "generic-api-key": "generic_high_entropy",
}


def _load_table() -> dict[str, int]:
    table_path = Path(__file__).with_name("criticality_table.yaml")
    with table_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return {str(k): int(v) for k, v in data.items()}


def classify(finding: RawFinding) -> ClassifiedFinding:
    """Map finding.rule_id (Gitleaks rule name) to a canonical secret_type using
    a fixed dict, then look up criticality from criticality_table.yaml.
    Unknown rule_id -> secret_type='generic_high_entropy', criticality=30."""
    rule_id = str(finding.rule_id).lower()
    secret_type = RULE_MAP.get(rule_id, "generic_high_entropy")
    criticality = _load_table().get(secret_type, 30)
    return ClassifiedFinding(
        commit_sha=finding.commit_sha,
        file=finding.file,
        line=finding.line,
        secret_type=secret_type,
        criticality=criticality,
        matched_string_hash=finding.matched_string_hash,
    )
