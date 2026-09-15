from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .models import BlobRecord
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


def _to_row(record: BlobRecord, repo_id: str) -> BlobRecordRow:
    return BlobRecordRow(
        repo_id=repo_id,
        commit_hash=record.commit_hash,
        commit_timestamp=record.commit_timestamp,
        file_path=record.file_path,
        blob_content=record.blob_content,
        is_head=record.is_head,
    )


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
