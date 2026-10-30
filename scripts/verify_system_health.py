"""One-click readiness check for the local API, model, and rotation sandbox."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
HEALTH_URL = os.getenv("HEALTH_URL", "http://localhost:8000/health")
MODEL_PATH = ROOT / "backend" / "ml" / "detector_model.pkl"


def check_api() -> None:
    try:
        with urlopen(HEALTH_URL, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"backend health check failed: {type(exc).__name__}") from exc
    if payload.get("status") != "ok" or payload.get("db") != "ok":
        raise RuntimeError(f"backend health check returned {payload!r}")


def check_model() -> None:
    if not MODEL_PATH.is_file() or MODEL_PATH.stat().st_size == 0:
        raise RuntimeError(f"detector model is missing or empty: {MODEL_PATH}")


def check_rotation_sandbox() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE credentials (id TEXT PRIMARY KEY, active INTEGER)")
        connection.execute("INSERT INTO credentials VALUES (?, 1)", ("health-check",))
        connection.execute("UPDATE credentials SET active = 0 WHERE id = ?", ("health-check",))
        active = connection.execute(
            "SELECT active FROM credentials WHERE id = ?", ("health-check",)
        ).fetchone()
    finally:
        connection.close()
    if active != (0,):
        raise RuntimeError("rotation sandbox verification failed")


def main() -> int:
    checks = (
        ("Backend API and database", check_api),
        ("Persisted ML model", check_model),
        ("SQLite rotation sandbox", check_rotation_sandbox),
    )
    try:
        for name, check in checks:
            check()
            print(f"[OK] {name}")
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        print("SYSTEM HEALTH CHECK FAILED - NOT READY FOR PRESENTATION", file=sys.stderr)
        return 1
    print("ALL SYSTEMS GO - READY FOR PRESENTATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
