from pydantic import BaseModel, ConfigDict
from datetime import datetime


class BlobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    commit_hash: str
    commit_timestamp: datetime
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
