"""Load and validate the versioned O1 ground-truth oracle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LIFECYCLE_LABELS = frozenset(
    {
        "STILL_IN_HEAD",
        "DELETED_IN_HISTORY",
        "ORPHAN_BRANCH",
        "GIT_TAG",
        "BASE64_ENCODED",
        "REWRITTEN_HISTORY",
    }
)


@dataclass(frozen=True)
class OracleEntry:
    id: str
    secret_type: str
    value: str
    is_secret: bool
    expected_lifecycle: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "secret_type": self.secret_type,
            "value": self.value,
            "is_secret": self.is_secret,
            "expected_lifecycle": self.expected_lifecycle,
        }


@dataclass(frozen=True)
class OracleSpec:
    version: str
    name: str
    description: str
    entries: tuple[OracleEntry, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "entries": [entry.as_dict() for entry in self.entries],
        }


def load_oracle(path: str | Path | None = None) -> OracleSpec:
    """Load an oracle and reject malformed or unsupported lifecycle labels."""
    oracle_path = Path(path) if path else Path(__file__).resolve().parents[2] / "fixtures" / "oracle_spec.yaml"
    try:
        raw = yaml.safe_load(oracle_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Unable to load oracle specification: {oracle_path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
        raise ValueError("Oracle specification must contain an entries list")

    entries: list[OracleEntry] = []
    seen_ids: set[str] = set()
    for item in raw["entries"]:
        if not isinstance(item, dict):
            raise ValueError("Oracle entries must be mappings")
        required = {"id", "secret_type", "value", "is_secret", "expected_lifecycle"}
        if not required.issubset(item):
            raise ValueError(f"Oracle entry is missing fields: {sorted(required - set(item))}")
        entry = OracleEntry(
            id=str(item["id"]),
            secret_type=str(item["secret_type"]),
            value=str(item["value"]),
            is_secret=bool(item["is_secret"]),
            expected_lifecycle=str(item["expected_lifecycle"]),
        )
        if entry.id in seen_ids:
            raise ValueError(f"Duplicate oracle entry id: {entry.id}")
        if entry.expected_lifecycle not in LIFECYCLE_LABELS:
            raise ValueError(f"Unsupported lifecycle label: {entry.expected_lifecycle}")
        seen_ids.add(entry.id)
        entries.append(entry)

    return OracleSpec(
        version=str(raw.get("version", "")),
        name=str(raw.get("name", "")),
        description=str(raw.get("description", "")),
        entries=tuple(entries),
    )


__all__ = ["LIFECYCLE_LABELS", "OracleEntry", "OracleSpec", "load_oracle"]
