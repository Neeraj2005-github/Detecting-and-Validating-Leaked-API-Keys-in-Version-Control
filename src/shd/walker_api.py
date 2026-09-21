from __future__ import annotations

import json
import hashlib
import logging
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import git
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from .walker_db import (
    BlobRecordRow,
    FindingRow,
    HistoricalFindingRow,
    RepositoryRow,
    ScanRow,
    SessionLocal,
    check_database,
    get_blobs_for_commit,
    get_commits,
    get_deleted_blobs,
    get_historical_findings,
    ingest_repo,
    init_db,
    persist_source_scan,
)
from .walker import get_commit_details, validate_repository
from backend.pipeline import run_pipeline

logger = logging.getLogger(__name__)
BASELINE_METRICS_PATH = Path(__file__).resolve().parents[2] / "reports" / "baseline_metrics.json"

app = FastAPI(title="Secret History Detector")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    repo_path: str
    repo_id: str
    analysis_mode: Literal["current", "history", "full"] = "full"


class RepositoryRequest(BaseModel):
    url: str


def _validate_repository_url(value: str) -> str:
    url = value.strip()
    if not url:
        raise HTTPException(status_code=400, detail="repository URL is required")
    if url.startswith("git@"):
        return url
    parsed = urllib.parse.urlparse(url)
    is_remote_url = parsed.scheme.lower() in {"http", "https", "git", "ssh"} and bool(parsed.netloc)
    is_local_path = (
        url.startswith((".", "/", "~"))
        or "\\" in url
        or "/" in url
        or (len(url) >= 2 and url[1] == ":")
    )
    if not (is_remote_url or is_local_path):
        raise HTTPException(status_code=400, detail="repository URL is malformed")
    return url


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
    historical_findings: int
    total_findings: int


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
    change_type: str


class CommitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    commit_hash: str
    commit_timestamp: datetime
    message: str | None = None
    author: str | None = None
    parent_hash: str | None = None
    short_hash: str | None = None
    parents: list[str] = []


class CommitDetailsResponse(BaseModel):
    commit_hash: str
    message: str
    author: str
    commit_timestamp: datetime
    parent_hash: str | None
    short_hash: str | None = None
    parents: list[str] = []
    changed_files: list[dict[str, object]]


class HistoricalFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: str
    repository_id: str
    commit_hash: str
    commit_timestamp: datetime
    file_path: str
    line_number: int
    secret_type: str
    detector: str
    confidence: float
    secret_hash: str
    masked_preview: str
    status: str


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
        if not request.repo_path.startswith(("http://", "https://", "git://", "git@", "ssh://")):
            request.repo_path = validate_repository(request.repo_path)
        count = 0
        findings_count = 0
        scan_id = 0
        if request.analysis_mode in {"history", "full"}:
            count = ingest_repo(request.repo_path, request.repo_id, session)
            if request.analysis_mode == "history":
                findings_count = session.scalar(
                    select(func.count()).select_from(HistoricalFindingRow).where(
                        HistoricalFindingRow.repository_id == request.repo_id
                    )
                ) or 0
        if request.analysis_mode in {"current", "full"}:
            scan_id, findings_count = persist_source_scan(request.repo_path, request.repo_id, session)
    except ValueError as exc:
        session.rollback()
        logger.warning("Repository scan rejected: repository=%s error=%s", request.repo_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        session.rollback()
        logger.exception("Repository scan failed: repository=%s operation=scan", request.repo_id)
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
    statement = select(FindingRow)
    if repo_id is not None:
        repository_key = repo_id
        if repo_id.isdigit():
            repository_key = session.scalar(
                select(RepositoryRow.repository_id).where(RepositoryRow.id == int(repo_id))
            )
            if repository_key is None:
                return []
        statement = statement.where(FindingRow.repository_id == repository_key)
    statement = statement.order_by(FindingRow.created_at.desc())
    rows = list(session.scalars(statement))
    return [FindingResponse.model_validate(row, from_attributes=True) for row in rows]


@app.post("/repositories")
def add_repository(request: RepositoryRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    url = _validate_repository_url(request.url)
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == url))
    if repository is None:
        repository = RepositoryRow(
            repository_id=url,
            path=url,
            created_at=datetime.utcnow(),
        )
        session.add(repository)
        session.commit()
        session.refresh(repository)
    return {"id": str(repository.id), "url": repository.path, "last_scan": None, "finding_count": 0}


