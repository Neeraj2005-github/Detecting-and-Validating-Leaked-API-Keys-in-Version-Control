from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Literal


class BlobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    commit_hash: str
    commit_timestamp: datetime | None
    file_path: str
    blob_content: str
    is_head: bool


class RawFinding(BaseModel):
    """One detector result passed from the matcher to the deduplicator."""

    model_config = ConfigDict(frozen=True)

    commit_hash: str
    file_path: str
    line_number: int
    matched_string: str
    secret_type: str
    detector_confidence: float
    detector_source: str
    commit_timestamp: datetime | None = None
    is_head: bool = False


class SourceFinding(BaseModel):
    """Redacted finding produced from the current working tree."""

    model_config = ConfigDict(frozen=True)

    finding_id: str
    repository_path: str
    file_path: str
    line_number: int
    secret_type: str
    detector: str
    confidence: float
    secret_hash: str
    masked_preview: str
    status: Literal["open", "resolved", "ignored"]


class DedupedFinding(BaseModel):
    """One normalized secret aggregated across repository history."""

    model_config = ConfigDict(frozen=True)

    secret_id: str
    secret_type: str
    commit_hashes: list[str]
    first_seen_commit: str
    present_in_head: bool
    label_ground_truth: bool
    dataset_split: Literal["reference", "eval"]
