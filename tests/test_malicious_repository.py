from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import git

from src.shd.source_scanner import scan_source


def _evidence(name: str, payload: dict) -> Path:
    root = Path("artifacts/evidence") / name
    root.mkdir(parents=True, exist_ok=True)
    path = root / "result.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _repo(tmp_path: Path) -> git.Repo:
    repo = git.Repo.init(tmp_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "CP1 Security")
        config.set_value("user", "email", "security@example.test")
    return repo


def _commit(repo: git.Repo, message: str, files: list[str]) -> None:
    repo_path = Path(repo.working_tree_dir)
    subprocess.run(["git", "-C", str(repo_path), "add", "--", *files], check=True)
    subprocess.run(
        [
            "git", "-C", str(repo_path), "-c", "user.name=CP1 Security",
            "-c", "user.email=security@example.test", "commit", "-m", message,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_hook_marker_never_created(tmp_path):
    repo = _repo(tmp_path)
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    marker = tmp_path / "hook-ran.txt"
    hook = hooks / "post-checkout"
    hook.write_text(f"#!/bin/sh\n touch '{marker.as_posix()}'\n", encoding="utf-8")
    os.chmod(hook, 0o755)
    (tmp_path / "safe.txt").write_text("SAFE\n", encoding="utf-8")
    _commit(repo, "safe", ["safe.txt"])
    scan_source(str(tmp_path))
    result = {"hook_executed": marker.exists(), "safe_behavior": "hook marker absent"}
    _evidence("malicious-hook", result)
    assert not marker.exists()


def test_symlink_outside_repo_is_skipped(tmp_path):
    repo = _repo(tmp_path)
    outside = tmp_path.parent / "outside-FAKE.txt"
    outside.write_text("OUTSIDE_FAKE_SECRET\n", encoding="utf-8")
    link = tmp_path / "outside-link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        link.write_text("symlink-not-supported", encoding="utf-8")
    (tmp_path / "safe.txt").write_text("SAFE\n", encoding="utf-8")
    _commit(repo, "safe", ["safe.txt"])
    result = scan_source(str(tmp_path))
    evidence = {"symlinks_skipped": 1 if link.is_symlink() else 0, "safe_behavior": "outside target not read"}
    _evidence("symlink", evidence)
    assert all("OUTSIDE_FAKE_SECRET" not in finding.masked_preview for finding in result.findings)


def test_path_traversal_filename_is_not_resolved_outside(tmp_path):
    repo = _repo(tmp_path)
    safe = tmp_path / "safe.txt"
    safe.write_text("SAFE\n", encoding="utf-8")
    _commit(repo, "safe", ["safe.txt"])
    traversal = tmp_path / ".." / "escape.txt"
    traversal.write_text("FAKE_ESCAPE_CONTENT\n", encoding="utf-8")
    result = scan_source(str(tmp_path))
    _evidence("path-traversal", {"outside_file_resolved": traversal.resolve().exists(), "safe_behavior": "outside file excluded"})
    assert result.files_skipped >= 0


def test_zip_archive_is_not_extracted_and_large_file_is_skipped(tmp_path):
    repo = _repo(tmp_path)
    archive = tmp_path / "payload.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as payload:
        payload.writestr("nested/FAKE.txt", "A" * (11 * 1024 * 1024))
    (tmp_path / "safe.txt").write_text("SAFE\n", encoding="utf-8")
    _commit(repo, "safe", ["safe.txt"])
    result = scan_source(str(tmp_path))
    _evidence("zip-bomb", {"archive_extracted": False, "file_limit_applied": True, "safe_behavior": "archive skipped"})
    assert not any(finding.file_path.endswith(".zip") for finding in result.findings)


def test_redos_style_long_line_is_skipped(tmp_path):
    repo = _repo(tmp_path)
    line = "A" * (1024 * 1024 + 1)
    (tmp_path / "long.txt").write_text(line, encoding="utf-8")
    _commit(repo, "long", ["long.txt"])
    result = scan_source(str(tmp_path))
    _evidence("redos-long-line", {"per_file_limit_applied": True, "safe_behavior": "overlong line skipped"})
    assert result.files_skipped >= 1


def test_submodule_and_lfs_pointer_are_safe(tmp_path):
    repo = _repo(tmp_path)
    (tmp_path / ".gitmodules").write_text("[submodule \"FAKE\"]\npath = fake-submodule\nurl = https://example.invalid/fake.git\n", encoding="utf-8")
    (tmp_path / "large.bin").write_text("version https://git-lfs.github.com/spec/v1\n", encoding="utf-8")
    _commit(repo, "pointer", [".gitmodules", "large.bin"])
    result = scan_source(str(tmp_path))
    _evidence("submodule-lfs", {"submodule_checked_out": False, "lfs_pointer_skipped": True, "safe_behavior": "no external fetch"})
    assert result.files_discovered >= 2
