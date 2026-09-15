from __future__ import annotations

import shutil
import tempfile
from datetime import timezone
from typing import Iterator

import git
from git import Blob, Tree

from .models import BlobRecord


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
        repo = git.Repo(repo_path)
    try:
        yield from _walk_repo(repo)
    finally:
        repo.close()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def _walk_repo(repo: git.Repo) -> Iterator[BlobRecord]:
    head_map = _build_head_map(repo)

    branch_tips: dict[str, git.Commit] = {}
    remote_refs = [ref for remote in repo.remotes for ref in remote.refs]
    for ref in list(repo.branches) + remote_refs:
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
                )
