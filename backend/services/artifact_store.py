"""Persistence for privacy-safe CP1 experiment artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from src.shd.walker_db import CP1ArtifactRow, SessionLocal, init_db


def save_cp1_artifact(name: str, payload: dict[str, Any], path: str | Path) -> Path:
    """Write JSON and upsert the payload into the configured SQLAlchemy DB."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    try:
        init_db()
        with SessionLocal() as session:
            row = session.query(CP1ArtifactRow).filter_by(name=name).one_or_none()
            if row is None:
                row = CP1ArtifactRow(name=name, payload=payload)
                session.add(row)
            else:
                row.payload = payload
            session.commit()
    except SQLAlchemyError:
        # Artifact generation remains usable when an optional DB is offline;
        # callers still receive the durable JSON evidence.
        pass
    return output


def load_cp1_artifact(name: str, path: str | Path) -> dict[str, Any]:
    try:
        init_db()
        with SessionLocal() as session:
            row = session.query(CP1ArtifactRow).filter_by(name=name).one_or_none()
            if row is not None:
                return dict(row.payload)
    except SQLAlchemyError:
        pass
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
