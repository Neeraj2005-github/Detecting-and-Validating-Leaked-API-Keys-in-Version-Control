from __future__ import annotations

from typing import Any


GITLEAKS_FIELDS = ("RuleID", "StartLine", "File", "Commit", "Secret", "Match")


def validate_gitleaks_report(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Gitleaks report must be a JSON array")
    validated: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Gitleaks report record {index} is not an object")
        missing = [field for field in GITLEAKS_FIELDS if field not in item]
        if missing:
            raise ValueError(f"Gitleaks report record {index} is missing required fields")
        if not isinstance(item["StartLine"], int) or item["StartLine"] < 1:
            raise ValueError(f"Gitleaks report record {index} has invalid StartLine")
        validated.append(item)
    return validated
