from __future__ import annotations

import os
import tempfile
from pathlib import Path

import git
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mktemp(prefix='shd_api_', suffix='.sqlite3'))}"

from shd.walker_api import app  # noqa: E402
from tests.fixtures.make_synthetic_secret_repo import make_synthetic_secret_repo


def test_scan_api_persists_redacted_current_source_finding(tmp_path: Path) -> None:
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "API Fixture")
        config.set_value("user", "email", "api-fixture@example.test")
    (tmp_path / "config.py").write_text(
        "AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'\n",
        encoding="utf-8",
    )
    repo.index.add(["config.py"])
    repo.index.commit("Add fake credential")
    repo.close()

    with TestClient(app) as client:
        response = client.post("/scan", json={"repo_path": str(tmp_path), "repo_id": "api-fixture"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["findings_count"] == 1
        assert payload["scan_id"] == 1

        findings = client.get("/findings", params={"repo_id": "api-fixture"})
        assert findings.status_code == 200
        finding = findings.json()[0]
        assert finding["masked_preview"] != "AKIAIOSFODNN7EXAMPLE"
        assert finding["secret_hash"] != "AKIAIOSFODNN7EXAMPLE"
        assert finding["file_path"] == "config.py"

        commits = client.get("/repos/api-fixture/commits").json()
        blobs = client.get(f"/repos/api-fixture/commits/{commits[0]['commit_hash']}/blobs").json()
        assert "AKIAIOSFODNN7EXAMPLE" not in blobs[0]["blob_content"]

        scans = client.get("/scans")
        assert scans.json()[0]["files_scanned"] == 1


def test_history_scan_registers_commits_deleted_files_and_findings(tmp_path: Path) -> None:
    repo_path, _ = make_synthetic_secret_repo(str(tmp_path), repo_id="history-fixture")

    with TestClient(app) as client:
        response = client.post(
            "/scan",
            json={"repo_path": repo_path, "repo_id": "history-fixture", "analysis_mode": "history"},
        )

        assert response.status_code == 200
        assert response.json()["blobs_written"] > 0
        assert response.json()["findings_count"] > 0

        repositories = client.get("/repositories").json()
        assert any(item["repository_id"] == "history-fixture" for item in repositories)

        commits = client.get("/repos/history-fixture/commits").json()
        assert len(commits) == 2
        assert all(commit["short_hash"] == commit["commit_hash"][:8] for commit in commits)

        deleted = client.get("/repos/history-fixture/deleted-blobs").json()
        assert any(blob["file_path"] == "config.py" and blob["change_type"] == "deleted" for blob in deleted)

        historical = client.get("/historical-findings", params={"repo_id": "history-fixture"})
        assert historical.status_code == 200
        assert historical.json()
        assert all("AKIAIOSFODNN7EXAMPLE" not in item["masked_preview"] for item in historical.json())
        assert all(item["commit_hash"] in {commit["commit_hash"] for commit in commits} for item in historical.json())

        metrics = client.get("/metrics").json()
        assert metrics["commits_analyzed"] >= 2
        assert metrics["historical_findings"] > 0
        assert isinstance(metrics["historical_secrets"], int)


def test_scan_rejects_non_git_directory_with_actionable_error(tmp_path: Path) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/scan",
            json={"repo_path": str(tmp_path), "repo_id": "not-a-repo", "analysis_mode": "history"},
        )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Not a Git repository:")
