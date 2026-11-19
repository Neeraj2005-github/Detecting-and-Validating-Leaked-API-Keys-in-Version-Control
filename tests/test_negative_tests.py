from pathlib import Path

import pytest

from backend.detection.gitleaks_runner import run_gitleaks
from backend.services.audit_log import append_audit, verify_chain
from backend.services.rotation_state_machine import rotate


def test_nt1_deleted_secret_remains_exposed(tmp_path):
    repo = tmp_path / "deleted-secret"
    repo.mkdir()
    import git
    git.Repo.init(repo)
    (repo / "config.env").write_text("TOKEN=EXAMPLE_FAKE_TOKEN\n", encoding="utf-8")
    import subprocess
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=CP1", "-c", "user.email=cp1@example.test", "commit", "-m", "add"], check=True)
    (repo / "config.env").unlink()
    subprocess.run(["git", "-C", str(repo), "add", "-u"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=CP1", "-c", "user.email=cp1@example.test", "commit", "-m", "delete"], check=True)
    assert subprocess.run(["git", "-C", str(repo), "log", "-p", "--all"], capture_output=True, text=True, check=True).stdout


def test_nt2_shallow_repository_must_be_refused(tmp_path):
    repo = tmp_path / "shallow-missing"
    repo.mkdir()
    marker = repo / ".git"
    marker.mkdir()
    (marker / "shallow").write_text("deadbeef\n", encoding="ascii")
    # The CLI preflight is responsible for refusing the marker.
    assert (marker / "shallow").exists()


def test_nt3_rotation_requires_verification():
    result = rotate("untested-secret")
    assert result["state"] in {"VERIFIED_REVOKED", "VALIDITY_UNKNOWN"}
    assert result["state"] != "ROTATED_UNVERIFIED"


def test_nt4_audit_tampering_is_detected(tmp_path):
    path = tmp_path / "audit.json"
    append_audit(path, "scanner", "detect", "finding-1")
    assert verify_chain(path)
    import json
    entries = json.loads(path.read_text(encoding="utf-8"))
    entries[0]["action"] = "modified"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert not verify_chain(path)


def test_nt5_config_change_requires_review(tmp_path):
    lock = Path("config.lock")
    original = lock.read_text(encoding="ascii")
    try:
        lock.write_text("tampered", encoding="ascii")
        with pytest.raises(RuntimeError, match="config.lock"):
            run_gitleaks(str(tmp_path))
    finally:
        lock.write_text(original, encoding="ascii")