@app.put("/repositories/{repository_id}")
def update_repository(repository_id: str, request: RepositoryRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    try:
        repo_id = int(repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid repository id") from exc

    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.id == repo_id))
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")

    updated_url = _validate_repository_url(request.url)
    previous_repository_id = repository.repository_id
    repository.repository_id = updated_url
    repository.path = updated_url

    if previous_repository_id != updated_url:
        session.execute(update(FindingRow).where(FindingRow.repository_id == previous_repository_id).values(repository_id=updated_url))
        session.execute(update(ScanRow).where(ScanRow.repository_id == previous_repository_id).values(repository_id=updated_url))
        session.execute(update(HistoricalFindingRow).where(HistoricalFindingRow.repository_id == previous_repository_id).values(repository_id=updated_url))
        session.execute(update(BlobRecordRow).where(BlobRecordRow.repo_id == previous_repository_id).values(repo_id=updated_url))

    session.commit()
    session.refresh(repository)
    return {
        "id": str(repository.id),
        "url": repository.path,
        "last_scan": session.scalar(
            select(ScanRow.completed_at)
            .where(ScanRow.repository_id == repository.repository_id)
            .order_by(ScanRow.completed_at.desc())
            .limit(1)
        ),
        "finding_count": session.scalar(
            select(func.count()).select_from(FindingRow).where(FindingRow.repository_id == repository.repository_id)
        ) or 0,
    }


@app.delete("/repositories/{repository_id}", status_code=204)
def delete_repository(repository_id: str, session: Session = Depends(get_session)) -> Response:
    try:
        repo_id = int(repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid repository id") from exc

    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.id == repo_id))
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")

    repository_key = repository.repository_id
    session.execute(delete(FindingRow).where(FindingRow.repository_id == repository_key))
    session.execute(delete(HistoricalFindingRow).where(HistoricalFindingRow.repository_id == repository_key))
    session.execute(delete(BlobRecordRow).where(BlobRecordRow.repo_id == repository_key))
    session.execute(delete(ScanRow).where(ScanRow.repository_id == repository_key))
    session.execute(delete(RepositoryRow).where(RepositoryRow.id == repo_id))
    session.commit()
    return Response(status_code=204)


@app.get("/repositories")
def repositories(session: Session = Depends(get_session)) -> list[dict[str, object]]:
    rows = list(session.scalars(select(RepositoryRow).order_by(RepositoryRow.created_at.desc())))
    result = []
    for row in rows:
        last_scan = session.scalar(
            select(ScanRow.completed_at)
            .where(ScanRow.repository_id == row.repository_id)
            .order_by(ScanRow.completed_at.desc())
            .limit(1)
        )
        finding_count = session.scalar(
            select(func.count()).select_from(FindingRow).where(FindingRow.repository_id == row.repository_id)
        ) or 0
        result.append({
            "id": str(row.id),
            "repository_id": row.repository_id,
            "url": row.path,
            "last_scan": last_scan,
            "finding_count": finding_count,
        })
    return result


