from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

import git


_MAX_BLOB_BYTES = 10 * 1024 * 1024
_SEVERITY = {
    "private_key": 5,
    "aws_access_key": 5,
    "github_pat": 5,
    "mysql_uri": 4,
    "mongodb_uri": 4,
    "slack_token": 4,
    "stripe_token": 4,
    "jwt": 3,
    "db_password_assignment": 4,
    "generic_assignment": 3,
}
_EXPOSURE_FACTOR = {
    "ACTIVE_IN_HEAD": 1.0,
    "DELETED_BUT_RECOVERABLE": 0.7,
    "UNREACHABLE_LOCAL_ONLY": 0.45,
}
_RISK_WEIGHTS = {
    "lifecycle": 0.25,
    "secret_severity": 0.25,
    "exposure_duration": 0.20,
    "public_repository": 0.15,
    "entropy": 0.15,
}


def _read_blob(commit: git.Commit, file_path: str) -> bytes | None:
    try:
        blob = commit.tree / PurePosixPath(file_path).as_posix()
    except (KeyError, ValueError):
        return None
    if not isinstance(blob, git.Blob) or blob.size > _MAX_BLOB_BYTES:
        return None
    try:
        return blob.data_stream.read()
    except OSError:
        return None


def _commit_map(
    repo: git.Repo,
    file_path: str,
    local_commit_shas: set[str],
) -> dict[str, git.Commit]:
    commits = {commit.hexsha: commit for commit in repo.iter_commits("--all", paths=file_path)}
    for commit_sha in local_commit_shas - commits.keys():
        try:
            commit = repo.commit(commit_sha)
        except (git.BadName, ValueError):
            continue
        if _read_blob(commit, file_path) is not None:
            commits[commit.hexsha] = commit
    return commits


def _is_descendant(repo: git.Repo, ancestor_sha: str, descendant_sha: str) -> bool:
    try:
        repo.git.merge_base("--is-ancestor", ancestor_sha, descendant_sha)
    except git.GitCommandError:
        return False
    return True


def _analyze_group(
    repo: git.Repo,
    *,
    file_path: str,
    secret: str,
    report_commits: set[str],
    reachable_commit_shas: set[str],
    local_commit_shas: set[str],
    public_repo: bool,
    now: datetime,
) -> dict[str, Any]:
    secret_bytes = secret.encode("utf-8")
    commits = _commit_map(repo, file_path, local_commit_shas)
    ordered = sorted(commits.values(), key=lambda commit: (commit.committed_date, commit.hexsha))
    present = [
        commit for commit in ordered
        if (content := _read_blob(commit, file_path)) is not None and secret_bytes in content
    ]

    head_content = _read_blob(repo.head.commit, file_path) if repo.head.is_valid() else None
    active = head_content is not None and secret_bytes in head_content
    if present:
        first_seen = present[0]
        last_seen = present[-1]
    else:
        reported = [commits[sha] for sha in report_commits if sha in commits]
        if reported:
            first_seen = min(reported, key=lambda commit: (commit.committed_date, commit.hexsha))
            last_seen = max(reported, key=lambda commit: (commit.committed_date, commit.hexsha))
        else:
            return {
                "first_seen_commit": min(report_commits) if report_commits else "",
                "last_seen_commit": max(report_commits) if report_commits else "",
                "removed_in_commit": None,
                "days_exposed": 0.0,
                "lifecycle_status": "UNREACHABLE_LOCAL_ONLY",
                "recoverable_from_fresh_clone": False,
                "recoverable_from_local_objects": True,
                "public_repository": public_repo,
            }

    removed_in = None
    if not active:
        later_absent = [
            commit for commit in ordered
            if commit.committed_date > last_seen.committed_date
            and commit.hexsha not in {item.hexsha for item in present}
            and _is_descendant(repo, last_seen.hexsha, commit.hexsha)
        ]
        if later_absent:
            removed_in = min(later_absent, key=lambda commit: (commit.committed_date, commit.hexsha))

    report_reachable = any(sha in reachable_commit_shas for sha in report_commits)
    present_reachable = any(commit.hexsha in reachable_commit_shas for commit in present)
    if active:
        lifecycle_status = "ACTIVE_IN_HEAD"
    elif report_reachable or present_reachable:
        lifecycle_status = "DELETED_BUT_RECOVERABLE"
    else:
        lifecycle_status = "UNREACHABLE_LOCAL_ONLY"

    first_date = datetime.fromtimestamp(first_seen.committed_date, tz=timezone.utc)
    end_date = (
        datetime.fromtimestamp(removed_in.committed_date, tz=timezone.utc)
        if removed_in is not None
        else now if active
        else datetime.fromtimestamp(last_seen.committed_date, tz=timezone.utc)
    )
    days_exposed = max(0.0, (end_date - first_date).total_seconds() / 86400)
    return {
        "first_seen_commit": first_seen.hexsha,
        "last_seen_commit": last_seen.hexsha,
        "removed_in_commit": removed_in.hexsha if removed_in else None,
        "days_exposed": round(days_exposed, 2),
        "lifecycle_status": lifecycle_status,
        "recoverable_from_fresh_clone": lifecycle_status in {
            "ACTIVE_IN_HEAD",
            "DELETED_BUT_RECOVERABLE",
        },
        "recoverable_from_local_objects": lifecycle_status == "UNREACHABLE_LOCAL_ONLY",
        "public_repository": public_repo,
    }


