"""Differential Git history walker for added-line secret detection."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

import git

EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class HistoryLine:
    commit_sha: str
    parent_sha: str | None
    file_path: str
    line_number: int
    added_line: str
    masked_line: str
    still_in_head: bool
    git_lifecycle_state: str

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.pop("added_line", None)
        return payload


def _mask_line(line: str) -> str:
    """Redact common credential assignments in any externally persisted line."""
    return re.sub(
        r"(?i)((?:password|secret|token|key|uri|url)\s*[:=]\s*)[^\s#]+",
        r"\1[REDACTED]",
        line,
    )


def _head_line_hashes(repo: git.Repo) -> dict[str, set[str]]:
    hashes: dict[str, set[str]] = {}
    if not repo.head.is_valid():
        return hashes
    for item in repo.head.commit.tree.traverse():
        if not isinstance(item, git.Blob):
            continue
        try:
            text = item.data_stream.read().decode("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hashes[item.path] = {hashlib.sha256(line.strip().encode("utf-8")).hexdigest() for line in text.splitlines() if line.strip()}
    return hashes


def _reachable_head(repo: git.Repo) -> set[str]:
    if not repo.head.is_valid():
        return set()
    return {commit.hexsha for commit in repo.iter_commits("HEAD")}


def _ref_commits(repo: git.Repo) -> set[str]:
    result: set[str] = set()
    for ref in repo.refs:
        try:
            result.update(commit.hexsha for commit in repo.iter_commits(ref))
        except (git.GitCommandError, ValueError):
            continue
    return result


def _reflog_only_commits(repo: git.Repo) -> set[str]:
    try:
        all_commits = {line.strip() for line in repo.git.rev_list("--all", "--reflog").splitlines() if line.strip()}
        refs = {line.strip() for line in repo.git.rev_list("--all").splitlines() if line.strip()}
        return all_commits - refs
    except git.GitCommandError:
        return set()


def _commit_ids(repo: git.Repo) -> list[str]:
    if not repo.head.is_valid():
        try:
            output = repo.git.rev_list("--all", "--reflog")
        except git.GitCommandError:
            return []
    else:
        output = repo.git.rev_list("--all", "--reflog")
    return [line.strip() for line in output.splitlines() if line.strip()]


def _diff_added_lines(repo_path: str, parent: str, commit: str) -> Iterator[tuple[str, int, str]]:
    try:
        diff = subprocess.run(
            ["git", "diff", "--unified=0", "--no-ext-diff", parent, commit, "--"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Unable to diff commit {commit}") from exc
    current_file = ""
    next_line = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
            continue
        hunk = _HUNK_RE.match(raw)
        if hunk:
            next_line = int(hunk.group(1))
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            yield current_file, next_line, raw[1:]
            next_line += 1
        elif not raw.startswith("-") and current_file:
            next_line += 1


def walk_history(repo_path: str | Path) -> Iterator[HistoryLine]:
    """Yield only added lines from all refs and reflog-visible commits."""
    path = Path(repo_path).resolve()
    try:
        repo = git.Repo(path)
    except (git.InvalidGitRepositoryError, ValueError) as exc:
        raise ValueError(f"Not a Git repository: {path}") from exc
    head_hashes = _head_line_hashes(repo)
    head_commits = _reachable_head(repo)
    ref_commits = _ref_commits(repo)
    reflog_only = _reflog_only_commits(repo)
    for commit_sha in _commit_ids(repo):
        commit = repo.commit(commit_sha)
        parents = [parent.hexsha for parent in commit.parents] or [EMPTY_TREE_SHA]
        for parent_sha in parents:
            for file_path, line_number, added_line in _diff_added_lines(str(path), parent_sha, commit_sha):
                normalized = added_line.strip()
                still = hashlib.sha256(normalized.encode("utf-8")).hexdigest() in head_hashes.get(file_path, set())
                if commit_sha in reflog_only:
                    lifecycle = "REWRITTEN"
                elif commit_sha not in head_commits and commit_sha in ref_commits:
                    lifecycle = "BRANCH_TAG"
                elif still:
                    lifecycle = "ACTIVE_HEAD"
                else:
                    lifecycle = "DELETED_HISTORY"
                yield HistoryLine(
                    commit_sha=commit_sha,
                    parent_sha=None if parent_sha == EMPTY_TREE_SHA else parent_sha,
                    file_path=file_path,
                    line_number=line_number,
                    added_line=added_line,
                    masked_line=_mask_line(added_line),
                    still_in_head=still,
                    git_lifecycle_state=lifecycle,
                )


HistoryFinding = HistoryLine
walk_all_history = walk_history

__all__ = ["EMPTY_TREE_SHA", "HistoryFinding", "HistoryLine", "walk_all_history", "walk_history"]
