from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class PlantedSecret(BaseModel):
    model_config = ConfigDict(frozen=True)

    commit_hash: str
    file_path: str
    secret_type: str
    removed_in_commit: str


class DatasetEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    repo_id: str
    split: Literal["reference", "eval"]
    source: str
    planted_secrets: list[PlantedSecret]


def load_manifest(path: str | Path) -> list[DatasetEntry]:
    """Load and validate a list or {"repos": [...]} manifest."""
    payload: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = payload.get("repos", payload) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("dataset manifest must contain a list of repository entries")
    return [DatasetEntry.model_validate(entry) for entry in entries]


def write_manifest(entries: list[DatasetEntry], path: str | Path) -> None:
    """Write a deterministic manifest after validating split disjointness."""
    validate_split_disjoint(entries)
    payload = {"repos": [entry.model_dump(mode="json") for entry in entries]}
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_split_disjoint(entries: list[DatasetEntry]) -> None:
    reference_ids = {entry.repo_id for entry in entries if entry.split == "reference"}
    eval_ids = {entry.repo_id for entry in entries if entry.split == "eval"}
    overlap = reference_ids & eval_ids
    if overlap:
        raise ValueError(f"repository IDs occur in both dataset splits: {sorted(overlap)}")