@app.post("/repositories/{repository_id}/scan")
def scan_repository(repository_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    try:
        repository = session.scalar(select(RepositoryRow).where(RepositoryRow.id == int(repository_id)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid repository id") from exc
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        pipeline_findings = run_pipeline(repository.path)
        session.execute(delete(FindingRow).where(FindingRow.repository_id == repository.repository_id))
        completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        scan = ScanRow(
            repository_id=repository.repository_id,
            started_at=started_at,
            completed_at=completed_at,
            files_discovered=0,
            files_scanned=0,
            files_skipped=0,
            findings_count=len(pipeline_findings),
            status="completed",
        )
        session.add(scan)
        session.flush()
        session.add_all([
            FindingRow(
                finding_id=hashlib.sha256(
                    f"{repository.repository_id}:{finding.get('commit_sha')}:{finding.get('file')}:{finding.get('line')}".encode()
                ).hexdigest(),
                scan_id=scan.id,
                repository_id=repository.repository_id,
                file_path=str(finding.get("file", "")),
                line_number=int(finding.get("line", 1)),
                secret_type=str(finding.get("secret_type", "generic_high_entropy")),
                detector=str(finding.get("rule_id", "gitleaks")),
                confidence=float(finding.get("ml_confidence", 0.0)),
                secret_hash=str(finding.get("secret_hash", "")),
                masked_preview=f"****{str(finding.get('secret_hash', ''))[-4:]}",
                status="open",
                created_at=completed_at,
            )
            for finding in pipeline_findings
        ])
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("Repository scan failed: repository=%s", repository.repository_id)
        raise HTTPException(status_code=400, detail="repository scan failed") from exc

    return {
        "repository_id": repository.repository_id,
        "scan_id": scan.id,
        "last_scan": completed_at,
        "finding_count": len(pipeline_findings),
    }


@app.get("/metrics", response_model=MetricsResponse)
def metrics(session: Session = Depends(get_session)) -> MetricsResponse:
    commit_rows = session.execute(select(BlobRecordRow.repo_id, BlobRecordRow.commit_hash)).all()
    current_hashes = set(session.scalars(select(FindingRow.secret_hash)))
    historical_hashes = set(session.scalars(select(HistoricalFindingRow.secret_hash)))
    historical_findings = session.scalar(select(func.count()).select_from(HistoricalFindingRow)) or 0
    return MetricsResponse(
        repositories=session.scalar(select(func.count()).select_from(RepositoryRow)) or 0,
        scans=session.scalar(select(func.count()).select_from(ScanRow)) or 0,
        commits_analyzed=len({(repo_id, commit_hash) for repo_id, commit_hash in commit_rows}),
        files_scanned=session.scalar(select(func.coalesce(func.sum(ScanRow.files_scanned), 0))) or 0,
        historical_files_recovered=session.scalar(
            select(func.count(func.distinct(BlobRecordRow.file_path)))
            .select_from(BlobRecordRow)
            .where(BlobRecordRow.is_head.is_(False))
        ) or 0,
        secrets_detected=len(current_hashes | historical_hashes),
        current_secrets=len(current_hashes),
        historical_secrets=len(historical_hashes),
        high_confidence_findings=(session.scalar(
            select(func.count()).select_from(FindingRow).where(FindingRow.confidence >= 0.8)
        ) or 0) + (session.scalar(
            select(func.count()).select_from(HistoricalFindingRow).where(HistoricalFindingRow.confidence >= 0.8)
        ) or 0),
        historical_findings=historical_findings,
        total_findings=(session.scalar(select(func.count()).select_from(FindingRow)) or 0) + historical_findings,
    )


@app.get("/metrics/baseline")
def baseline_metrics(response: Response) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    if not BASELINE_METRICS_PATH.exists():
        raise HTTPException(status_code=404, detail="baseline metrics report not found")
    return json.loads(BASELINE_METRICS_PATH.read_text(encoding="utf-8"))


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
                short_hash=details.get("short_hash"),
                parents=details.get("parents", []),
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


@app.get("/historical-findings", response_model=list[HistoricalFindingResponse])
def historical_findings(
    repo_id: str | None = None,
    session: Session = Depends(get_session),
) -> list[HistoricalFindingResponse]:
    return [
        HistoricalFindingResponse.model_validate(row, from_attributes=True)
        for row in get_historical_findings(repo_id, session)
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
