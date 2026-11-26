from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import baseline


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def test_clean_checkout_ignores_submodule_dirt_but_rejects_other_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.com")
    (root / "tracked.txt").write_text("parent\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "parent")

    submodule = root / "artifacts" / "synthetic_repo_v1"
    submodule.mkdir(parents=True)
    _git(submodule, "init")
    _git(submodule, "config", "user.name", "Test")
    _git(submodule, "config", "user.email", "test@example.com")
    (submodule / "fixture.txt").write_text("fixture\n", encoding="utf-8")
    _git(submodule, "add", "fixture.txt")
    _git(submodule, "commit", "-m", "fixture")
    _git(root, "add", "-f", "artifacts/synthetic_repo_v1")
    _git(root, "commit", "-m", "record fixture gitlink")

    monkeypatch.setattr(baseline, "ROOT", root)
    (submodule / "fixture.txt").write_text("changed fixture\n", encoding="utf-8")
    baseline._require_clean_checkout()

    (root / "unexpected.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unexpected.txt"):
        baseline._require_clean_checkout()
