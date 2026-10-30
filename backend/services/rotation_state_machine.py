"""Deterministic offline credential rotation state machine."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.artifact_store import save_cp1_artifact

STATES = ("DETECTED", "SANDBOX_VALIDATING", "ROTATING_CREDENTIAL", "VERIFIED_SAFE", "FAILED_ROLLBACK")


@dataclass
class RotationStateMachine:
    credential_id: str
    transitions: list[dict[str, Any]] = field(default_factory=list)
    state: str = "DETECTED"
    started_ns: int = field(default_factory=time.perf_counter_ns)

    def _transition(self, state: str, detail: str) -> None:
        self.state = state
        self.transitions.append({"state": state, "timestamp": datetime.now(timezone.utc).isoformat(), "detail": detail})

    def run(self, *, force_failure: bool = False) -> dict[str, Any]:
        try:
            self._transition("DETECTED", "synthetic finding accepted")
            self._transition("SANDBOX_VALIDATING", "SQLite in-memory sandbox selected")
            connection = sqlite3.connect(":memory:")
            connection.execute("CREATE TABLE credentials (id TEXT PRIMARY KEY, active INTEGER)")
            connection.execute("INSERT INTO credentials VALUES (?, 1)", (self.credential_id,))
            self._transition("ROTATING_CREDENTIAL", "synthetic credential replaced")
            connection.execute("UPDATE credentials SET active=0 WHERE id=?", (self.credential_id,))
            if force_failure:
                raise RuntimeError("deterministic rotation failure requested")
            safe = connection.execute("SELECT active FROM credentials WHERE id=?", (self.credential_id,)).fetchone()[0] == 0
            self._transition("VERIFIED_SAFE" if safe else "FAILED_ROLLBACK", "post-rotation verification")
            connection.close()
        except (sqlite3.Error, RuntimeError) as exc:
            self._transition("FAILED_ROLLBACK", type(exc).__name__)
        payload = {"credential_id": self.credential_id, "state": self.state, "transitions": self.transitions, "mttr_ms": (time.perf_counter_ns() - self.started_ns) / 1_000_000, "sandbox": "sqlite-in-memory-offline"}
        save_cp1_artifact("rotation_state_machine", payload, Path(__file__).resolve().parents[2] / "artifacts" / "rotation_state_machine.json")
        return payload


def rotate(credential_id: str, *, force_failure: bool = False) -> dict[str, Any]:
    return RotationStateMachine(credential_id).run(force_failure=force_failure)
