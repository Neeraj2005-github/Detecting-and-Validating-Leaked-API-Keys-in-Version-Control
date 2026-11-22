from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.audit_log import append_audit, verify_chain
from backend.services.rotation_state_machine import (
    ALLOWED_TRANSITIONS,
    STATES,
    RotationStateMachine,
)


pytestmark = [pytest.mark.req("FR-6"), pytest.mark.req("NFR-6")]


def test_every_allowed_transition_is_accepted() -> None:
    for source, targets in ALLOWED_TRANSITIONS.items():
        for target in targets:
            machine = RotationStateMachine("FAKE_FINDING")
            machine.state = source
            machine.transition(target, "FAKE_TEST_TRANSITION")
            assert machine.state == target


def test_every_forbidden_transition_is_rejected() -> None:
    for source in STATES:
        allowed = ALLOWED_TRANSITIONS[source]
        for target in STATES:
            if target not in allowed:
                machine = RotationStateMachine("FAKE_FINDING")
                machine.state = source
                with pytest.raises(ValueError, match="FORBIDDEN_TRANSITION"):
                    machine.transition(target, "FAKE_FORBIDDEN_TRANSITION")


def test_unknown_state_is_rejected() -> None:
    machine = RotationStateMachine("FAKE_FINDING")
    with pytest.raises(ValueError, match="UNKNOWN_LIFECYCLE_STATE"):
        machine.transition("UNKNOWN_FAKE_STATE", "fake")


def test_rotation_force_failure_stays_unverified(tmp_path: Path) -> None:
    result = RotationStateMachine("FAKE_CREDENTIAL").run(force_failure=True)
    assert result["state"] == "VALIDITY_UNKNOWN"


def test_audit_hash_chain_detects_tampering(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    append_audit(audit, "FAKE_ACTOR", "DETECTED", "FAKE_FINDING")
    append_audit(audit, "FAKE_ACTOR", "ROTATED", "FAKE_FINDING")
    assert verify_chain(audit)
    entries = json.loads(audit.read_text(encoding="utf-8"))
    entries[0]["action"] = "TAMPERED"
    audit.write_text(json.dumps(entries), encoding="utf-8")
    assert not verify_chain(audit)
