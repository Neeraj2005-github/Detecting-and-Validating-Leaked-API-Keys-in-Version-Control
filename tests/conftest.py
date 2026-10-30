"""Failure evidence hook for CP1/O2 test execution."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


FAILURE_LOG = Path(__file__).resolve().parents[1] / "artifacts" / "failure_log.json"


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]) -> None:
    if call.when != "call" or call.excinfo is None:
        return
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(FAILURE_LOG.read_text(encoding="utf-8")) if FAILURE_LOG.exists() else []
    except (OSError, json.JSONDecodeError):
        existing = []
    existing.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test": item.nodeid,
        "exception": call.excinfo.type.__name__,
        "message": str(call.excinfo.value),
    })
    FAILURE_LOG.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
