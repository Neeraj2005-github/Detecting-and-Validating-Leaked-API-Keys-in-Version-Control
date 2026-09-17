from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .models import BlobRecord, SourceFinding
from .matcher import match
from .walker import walk_repository

load_dotenv()


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "3306")
    database = os.getenv("DB_NAME")
    missing = [
        name
        for name, value in {
            "DB_USER": user,
            "DB_PASS": password,
            "DB_HOST": host,
            "DB_NAME": database,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Configure an external MySQL database with DATABASE_URL or: "
            + ", ".join(missing)
        )
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


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
    repository_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
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


def init_db() -> None:
    Base.metadata.create_all(engine)


def ingest_repo(repo_path: str, repo_id: str, session: Session) -> int:
    rows: list[BlobRecordRow] = []
    count = 0
    for record in walk_repository(repo_path):
        rows.append(_to_row(record, repo_id))
        if len(rows) >= 500:
            session.add_all(rows)
            count += len(rows)
            rows.clear()
    if rows:
        session.add_all(rows)
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
        .where(BlobRecordRow.repo_id == repo_id, BlobRecordRow.is_head.is_(False))
        .order_by(BlobRecordRow.commit_timestamp.desc(), BlobRecordRow.file_path)
    )
    return list(session.scalars(statement))


def check_database() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
