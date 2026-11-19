import json

import pytest

from backend.services.audit_log import append_audit, verify_chain
from backend.services.report_parser import validate_gitleaks_report


def test_audit_chain_detects_tampering(tmp_path):
    path = tmp_path / "audit.json"
    append_audit(path, "tester", "scan", "finding-1")
    append_audit(path, "tester", "report", "finding-1")
    assert verify_chain(path)
    entries = json.loads(path.read_text(encoding="utf-8"))
    entries[0]["action"] = "tampered"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert not verify_chain(path)


def test_gitleaks_parser_rejects_schema_change():
    with pytest.raises(ValueError, match="missing required fields"):
        validate_gitleaks_report([{"RuleID": "rule"}])
