import hashlib
from pathlib import Path

import pytest

from backend.detection.gitleaks_runner import run_gitleaks
from backend.detection.normalizer import RawFinding, normalize


def test_run_gitleaks_not_installed(monkeypatch):
    import backend.detection.gitleaks_runner as runner

    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="gitleaks"):
        runner.run_gitleaks(".")


def test_resolve_gitleaks_binary_rejects_missing_path(monkeypatch):
    import backend.detection.gitleaks_runner as runner

    monkeypatch.setattr(runner.shutil, "which", lambda name: "./definitely/not/here/gitleaks")
    with pytest.raises(RuntimeError, match="gitleaks"):
        runner._resolve_gitleaks_binary()


def test_run_gitleaks_seeded_repo():
    repo_path = Path("testdata/seeded_repo")
    if not repo_path.exists():
        pytest.skip("seeded repo has not been generated yet")

    result = run_gitleaks(str(repo_path))
    assert isinstance(result, list)
    assert len(result) > 0


def test_normalizer_hashes_secrets_and_strips_plaintext():
    secret = "AKIA1234567890ABCDEF"
    raw = [{"Commit": "abc123", "File": "config.env", "StartLine": 7, "RuleID": "aws-access-key", "Secret": secret}]
    findings = normalize(raw)

    assert len(findings) == 1
    assert isinstance(findings[0], RawFinding)
    assert findings[0].matched_string_hash == hashlib.sha256(secret.encode()).hexdigest()
    assert not any(secret in str(f).lower() for f in findings)
    assert findings[0].rule_id == "aws-access-key"
