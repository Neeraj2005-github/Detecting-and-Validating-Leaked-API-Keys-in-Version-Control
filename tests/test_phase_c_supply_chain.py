from __future__ import annotations

from pathlib import Path

import pytest
import os

from backend.services.dependency_checker import (
    _binary_status,
    _database_status,
    _module_status,
    check_dependencies,
)
from backend.evaluation_metrics import _metrics
from backend.services.repository_ingestion import _is_public_ip
from backend.ml_filter.train import main as train_main


pytestmark = pytest.mark.req("NFR-1")


def test_dockerfile_is_pinned_nonroot_and_network_ready() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "v8.18.4" in dockerfile
    assert "sha256sum -c" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "--network none" in dockerfile


def test_readonly_root_repo_mount_contract_is_documented() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "repo mounted" in dockerfile or "bind mount" in dockerfile


def test_dependency_lockfiles_exist() -> None:
    assert Path("package-lock.json").is_file()
    assert Path("frontend/package-lock.json").is_file()
    assert Path("requirements.txt").is_file()


def test_dependency_readiness_helpers_are_offline_and_typed() -> None:
    assert isinstance(_module_status("git"), dict)
    assert isinstance(_binary_status("git", ["--version"]), dict)
    assert isinstance(_database_status(), dict)
    assert isinstance(check_dependencies(), dict)


def test_database_status_handles_unsupported_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://FAKE.example/test")
    status = _database_status()
    assert status["available"] is False
    assert status["backend"] == "unsupported"


def test_metrics_cover_tp_fp_fn_tn_and_empty_inputs() -> None:
    metric = _metrics([True, False, True, False], [True, True, False, False])
    assert metric["tp"] == 1
    assert metric["fp"] == 1
    assert metric["fn"] == 1
    assert metric["tn"] == 1
    assert _metrics([], [])["precision"] == 0.0


def test_public_ip_helper_rejects_reserved_addresses() -> None:
    assert not _is_public_ip("127.0.0.1")
    assert not _is_public_ip("10.0.0.1")
    assert not _is_public_ip("169.254.1.1")
    assert not _is_public_ip("not-an-ip")


def test_offline_model_training_smoke() -> None:
    train_main()
    assert Path("backend/ml_filter/model.pkl").is_file()
