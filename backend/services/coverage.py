from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import git


def build_coverage(
    repo_path: str | Path,
    *,
    commits_scanned: int | None = None,
    skipped_items: list[str] | None = None,
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
        shallow = repo.git.rev_parse("--is-shallow-repository").strip() == "true"
    except git.GitCommandError:
        shallow = True

    unreachable = 0
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
        unreachable = sum(
            1 for line in fsck.stdout.splitlines()
            if line.startswith("unreachable ")
        )
    except (OSError, subprocess.TimeoutExpired):
        unreachable = -1

    return {
        "refs": {
            "branches": branches,
            "tags": tags,
            "branch_count": len(branches),
            "tag_count": len(tags),
        },
        "commits_reachable": len(reachable),
        "commits_actually_scanned": len(reachable) if commits_scanned is None else int(commits_scanned),
        "commits_reachable_shas": reachable,
        "shallow": shallow,
        "unreachable_object_count": unreachable,
        "skipped_items": skipped_items or [],
        "completeness": "complete" if not shallow and unreachable >= 0 else "incomplete",
    }


def assert_scan_complete(
    repo_path: str | Path,
    *,
    commits_scanned: int | None = None,
    skipped_items: list[str] | None = None,
) -> dict[str, Any]:
    manifest = build_coverage(
        repo_path,
        commits_scanned=commits_scanned,
        skipped_items=skipped_items,
    )
    if manifest["shallow"]:
        raise ValueError("SHALLOW_REPOSITORY_REFUSED")
    if manifest["commits_actually_scanned"] < manifest["commits_reachable"]:
        raise RuntimeError("SCAN_COVERAGE_MISMATCH")
    return manifest
