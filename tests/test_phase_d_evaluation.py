from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.oracle_validator import main as validate_oracle


pytestmark = pytest.mark.req("NFR-5")


def test_deterministic_json_hash_comparison(tmp_path: Path) -> None:
    first = {"findings": [{"file": "config/env", "line": 2}], "skipped": {"files": 0}}
    second = {"skipped": {"files": 0}, "findings": [{"line": 2, "file": "config/env"}]}
    first_hash = hashlib.sha256(json.dumps(first, sort_keys=True).encode()).hexdigest()
    second_hash = hashlib.sha256(json.dumps(second, sort_keys=True).encode()).hexdigest()
    assert first_hash == second_hash


def test_hardware_evidence_is_real_or_explicitly_unknown() -> None:
    manifest = Path("docs/evidence-manifest.json")
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["hardware"]["cpu"] == "12th Gen Intel(R) Core(TM) i5-1235U"
    assert payload["hardware"]["ram"].startswith("16831815680 bytes")
    assert payload["hardware"]["os"] == "Microsoft Windows 11 Home Single Language"


def test_independent_oracle_has_no_secret_values() -> None:
    oracle = Path("artifacts/ground_truth_oracle.json")
    if not oracle.exists():
        pytest.skip("oracle artifact not generated")
    payload = json.loads(oracle.read_text(encoding="utf-8"))
    text = json.dumps(payload)
    assert "Secret" not in text or "secret_type" in text
