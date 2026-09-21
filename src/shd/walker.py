from __future__ import annotations

import shutil
import tempfile
from datetime import timezone
from pathlib import Path
from typing import Iterator

import git
from git import Blob, Tree

from .models import BlobRecord


def validate_repository(repo_path: str) -> str:
    """Validate and normalize a local Git repository path."""
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Not a Git repository: {root}")
    try:
        repo = git.Repo(str(root), search_parent_directories=False)
        repo.git.rev_parse("--is-inside-work-tree")
    except (git.NoSuchPathError, git.InvalidGitRepositoryError, git.GitCommandError) as exc:
        raise ValueError(f"Not a Git repository: {root}") from exc
    finally:
        if "repo" in locals():
            repo.close()
    return str(root)


def get_commit_details(repo_path: str, commit_hash: str) -> dict[str, object]:
    """Return reproducible metadata for one local Git commit."""
    repo = git.Repo(repo_path)
    try:
        commit = repo.commit(commit_hash)
        parent = commit.parents[0] if commit.parents else None
        diff_index = parent.diff(commit) if parent is not None else commit.diff(git.NULL_TREE)
        changed_files = []
        for diff_item in diff_index:
            path = diff_item.b_path or diff_item.a_path
            stats = commit.stats.files.get(path) or commit.stats.files.get(diff_item.a_path or "") or {}
            change_type = str(diff_item.change_type or "M").lower()
            changed_files.append(
                {
                    "path": path,
                    "old_path": diff_item.a_path if diff_item.a_path != path else None,
                    "status": {
                        "a": "added",
                        "d": "deleted",
                        "m": "modified",
                        "r": "renamed",
                        "c": "renamed",
                    }.get(change_type, change_type),
                    "insertions": stats.get("insertions", 0),
                    "deletions": stats.get("deletions", 0),
                }
            )
        return {
            "commit_hash": commit.hexsha,
            "short_hash": commit.hexsha[:8],
            "message": commit.message.strip(),
            "author": str(commit.author),
            "commit_timestamp": commit.authored_datetime,
            "parent_hash": parent.hexsha if parent else None,
            "parents": [item.hexsha for item in commit.parents],
            "changed_files": sorted(changed_files, key=lambda item: item["path"]),
        }
    finally:
        repo.close()


def _build_head_map(repo: git.Repo) -> dict[str, str]:
    try:
        head_commit = repo.head.commit
    except Exception:
        return {}
    result: dict[str, str] = {}
    for item in head_commit.tree.traverse():
        if item.type == "blob":
            result[item.path] = item.hexsha
    return result


def _decode_blob(blob: Blob) -> str:
    try:
        raw = blob.data_stream.read()
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _blob_at_path(tree: Tree, path: str) -> Blob | None:
    try:
        item = tree[path]
    except (KeyError, IndexError):
        return None
    return item if isinstance(item, Blob) else None


def walk_repository(repo_path: str) -> Iterator[BlobRecord]:
    tmpdir: str | None = None
    is_remote = repo_path.startswith(("http://", "https://", "git://", "git@", "ssh://"))
    if is_remote:
        tmpdir = tempfile.mkdtemp(prefix="shd_clone_")
        repo = git.Repo.clone_from(repo_path, tmpdir)
    else:
        repo = git.Repo(validate_repository(repo_path))
    try:
        yield from _walk_repo(repo)
    finally:
        repo.close()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def _walk_repo(repo: git.Repo) -> Iterator[BlobRecord]:
    head_map = _build_head_map(repo)

    branch_tips: dict[str, git.Commit] = {}
    for ref in repo.refs:
        try:
            commit = ref.commit
            branch_tips[commit.hexsha] = commit
        except Exception:
            continue

    if not branch_tips:
        try:
            commit = repo.head.commit
            branch_tips[commit.hexsha] = commit
        except Exception:
            return

    seen_commits: set[str] = set()

    for tip in branch_tips.values():
        for commit in repo.iter_commits(tip):
            if commit.hexsha in seen_commits:
                continue
            seen_commits.add(commit.hexsha)

            timestamp = commit.authored_datetime
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            blobs_in_commit: set[str] = set()
            change_types = _change_types_for_commit(commit)
            for item in commit.tree.traverse():
                if item.type != "blob":
                    continue
                blobs_in_commit.add(item.path)
                yield BlobRecord(
                    commit_hash=commit.hexsha,
                    commit_timestamp=timestamp,
                    file_path=item.path,
                    blob_content=_decode_blob(item),
                    is_head=head_map.get(item.path) == item.hexsha,
                    change_type=change_types.get(item.path, "present"),
                )

            if not commit.parents:
                continue

            parent = commit.parents[0]
            try:
                diffs = parent.diff(commit)
            except Exception:
                continue

            for diff_item in diffs:
                if diff_item.change_type != "D":
                    continue
                deleted_path = diff_item.a_path
                if deleted_path in blobs_in_commit:
                    continue
                parent_blob = _blob_at_path(parent.tree, deleted_path)
                if parent_blob is None:
                    continue
                yield BlobRecord(
                    commit_hash=commit.hexsha,
                    commit_timestamp=timestamp,
                    file_path=deleted_path,
                    blob_content=_decode_blob(parent_blob),
                    is_head=False,
                    change_type="deleted",
                )


def _change_types_for_commit(commit: git.Commit) -> dict[str, str]:
    parent = commit.parents[0] if commit.parents else git.NULL_TREE
    try:
        diffs = parent.diff(commit)
    except Exception:
        return {}

    result: dict[str, str] = {}
    for diff_item in diffs:
        path = diff_item.b_path or diff_item.a_path
        change_type = str(diff_item.change_type or "M").lower()
        result[path] = {
            "a": "added",
            "d": "deleted",
            "m": "modified",
            "r": "renamed",
            "c": "renamed",
        }.get(change_type, "present")
    return result
