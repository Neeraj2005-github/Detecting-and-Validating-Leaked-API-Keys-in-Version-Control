from __future__ import annotations

from datetime import datetime
from typing import Literal

import git
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .walker_db import (
    BlobRecordRow,
    FindingRow,
    RepositoryRow,
    ScanRow,
    SessionLocal,
    check_database,
    get_blobs_for_commit,
    get_commits,
    get_deleted_blobs,
    ingest_repo,
    init_db,
    persist_source_scan,
)
from .walker import get_commit_details

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
    analysis_mode: Literal["current", "history", "full"] = "full"


class ScanResponse(BaseModel):
    scan_id: int
    analysis_mode: str
    blobs_written: int
    findings_count: int


class MetricsResponse(BaseModel):
    repositories: int
    scans: int
    commits_analyzed: int
    files_scanned: int
    historical_files_recovered: int
    secrets_detected: int
    current_secrets: int
    historical_secrets: int | None
    high_confidence_findings: int


class FindingResponse(BaseModel):
    id: int
    finding_id: str
    scan_id: int
    repository_id: str
    file_path: str
    line_number: int
    secret_type: str
    detector: str
    confidence: float
    secret_hash: str
    masked_preview: str
    status: str


class ScanSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: str
    files_discovered: int
    files_scanned: int
    files_skipped: int
    findings_count: int
    status: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int


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
    model_config = ConfigDict(from_attributes=True)

    commit_hash: str
    commit_timestamp: datetime
    message: str | None = None
    author: str | None = None
    parent_hash: str | None = None


class CommitDetailsResponse(BaseModel):
    commit_hash: str
    message: str
    author: str
    commit_timestamp: datetime
    parent_hash: str | None
    changed_files: list[dict[str, object]]


def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/scan", response_model=ScanResponse)
def scan(request: ScanRequest, session: Session = Depends(get_session)) -> ScanResponse:
    try:
        count = 0
        findings_count = 0
        scan_id = 0
        if request.analysis_mode in {"history", "full"}:
            count = ingest_repo(request.repo_path, request.repo_id, session)
        if request.analysis_mode in {"current", "full"}:
            scan_id, findings_count = persist_source_scan(request.repo_path, request.repo_id, session)
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail="repository scan failed") from exc
    return ScanResponse(
        scan_id=scan_id,
        analysis_mode=request.analysis_mode,
        blobs_written=count,
        findings_count=findings_count,
    )


@app.get("/scans", response_model=list[ScanSummaryResponse])
def scans(session: Session = Depends(get_session)) -> list[ScanSummaryResponse]:
    rows = list(session.scalars(select(ScanRow).order_by(ScanRow.completed_at.desc())))
    return [
        ScanSummaryResponse(
            id=row.id,
            repository_id=row.repository_id,
            files_discovered=row.files_discovered,
            files_scanned=row.files_scanned,
            files_skipped=row.files_skipped,
            findings_count=row.findings_count,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            duration_ms=max(0, int((row.completed_at - row.started_at).total_seconds() * 1000)),
        )
        for row in rows
    ]


@app.get("/findings", response_model=list[FindingResponse])
def findings(repo_id: str | None = None, session: Session = Depends(get_session)) -> list[FindingResponse]:
    statement = select(FindingRow).order_by(FindingRow.created_at.desc())
    if repo_id:
        statement = statement.where(FindingRow.repository_id == repo_id)
    rows = list(session.scalars(statement))
    return [FindingResponse.model_validate(row, from_attributes=True) for row in rows]


@app.get("/repositories")
def repositories(session: Session = Depends(get_session)) -> list[dict[str, object]]:
    rows = list(session.scalars(select(RepositoryRow).order_by(RepositoryRow.created_at.desc())))
    return [{"repository_id": row.repository_id, "path": row.path} for row in rows]


@app.get("/metrics", response_model=MetricsResponse)
def metrics(session: Session = Depends(get_session)) -> MetricsResponse:
    commit_rows = session.execute(select(BlobRecordRow.repo_id, BlobRecordRow.commit_hash)).all()
    return MetricsResponse(
        repositories=session.scalar(select(func.count()).select_from(RepositoryRow)) or 0,
        scans=session.scalar(select(func.count()).select_from(ScanRow)) or 0,
        commits_analyzed=len({(repo_id, commit_hash) for repo_id, commit_hash in commit_rows}),
        files_scanned=session.scalar(select(func.coalesce(func.sum(ScanRow.files_scanned), 0))) or 0,
        historical_files_recovered=session.scalar(
            select(func.count()).select_from(BlobRecordRow).where(BlobRecordRow.is_head.is_(False))
        ) or 0,
        secrets_detected=session.scalar(select(func.count()).select_from(FindingRow)) or 0,
        current_secrets=session.scalar(select(func.count()).select_from(FindingRow)) or 0,
        historical_secrets=None,
        high_confidence_findings=session.scalar(
            select(func.count()).select_from(FindingRow).where(FindingRow.confidence >= 0.8)
        ) or 0,
    )


@app.get("/repos/{repo_id}/commits", response_model=list[CommitResponse])
def commits(repo_id: str, session: Session = Depends(get_session)) -> list[CommitResponse]:
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == repo_id))
    rows = get_commits(repo_id, session)
    if repository is None:
        return []
    result = []
    for row in rows:
        try:
            details = get_commit_details(repository.path, row.commit_hash)
        except Exception:
            details = {}
        result.append(
            CommitResponse(
                commit_hash=row.commit_hash,
                commit_timestamp=row.commit_timestamp,
                message=details.get("message"),
                author=details.get("author"),
                parent_hash=details.get("parent_hash"),
            )
        )
    return result


@app.get("/repos/{repo_id}/commits/{commit_hash}", response_model=CommitDetailsResponse)
def commit_details(repo_id: str, commit_hash: str, session: Session = Depends(get_session)) -> CommitDetailsResponse:
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == repo_id))
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")
    try:
        return CommitDetailsResponse(**get_commit_details(repository.path, commit_hash))
    except (git.BadName, ValueError, OSError) as exc:
        raise HTTPException(status_code=404, detail="commit not found") from exc


@app.get("/findings/{finding_id}", response_model=FindingResponse)
def finding_detail(finding_id: str, session: Session = Depends(get_session)) -> FindingResponse:
    row = session.scalar(select(FindingRow).where(FindingRow.finding_id == finding_id))
    if row is None:
        raise HTTPException(status_code=404, detail="finding not found")
    return FindingResponse.model_validate(row, from_attributes=True)


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
