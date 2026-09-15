from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from .walker_db import (
    BlobRecordRow,
    SessionLocal,
    check_database,
    get_blobs_for_commit,
    get_commits,
    get_deleted_blobs,
    ingest_repo,
    init_db,
)

app = FastAPI(title="Secret History Detector")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    repo_path: str
    repo_id: str


class BlobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: str
    commit_hash: str
    commit_timestamp: datetime
    file_path: str
    blob_content: str
    is_head: bool


class CommitResponse(BaseModel):
    commit_hash: str
    commit_timestamp: datetime


def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/scan")
def scan(request: ScanRequest, session: Session = Depends(get_session)) -> dict[str, int]:
    try:
        count = ingest_repo(request.repo_path, request.repo_id, session)
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"blobs_written": count}


@app.get("/repos/{repo_id}/commits", response_model=list[CommitResponse])
def commits(repo_id: str, session: Session = Depends(get_session)) -> list[CommitResponse]:
    return [
        CommitResponse(commit_hash=row.commit_hash, commit_timestamp=row.commit_timestamp)
        for row in get_commits(repo_id, session)
    ]


@app.get("/repos/{repo_id}/commits/{commit_hash}/blobs", response_model=list[BlobResponse])
def commit_blobs(repo_id: str, commit_hash: str, session: Session = Depends(get_session)) -> list[BlobRecordRow]:
    return get_blobs_for_commit(repo_id, commit_hash, session)


@app.get("/repos/{repo_id}/deleted-blobs", response_model=list[BlobResponse])
def deleted_blobs(repo_id: str, session: Session = Depends(get_session)) -> list[BlobRecordRow]:
    return get_deleted_blobs(repo_id, session)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        check_database()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "db": "ok"}
