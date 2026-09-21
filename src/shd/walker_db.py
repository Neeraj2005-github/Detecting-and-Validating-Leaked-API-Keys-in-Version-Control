from __future__ import annotations

import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, delete, func, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .models import BlobRecord, SourceFinding
from .matcher import match
from .walker import walk_repository

load_dotenv()


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    project_root = Path(__file__).resolve().parents[2]
    sqlite_path = project_root / "runtime" / "shd-local.sqlite3"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path}"


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class RepositoryRow(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ScanRow(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("repositories.repository_id"),
        index=True,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    files_discovered: Mapped[int] = mapped_column(Integer, nullable=False)
    files_scanned: Mapped[int] = mapped_column(Integer, nullable=False)
    files_skipped: Mapped[int] = mapped_column(Integer, nullable=False)
    findings_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class FindingRow(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    scan_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    repository_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    secret_type: Mapped[str] = mapped_column(String(255), nullable=False)
    detector: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    masked_preview: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class BlobRecordRow(Base):
    __tablename__ = "blob_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    commit_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    blob_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_head: Mapped[bool] = mapped_column(Boolean, nullable=False)
    change_type: Mapped[str] = mapped_column(String(16), nullable=False, default="present")


class HistoricalFindingRow(Base):
    __tablename__ = "historical_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    repository_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    commit_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    secret_type: Mapped[str] = mapped_column(String(255), nullable=False)
    detector: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    masked_preview: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("blob_records")}
    if "change_type" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE blob_records ADD COLUMN change_type VARCHAR(16) NOT NULL DEFAULT 'present'")
            )

    finding_columns = {column["name"] for column in inspect(engine).get_columns("findings")}
    if "repository_id" not in finding_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE findings ADD COLUMN repository_id VARCHAR(255)"))

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE findings "
                "SET repository_id = ("
                "SELECT repository_id FROM repositories "
                "WHERE path LIKE '%seeded_repo%' "
                "OR repository_id LIKE '%seeded_repo%' "
                "ORDER BY id LIMIT 1) "
                "WHERE repository_id IS NULL OR repository_id = ''"
            )
        )


def ingest_repo(repo_path: str, repo_id: str, session: Session) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == repo_id))
    if repository is None:
        session.add(RepositoryRow(repository_id=repo_id, path=repo_path, created_at=now))
    else:
        repository.path = repo_path

    session.execute(delete(BlobRecordRow).where(BlobRecordRow.repo_id == repo_id))
    session.execute(delete(HistoricalFindingRow).where(HistoricalFindingRow.repository_id == repo_id))
    rows: list[BlobRecordRow] = []
    findings: list[HistoricalFindingRow] = []
    count = 0
    for record in walk_repository(repo_path):
        rows.append(_to_row(record, repo_id))
        findings.extend(_historical_finding_rows(record, repo_id))
        if len(rows) >= 500:
            session.add_all(rows)
            session.add_all(findings)
            count += len(rows)
            rows.clear()
            findings.clear()
    if rows:
        session.add_all(rows)
        session.add_all(findings)
        count += len(rows)
    session.commit()
    return count


def persist_source_scan(repo_path: str, repo_id: str, session: Session) -> tuple[int, int]:
    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    from .source_scanner import scan_source

    result = scan_source(repo_path)
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == repo_id))
    if repository is None:
        session.add(RepositoryRow(repository_id=repo_id, path=repo_path, created_at=started_at))
    else:
        repository.path = repo_path

    session.execute(delete(FindingRow).where(FindingRow.repository_id == repo_id))

    scan = ScanRow(
        repository_id=repo_id,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        files_discovered=result.files_discovered,
        files_scanned=result.files_scanned,
        files_skipped=result.files_skipped,
        findings_count=len(result.findings),
        status="completed",
    )
    session.add(scan)
    session.flush()
    session.add_all(
        [
            FindingRow(
                finding_id=finding.finding_id,
                scan_id=scan.id,
                repository_id=repo_id,
                file_path=finding.file_path,
                line_number=finding.line_number,
                secret_type=finding.secret_type,
                detector=finding.detector,
                confidence=finding.confidence,
                secret_hash=finding.secret_hash,
                masked_preview=finding.masked_preview,
                status=finding.status,
                created_at=scan.completed_at,
            )
            for finding in result.findings
        ]
    )
    session.commit()
    return scan.id, len(result.findings)


def _to_row(record: BlobRecord, repo_id: str) -> BlobRecordRow:
    return BlobRecordRow(
        repo_id=repo_id,
        commit_hash=record.commit_hash,
        commit_timestamp=record.commit_timestamp,
        file_path=record.file_path,
        blob_content=_redact_blob_content(record),
        is_head=record.is_head,
        change_type=record.change_type,
    )


def _redact_blob_content(record: BlobRecord) -> str:
    content = record.blob_content
    for finding in match(record):
        value = finding.matched_string.strip()
        if not value:
            continue
        preview = value if len(value) <= 8 else f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"
        content = content.replace(value, preview)
    return content


def get_commits(repo_id: str, session: Session) -> list[BlobRecordRow]:
    statement = (
        select(BlobRecordRow)
        .where(BlobRecordRow.repo_id == repo_id)
        .order_by(BlobRecordRow.commit_timestamp.desc())
    )
    rows = list(session.scalars(statement))
    seen: set[str] = set()
    return [row for row in rows if not (row.commit_hash in seen or seen.add(row.commit_hash))]


def get_blobs_for_commit(repo_id: str, commit_hash: str, session: Session) -> list[BlobRecordRow]:
    statement = (
        select(BlobRecordRow)
        .where(BlobRecordRow.repo_id == repo_id, BlobRecordRow.commit_hash == commit_hash)
        .order_by(BlobRecordRow.file_path)
    )
    return list(session.scalars(statement))


def get_deleted_blobs(repo_id: str, session: Session) -> list[BlobRecordRow]:
    statement = (
        select(BlobRecordRow)
        .where(BlobRecordRow.repo_id == repo_id, BlobRecordRow.change_type == "deleted")
        .order_by(BlobRecordRow.commit_timestamp.desc(), BlobRecordRow.file_path)
    )
    return list(session.scalars(statement))


def get_historical_findings(repo_id: str | None, session: Session) -> list[HistoricalFindingRow]:
    statement = select(HistoricalFindingRow).order_by(
        HistoricalFindingRow.commit_timestamp.desc(),
        HistoricalFindingRow.file_path,
        HistoricalFindingRow.line_number,
    )
    if repo_id:
        statement = statement.where(HistoricalFindingRow.repository_id == repo_id)
    return list(session.scalars(statement))


def _historical_finding_rows(record: BlobRecord, repo_id: str) -> list[HistoricalFindingRow]:
    from .source_scanner import _fingerprint, _mask

    rows = []
    for finding in match(record):
        secret_hash = _fingerprint(finding.matched_string)
        finding_id = hashlib.sha256(
            f"{repo_id}:{record.commit_hash}:{record.file_path}:{finding.line_number}:{finding.secret_type}:{secret_hash}".encode(
                "utf-8"
            )
        ).hexdigest()
        rows.append(
            HistoricalFindingRow(
                finding_id=finding_id,
                repository_id=repo_id,
                commit_hash=record.commit_hash,
                commit_timestamp=record.commit_timestamp,
                file_path=record.file_path,
                line_number=finding.line_number,
                secret_type=finding.secret_type,
                detector=finding.detector_source,
                confidence=finding.detector_confidence,
                secret_hash=secret_hash,
                masked_preview=_mask(finding.matched_string),
                status="historical",
            )
        )
    return rows


def check_database() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
