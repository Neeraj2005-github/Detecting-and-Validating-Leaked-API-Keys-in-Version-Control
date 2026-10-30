from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath


class Classification(StrEnum):
    TRUE_SECRET = "TRUE_SECRET"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    TEST_FIXTURE = "TEST_FIXTURE"
    EXAMPLE_DOCUMENTATION = "EXAMPLE_DOCUMENTATION"
    UNKNOWN = "UNKNOWN"


class ValidationStatus(StrEnum):
    NOT_CHECKED = "NOT_CHECKED"


def classify_path(file_path: str) -> Classification:
    """Apply explicit O2 fixture rules without treating detection as validity."""
    path = PurePosixPath((file_path or "").replace("\\", "/"))
    parts = {part.lower() for part in path.parts}
    filename = path.name.lower()
    if "testdata" in parts or "tests" in parts or filename.startswith("test_"):
        return Classification.TEST_FIXTURE
    if "docs" in parts and (filename.startswith("example") or filename.endswith(".md")):
        return Classification.EXAMPLE_DOCUMENTATION
    return Classification.UNKNOWN


def criticality_level(
    *,
    secret_type: str,
    confidence: float | None,
    classification: Classification,
    is_current: bool,
    is_historical: bool,
    validation_status: ValidationStatus = ValidationStatus.NOT_CHECKED,
) -> str:
    if classification in {Classification.TEST_FIXTURE, Classification.EXAMPLE_DOCUMENTATION}:
        return "LOW"
    if validation_status != ValidationStatus.NOT_CHECKED:
        return "HIGH" if validation_status == "VALID" else "MEDIUM"
    if not confidence or confidence < 0.5:
        return "UNKNOWN"
    if is_current and is_historical:
        return "CRITICAL"
    if is_current:
        return "HIGH" if secret_type in {"aws_access_key", "aws_secret_key", "stripe_key", "github_pat"} else "MEDIUM"
    if is_historical:
        return "MEDIUM"
    return "UNKNOWN"


def classification_label(value: str | None) -> Classification:
    try:
        return Classification(str(value or Classification.UNKNOWN))
    except ValueError:
        return Classification.UNKNOWN
