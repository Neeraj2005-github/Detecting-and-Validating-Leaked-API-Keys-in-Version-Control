from __future__ import annotations

import os
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import git


KNOWN_ARCHIVE_SUFFIXES = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z"}
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_LINE_LENGTH = 1024 * 1024
EXCLUDED_DIRECTORY_NAMES = {"node_modules", "vendor", "target", "build", "dist", ".vite", ".mvn"}
EXCLUDED_FILE_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}


def _skipped_summary(path: Path) -> dict[str, Any]:
    by_reason: dict[str, dict[str, int]] = {}
    items: list[dict[str, Any]] = []

    def add(file_path: Path, reason: str, line_count: int = 0) -> None:
        bucket = by_reason.setdefault(reason, {"files": 0, "lines": 0})
        bucket["files"] += 1
        bucket["lines"] += line_count
        items.append({
            "path": file_path.relative_to(path).as_posix() if file_path.is_relative_to(path) else str(file_path),
            "reason": reason,
            "lines": line_count,
        })

    for current_root, directories, filenames in os.walk(path):
        kept_directories = []
        for name in sorted(directories):
            directory = Path(current_root) / name
            if name in EXCLUDED_DIRECTORY_NAMES:
                add(directory, "dependency_path")
                continue
            if name not in {".git", ".venv", "__pycache__"}:
                kept_directories.append(name)
        directories[:] = kept_directories
        for filename in sorted(filenames):
            file_path = Path(current_root) / filename
            lower_name = filename.lower()
            if (
                filename in EXCLUDED_FILE_NAMES
                or lower_name.endswith(".min.js")
                or lower_name.endswith(".lock")
                or lower_name.endswith(".md")
                or lower_name.endswith(".class")
                or lower_name.endswith(".jar")
            ):
                add(file_path, "generated_or_dependency_file")
                continue
            if file_path.is_symlink():
                add(file_path, "symlink")
                continue
            suffix = file_path.suffix.lower()
            if suffix in KNOWN_ARCHIVE_SUFFIXES:
                add(file_path, "archive")
                continue
            if filename == ".gitmodules":
                add(file_path, "submodule", len(file_path.read_text(errors="replace").splitlines()) if file_path.exists() else 0)
                continue
            try:
                data = file_path.read_bytes()
            except OSError:
                add(file_path, "unreadable")
                continue
            if len(data) > MAX_FILE_BYTES:
                add(file_path, "oversized")
                continue
            if b"\x00" in data:
                add(file_path, "binary")
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                add(file_path, "binary")
                continue
            lines = text.splitlines()
            if any(len(line) > MAX_LINE_LENGTH for line in lines):
                add(file_path, "too_long", len(lines))
                continue
            if text.startswith("version https://git-lfs.github.com/spec/v1"):
                add(file_path, "lfs_pointer", len(lines))

    files = sum(bucket["files"] for bucket in by_reason.values())
    lines = sum(bucket["lines"] for bucket in by_reason.values())
    return {
        "files": files,
        "lines": lines,
        "by_reason": by_reason,
        "items": items,
    }


def build_coverage(
    repo_path: str | Path,
    *,
    commits_scanned: int | None = None,
    skipped_items: list[str] | None = None,
    skipped_threshold: int | None = None,
) -> dict[str, Any]:
    path = Path(repo_path).resolve()
    repo = git.Repo(path)
    branches = sorted(
        ref.name.removeprefix("refs/heads/")
        for ref in repo.refs
        if ref.path.startswith("refs/heads/")
    )
    tags = sorted(
        ref.name.removeprefix("refs/tags/")
        for ref in repo.refs
        if ref.path.startswith("refs/tags/")
    )
    try:
        reachable = sorted(set(repo.git.rev_list("--all").splitlines()))
    except git.GitCommandError:
        reachable = []
    try:
        local_commits = set(repo.git.rev_list("--all", "--reflog").splitlines())
    except git.GitCommandError:
        local_commits = set(reachable)
    try:
        shallow = repo.git.rev_parse("--is-shallow-repository").strip() == "true"
    except git.GitCommandError:
        shallow = True

    unreachable = 0
    unreachable_commit_shas: set[str] = set()
    try:
        fsck = subprocess.run(
            ["git", "fsck", "--unreachable", "--no-reflogs"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
        unreachable_lines = [
            line for line in fsck.stdout.splitlines()
            if line.startswith("unreachable ")
        ]
        unreachable = len(unreachable_lines)
        unreachable_commit_shas = {
            line.split()[2]
            for line in unreachable_lines
            if len(line.split()) >= 3 and line.split()[1] == "commit"
        }
    except (OSError, subprocess.TimeoutExpired):
        unreachable = -1

    scanned_skips = skipped_items or []
    disk_skips = _skipped_summary(path)
    if scanned_skips:
        disk_skips["items"].extend(
            {"path": "unknown", "reason": str(item), "lines": 0}
            for item in scanned_skips
        )
        disk_skips["files"] += len(scanned_skips)

    threshold = skipped_threshold
    if threshold is None:
        try:
            threshold = int(os.getenv("SHD_SKIPPED_THRESHOLD", "100"))
        except ValueError:
            threshold = 100
    threshold_exceeded = disk_skips["files"] + disk_skips["lines"] > max(0, threshold)
    skipped_items_count = disk_skips["files"] + disk_skips["lines"]
    manifest = {
        "refs": {
            "branches": branches,
            "tags": tags,
            "branch_count": len(branches),
            "tag_count": len(tags),
        },
        "commits_reachable": len(reachable),
        "commits_actually_scanned": len(reachable) if commits_scanned is None else int(commits_scanned),
        "commits_reachable_shas": reachable,
        "local_commit_shas": sorted(local_commits | unreachable_commit_shas),
        "unreachable_commit_shas": sorted(unreachable_commit_shas),
        "shallow": shallow,
        "unreachable_object_count": unreachable,
        "skipped_items": [item["reason"] for item in disk_skips["items"]],
        "skipped": disk_skips,
        "skipped_threshold": max(0, threshold),
        "skipped_threshold_exceeded": threshold_exceeded,
        "skipped_items_count": skipped_items_count,
        "completeness": "complete" if not shallow and unreachable >= 0 and not threshold_exceeded else "incomplete",
        "human_summary": (
            f"branches={len(branches)}, tags={len(tags)}, reachable_commits={len(reachable)}, "
            f"scanned_commits={len(reachable) if commits_scanned is None else int(commits_scanned)}, "
            f"shallow={str(shallow).lower()}, skipped_files={disk_skips['files']}, "
            f"skipped_lines={disk_skips['lines']}, completeness={'complete' if not shallow and unreachable >= 0 and not threshold_exceeded else 'incomplete'}"
        ),
    }
    return manifest


def assert_scan_complete(
    repo_path: str | Path,
    *,
    commits_scanned: int | None = None,
    skipped_items: list[str] | None = None,
    skipped_threshold: int | None = None,
) -> dict[str, Any]:
    manifest = build_coverage(
        repo_path,
        commits_scanned=commits_scanned,
        skipped_items=skipped_items,
        skipped_threshold=skipped_threshold,
    )
    if manifest["shallow"]:
        raise ValueError("SHALLOW_REPOSITORY_REFUSED")
    if manifest["commits_actually_scanned"] < manifest["commits_reachable"]:
        raise RuntimeError("SCAN_COVERAGE_MISMATCH")
    if manifest["skipped_threshold_exceeded"]:
        raise RuntimeError("SCAN_SKIPPED_THRESHOLD_EXCEEDED")
    return manifest
