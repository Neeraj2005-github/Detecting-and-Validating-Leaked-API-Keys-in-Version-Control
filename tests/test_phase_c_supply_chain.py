from __future__ import annotations

from pathlib import Path

import pytest


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