def build_exposure_lifecycle(
    repo: git.Repo,
    raw_findings: list[dict[str, Any]],
    normalized_findings: list[Any],
    *,
    reachable_commit_shas: set[str],
    local_commit_shas: set[str],
    public_repo: bool = False,
    now: datetime | None = None,
) -> dict[tuple[str, int, str], dict[str, Any]]:
    """Derive exposure intervals while keeping raw values in process memory only."""
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw, normalized in zip(raw_findings, normalized_findings):
        secret = str(raw.get("Secret") or raw.get("Match") or "").strip().rstrip("\r\n")
        if not secret:
            continue
        file_path = str(raw.get("File") or raw.get("file") or "")
        rule_id = str(raw.get("RuleID") or raw.get("rule_id") or "")
        fingerprint = str(normalized.matched_string_hash)
        group_key = (file_path, rule_id, fingerprint)
        group = groups.setdefault(group_key, {"secret": secret, "occurrences": []})
        group["occurrences"].append((
            str(raw.get("Commit") or raw.get("commit") or ""),
            int(raw.get("StartLine") or raw.get("line") or 1),
        ))

    current_time = now or datetime.now(timezone.utc)
    lifecycle: dict[tuple[str, int, str], dict[str, Any]] = {}
    cache: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (file_path, rule_id, fingerprint), group in groups.items():
        report_commits = {commit_sha for commit_sha, _ in group["occurrences"] if commit_sha}
        cache_key = (file_path, rule_id, fingerprint)
        metadata = _analyze_group(
            repo,
            file_path=file_path,
            secret=group["secret"],
            report_commits=report_commits,
            reachable_commit_shas=reachable_commit_shas,
            local_commit_shas=local_commit_shas,
            public_repo=public_repo,
            now=current_time,
        )
        cache[cache_key] = metadata
        for commit_sha, line_number in group["occurrences"]:
            lifecycle[(file_path, line_number, commit_sha)] = metadata
    return lifecycle


def calculate_exposure_risk(finding: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Return a monotonic 0-100 risk score and its visible weighted terms."""
    secret_type = str(finding.get("secret_type", ""))
    severity = next(
        (value for secret_name, value in _SEVERITY.items() if secret_name in secret_type.lower()),
        3,
    )
    lifecycle = str(finding.get("lifecycle_status", "DELETED_BUT_RECOVERABLE"))
    factors = {
        "lifecycle": _EXPOSURE_FACTOR.get(lifecycle, 0.45),
        "secret_severity": severity / 5,
        "exposure_duration": min(max(float(finding.get("days_exposed", 0)) / 365, 0.0), 1.0),
        "public_repository": float(bool(finding.get("public_repository", False))),
        "entropy": min(max(float((finding.get("features") or {}).get("entropy", 0)) / 4, 0.0), 1.0),
    }
    terms = {
        name: {
            "weight": weight,
            "factor": factors[name],
            "points": round(100 * weight * factors[name], 2),
        }
        for name, weight in _RISK_WEIGHTS.items()
    }
    score = round(sum(term["points"] for term in terms.values()))
    return score, {
        "formula": "100 * (0.25*lifecycle + 0.25*severity + 0.20*duration + 0.15*public + 0.15*entropy)",
        "terms": terms,
        "score": score,
    }
