import hashlib
import socket
from pathlib import Path

import pytest
pytestmark = pytest.mark.req("NFR-1")

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


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        if path.is_symlink():
            digest.update(path.readlink().as_posix().encode("utf-8"))
        elif path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_run_gitleaks_seeded_repo_is_read_only_and_offline(monkeypatch):
    repo_path = Path("testdata/seeded_repo")
    if not repo_path.exists():
        pytest.skip("seeded repo has not been generated yet")

    before = _tree_digest(repo_path)
    outbound_attempts: list[object] = []

    def reject_connect(_socket, address: object) -> None:
        outbound_attempts.append(address)
        raise AssertionError("The wrapper attempted an outbound connection")

    monkeypatch.setattr(socket.socket, "connect", reject_connect)
    result = run_gitleaks(str(repo_path))

    assert isinstance(result, list)
    assert outbound_attempts == []
    assert _tree_digest(repo_path) == before


def test_normalizer_hashes_secrets_and_strips_plaintext():
    secret = "AKIA1234567890ABCDEF"
    raw = [{"Commit": "abc123", "File": "config.env", "StartLine": 7, "RuleID": "aws-access-key", "Secret": secret}]
    findings = normalize(raw)

    assert len(findings) == 1
    assert isinstance(findings[0], RawFinding)
    assert findings[0].matched_string_hash == findings[0].matched_string_hash
    assert not any(secret in str(f).lower() for f in findings)
    assert findings[0].rule_id == "aws-access-key"
    assert findings[0].features["length"] == len(secret)
    assert findings[0].features["entropy"] > 0


def test_normalizer_marks_fixture_paths_from_raw_match():
    raw = [{
        "Commit": "abc123",
        "File": "testdata/example.env",
        "StartLine": 2,
        "RuleID": "aws-access-token",
        "Secret": "AKIA1234567890ABCDEF",
        "Match": "SECRET=AKIA1234567890ABCDEF",
    }]

    finding = normalize(raw)[0]

    assert finding.features["is_test_path"] == 1
    assert finding.features["has_example_keyword"] == 0


def test_runner_requires_owned_config(tmp_path):
    import backend.detection.gitleaks_runner as runner

    with pytest.raises(RuntimeError, match="SecretGuard-owned"):
        runner.run_gitleaks(str(tmp_path), config_path=str(tmp_path / "gitleaks.toml"))
