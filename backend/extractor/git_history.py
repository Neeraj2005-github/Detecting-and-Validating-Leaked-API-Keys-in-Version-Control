from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import git


@dataclass
class CommitDiff:
    commit_sha: str
    author_date: str
    file_path: str
    diff_text: str


def _is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return True
    if not chunk:
        return False
    return b"\x00" in chunk


def extract_history(repo_path: str) -> Iterator[CommitDiff]:
    """Walk the FULL commit history (all branches reachable from HEAD, not just
    the tip) and yield one CommitDiff per changed file per commit.
    Must handle: empty repo (yield nothing, no exception), binary files (skip,
    do not attempt to decode), very large single commits (stream, do not load
    entire repo into memory at once)."""
    path = Path(repo_path)
    if not path.exists():
        return iter(())

    try:
        repo = git.Repo(str(path))
    except (git.InvalidGitRepositoryError, ValueError):
        return iter(())

    if not repo.head.is_valid():
        return iter(())

    def _iter() -> Iterator[CommitDiff]:
        for commit in repo.iter_commits(rev='HEAD', all=True):
            try:
                changed_paths = list(commit.stats.files.keys())
                if not changed_paths:
                    continue
                for file_path in changed_paths:
                    if not file_path:
                        continue
                    try:
                        blob = commit.tree / file_path
                    except Exception:
                        continue
                    try:
                        payload = blob.data_stream.read()
                    except Exception:
                        continue
                    if not payload or _is_binary_file(Path(repo.working_tree_dir) / file_path) if (repo.working_tree_dir and (Path(repo.working_tree_dir) / file_path).exists()) else False:
                        continue
                    try:
                        text = payload.decode("utf-8", errors="strict")
                    except Exception:
                        continue
                    yield CommitDiff(
                        commit_sha=commit.hexsha,
                        author_date=commit.authored_datetime.isoformat() if commit.authored_datetime else "",
                        file_path=file_path,
                        diff_text=text,
                    )
            except Exception:
                continue

    return _iter()
