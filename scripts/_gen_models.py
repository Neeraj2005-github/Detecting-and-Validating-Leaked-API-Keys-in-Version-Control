from pydantic import BaseModel, ConfigDict
from datetime import datetime


class BlobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    commit_hash: str
    commit_timestamp: datetime
    file_path: str
    blob_content: str
    is_head: bool
