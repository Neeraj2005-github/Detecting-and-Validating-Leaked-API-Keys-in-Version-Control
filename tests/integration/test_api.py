from __future__ import annotations

import os
import tempfile
from pathlib import Path

import git
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mktemp(prefix='shd_api_', suffix='.sqlite3'))}"

from shd.walker_api import app  # noqa: E402


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
