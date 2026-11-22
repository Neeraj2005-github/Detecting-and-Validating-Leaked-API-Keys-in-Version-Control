from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.req("NFR-5")


def test_freeze_refuses_without_confirm() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/freeze.py"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 2
    assert "Refusing" in completed.stdout


def test_required_phase_f_documents_exist() -> None:
    for relative in (
        "docs/adr-wrapper-over-fork.md",
        "docs/threat-model.md",
        "docs/ethics-and-legal-scope.md",
        "docs/traceability_matrix.md",
        "docs/evidence-manifest.json",
        "SECURITY.md",
        "CODEOWNERS",
    ):
        assert Path(relative).is_file(), relative


def test_evidence_manifest_is_valid_json() -> None:
    payload = json.loads(Path("docs/evidence-manifest.json").read_text(encoding="utf-8"))
    assert "gitleaks" in payload
