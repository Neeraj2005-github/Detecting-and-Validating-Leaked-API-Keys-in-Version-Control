from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import git
import pytest

from backend.services.repository_ingestion import (
    _directory_size_bytes,
    validate_https_url,
)


def _local_repo(tmp_path: Path) -> Path:
    repo = git.Repo.init(tmp_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Phase A Fixture")
        config.set_value("user", "email", "phase-a@example.test")
    (tmp_path / "config.env").write_text(
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n",
        encoding="utf-8",
    )
    repo.index.add(["config.env"])
    repo.index.commit("Add fake credential")
    repo.close()
    return tmp_path


def test_cli_local_repo_json_end_to_end(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    env = os.environ.copy()
    env["SHD_HMAC_KEY"] = "FAKE_TEST_HMAC_KEY_NOT_A_SECRET"
    out = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.shd.cli",
            "scan",
            str(repo),
            "--format",
            "json",
            "--out",
            str(out),
            "--fail-on-findings",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=env,
    )
    assert completed.returncode == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["coverage"]["refs"]["branch_count"] >= 1
    assert payload["coverage"]["refs"]["tag_count"] >= 0
    assert payload["findings"]
    assert "AKIAIOSFODNN7EXAMPLE" not in out.read_text(encoding="utf-8")
    assert "commits=" in completed.stdout
    assert "exit-code=" in completed.stdout


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/repository.git",
        "ssh://git@example.test/repository.git",
        "ext::sh -c /bin/false",
        "http://example.test/repository.git",
    ],
)
def test_cli_rejects_forbidden_schemes(url: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "src.shd.cli", "scan", url],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 4


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/repository.git",
        "https://127.0.0.1/repository.git",
        "https://10.0.0.10/repository.git",
        "https://169.254.169.254/repository.git",
        "https://[::1]/repository.git",
    ],
)
def test_https_url_rejects_forbidden_addresses(url: str) -> None:
    with pytest.raises(ValueError):
        validate_https_url(url)


def test_https_url_accepts_only_a_resolved_public_host() -> None:
    with pytest.raises(ValueError):
        validate_https_url("https://localhost/repository.git")


def test_oversize_limit_helper(tmp_path: Path) -> None:
    (tmp_path / "small.bin").write_bytes(b"FAKE" * 16)
    assert _directory_size_bytes(tmp_path) == 64
