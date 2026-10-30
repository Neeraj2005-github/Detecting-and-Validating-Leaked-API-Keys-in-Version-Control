"""O1.1 Problem Reproduction Engine for SecretGuard.

This module programmatically constructs a temporary Git repository that
demonstrates the core problem SecretGuard addresses: **deleted secrets remain
fully recoverable in Git history** even after they are removed from the
working tree.

The reproduction follows a deterministic three-commit timeline:

1. Commit 1 – add ``config/prod.env`` containing realistic AWS / DB secrets.
2. Commit 2 – delete ``config/prod.env`` (simulating a "fix").
3. Commit 3 – add normal application code (``app/main.py``).

After building the repo the engine runs ``git log -p --all`` and
``git rev-list --all`` via *subprocess* to prove the secret is still
reachable, then returns a structured verification result.

Public API
----------
* :func:`run_reproduction` – build the repo, verify, return result dict.
* :func:`save_artifacts`  – persist the result to JSON + Markdown files.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from git import Actor, Repo  # GitPython

__all__ = ["run_reproduction", "save_artifacts"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SECRET_MARKER = "AKIAIOSFODNN7EXAMPLE"
"""A distinctive substring used to check whether the AWS key is present."""

_PROD_ENV_CONTENT = textwrap.dedent(
    """\
    # Production Configuration - DO NOT COMMIT
    AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
    AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    DATABASE_URL=mysql://admin:SuperSecret123!@prod-db.internal:3306/myapp
    """
)

_APP_MAIN_CONTENT = textwrap.dedent(
    '''\
    """Minimal FastAPI application – normal, non-secret code."""

    from fastapi import FastAPI

    app = FastAPI(title="MyApp", version="0.1.0")


    @app.get("/")
    async def root() -> dict[str, str]:
        """Health-check / hello-world endpoint."""
        return {"message": "Hello, World!"}
    '''
)

_AUTHOR = Actor("SecretGuard Bot", "secretguard-bot@example.com")


def _mask_sensitive_diff(value: str) -> str:
    """Keep persisted evidence useful without persisting credential material."""
    replacements = {
        "AKIAIOSFODNN7EXAMPLE": "[REDACTED_AWS_ACCESS_KEY]",
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY": "[REDACTED_AWS_SECRET]",
        "mysql://prod-db.internal:3306/myapp": "[REDACTED_MYSQL_URI]",
        "******prod-db.internal:3306/myapp": "[REDACTED_MYSQL_URI]",
    }
    for plaintext, replacement in replacements.items():
        value = value.replace(plaintext, replacement)
    value = re.sub(
        r"(?im)(DATABASE_URL=)[^\r\n]*",
        r"\1[REDACTED_DATABASE_URI]",
        value,
    )
    return value

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_git_command(
    args: List[str],
    cwd: str,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a raw ``git`` CLI command via *subprocess* and return the result.

    Parameters
    ----------
    args:
        Arguments *after* ``git``, e.g. ``["log", "-p", "--all"]``.
    cwd:
        Working directory (the repo root).
    check:
        If *True* (default) raise on non-zero exit.

    Returns
    -------
    subprocess.CompletedProcess[str]
    """
    full_cmd = ["git"] + args
    logger.debug("Running: %s (cwd=%s)", " ".join(full_cmd), cwd)
    return subprocess.run(
        full_cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _build_timeline(repo: Repo) -> List[Dict[str, Any]]:
    """Walk commits oldest-first and return a serialisable timeline list.

    Each entry contains:
    * ``sha`` – full 40-char hex SHA.
    * ``message`` – first line of the commit message.
    * ``timestamp`` – ISO-8601 authored date (UTC).
    * ``files_changed`` – list of file paths touched by the commit.
    """
    timeline: List[Dict[str, Any]] = []
    for commit in repo.iter_commits("HEAD", reverse=True):
        # Diff against parent (or empty tree for the root commit).
        # ``--root`` is required for the first commit; without it Git reports
        # an empty file list for a root commit.
        dt = subprocess.run(
            ["git", "diff-tree", "--root", "--no-commit-id", "-r", "--name-only", commit.hexsha],
            cwd=str(repo.working_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        files_changed = sorted({f.strip() for f in dt.stdout.splitlines() if f.strip()})

        timeline.append(
            {
                "sha": commit.hexsha,
                "message": commit.message.strip().split("\n", 1)[0],
                "timestamp": commit.authored_datetime.astimezone(timezone.utc).isoformat(),
                "files_changed": files_changed,
            }
        )
    return timeline


def _check_working_tree_for_secret(repo_path: str) -> bool:
    """Return whether ``HEAD`` still contains the marker in tracked content."""
    result = subprocess.run(
        ["git", "grep", "--fixed-strings", "--quiet", _SECRET_MARKER, "HEAD", "--"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Unable to inspect HEAD for the reproduction marker: {result.stderr.strip()}")
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_reproduction(
    repo_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a temporary Git repo and verify that deleted secrets persist in history.

    Parameters
    ----------
    repo_dir:
        Optional path for the repository.  When *None* a directory is created
        inside the system temp folder (and **not** cleaned up so it can be
        inspected afterwards).

    Returns
    -------
    dict
        Structured result with keys ``repo_path``, ``timeline``,
        ``diff_output``, ``rev_list``, ``verification``, and ``status``.

    Raises
    ------
    RuntimeError
        If the Git CLI is unavailable or a subprocess command fails
        unexpectedly.
    """
    # ------------------------------------------------------------------ setup
    if repo_dir is None:
        repo_dir = tempfile.mkdtemp(prefix="secretguard_o1_")
    repo_path = str(Path(repo_dir).resolve())
    logger.info("Creating reproduction repository at %s", repo_path)

    try:
        repo = Repo.init(repo_path)
        # Configure user for commits so GitPython doesn't complain.
        with repo.config_writer() as cw:
            cw.set_value("user", "name", _AUTHOR.name)
            cw.set_value("user", "email", _AUTHOR.email)

        # ------------------------------------------------------ Commit 1
        config_dir = Path(repo_path) / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        prod_env = config_dir / "prod.env"
        prod_env.write_text(_PROD_ENV_CONTENT, encoding="utf-8")

        repo.index.add(["config/prod.env"])
        commit1 = repo.index.commit(
            "Add production configuration",
            author=_AUTHOR,
            committer=_AUTHOR,
        )
        logger.info("Commit 1 (%s): %s", commit1.hexsha[:8], commit1.message.strip())

        # ------------------------------------------------------ Commit 2
        prod_env.unlink()
        repo.index.remove(["config/prod.env"], working_tree=True)
        commit2 = repo.index.commit(
            "Removed sensitive file",
            author=_AUTHOR,
            committer=_AUTHOR,
        )
        logger.info("Commit 2 (%s): %s", commit2.hexsha[:8], commit2.message.strip())

        # ------------------------------------------------------ Commit 3
        app_dir = Path(repo_path) / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "main.py").write_text(_APP_MAIN_CONTENT, encoding="utf-8")

        repo.index.add(["app/main.py"])
        commit3 = repo.index.commit(
            "Add application entrypoint",
            author=_AUTHOR,
            committer=_AUTHOR,
        )
        logger.info("Commit 3 (%s): %s", commit3.hexsha[:8], commit3.message.strip())

        # ----------------------------------------- subprocess verification
        log_result = _run_git_command(["log", "-p", "--all"], cwd=repo_path)
        raw_diff_output: str = log_result.stdout
        diff_output: str = _mask_sensitive_diff(raw_diff_output)

        revlist_result = _run_git_command(["rev-list", "--all"], cwd=repo_path)
        rev_list: List[str] = [
            line.strip() for line in revlist_result.stdout.splitlines() if line.strip()
        ]

        # ----------------------------------------- verification logic
        secret_in_history: bool = _SECRET_MARKER in raw_diff_output
        secret_in_working_tree: bool = _check_working_tree_for_secret(repo_path)
        secret_recoverable: bool = secret_in_history and (not secret_in_working_tree)

        # Identify which commits added/removed the secret.
        commit_adding_secret: str = commit1.hexsha
        commit_removing_secret: str = commit2.hexsha

        verification: Dict[str, Any] = {
            "secret_in_history": secret_in_history,
            "secret_in_working_tree": secret_in_working_tree,
            "secret_recoverable": secret_recoverable,
            "secret_marker_found_in_git_log": secret_in_history,
            "persisted_diff_is_redacted": _SECRET_MARKER not in diff_output,
            "commit_adding_secret": commit_adding_secret,
            "commit_removing_secret": commit_removing_secret,
        }

        # PASS iff the secret IS in history AND is NOT in the working tree
        status = "PASS" if (secret_in_history and not secret_in_working_tree) else "FAIL"

        timeline = _build_timeline(repo)

        result: Dict[str, Any] = {
            "repo_path": repo_path,
            "timeline": timeline,
            "diff_output": diff_output,
            "rev_list": rev_list,
            "verification": verification,
            "status": status,
        }

        logger.info(
            "Reproduction complete – status=%s  secret_in_history=%s  "
            "secret_in_working_tree=%s",
            status,
            secret_in_history,
            secret_in_working_tree,
        )
        return result

    except subprocess.CalledProcessError as exc:
        logger.error(
            "Git subprocess failed (cmd=%s, returncode=%d): %s",
            exc.cmd,
            exc.returncode,
            exc.stderr,
        )
        raise RuntimeError(
            f"Git command failed: {' '.join(str(c) for c in exc.cmd)}"
        ) from exc
    except Exception:
        logger.exception("Unexpected error during problem reproduction")
        raise


# ---------------------------------------------------------------------------
# Artifact persistence
# ---------------------------------------------------------------------------


def save_artifacts(
    result: Dict[str, Any],
    artifacts_dir: Path,
) -> Tuple[Path, Path]:
    """Persist reproduction results as JSON and Markdown reports.

    Parameters
    ----------
    result:
        The dict returned by :func:`run_reproduction`.
    artifacts_dir:
        Project root (or custom output directory).  Files are written to:

        * ``<artifacts_dir>/artifacts/o1_reproduction_log.json``
        * ``<artifacts_dir>/docs/o1_reproduction_log.md``

    Returns
    -------
    tuple[Path, Path]
        ``(json_path, md_path)``
    """
    # ---- JSON ----
    json_dir = artifacts_dir / "artifacts"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / "o1_reproduction_log.json"

    # Persist only redacted diff output. The raw subprocess result is used for
    # verification above and is never returned, logged, or written to disk.
    json_path.write_text(
        json.dumps(result, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("JSON artifact saved to %s", json_path)

    # ---- Markdown ----
    md_dir = artifacts_dir / "docs"
    md_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / "o1_reproduction_log.md"

    verification = result.get("verification", {})
    timeline = result.get("timeline", [])

    md_lines: List[str] = [
        "# O1.1 – Problem Reproduction Report",
        "",
        f"**Status:** `{result.get('status', 'UNKNOWN')}`  ",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}  ",
        f"**Repo path:** `{result.get('repo_path', 'N/A')}`",
        "",
        "---",
        "",
        "## Verification Summary",
        "",
        "| Check | Result |",
        "|-------|--------|",
        f"| Secret present in `git log -p` history | "
        f"{'✅ Yes' if verification.get('secret_in_history') else '❌ No'} |",
        f"| Secret present in working tree (HEAD) | "
        f"{'⚠️ Yes' if verification.get('secret_in_working_tree') else '✅ No'} |",
        f"| Secret recoverable from history | "
        f"{'✅ Yes' if verification.get('secret_recoverable') else '❌ No'} |",
        f"| Commit that **added** the secret | "
        f"`{verification.get('commit_adding_secret', 'N/A')[:12]}` |",
        f"| Commit that **removed** the secret | "
        f"`{verification.get('commit_removing_secret', 'N/A')[:12]}` |",
        "",
        "---",
        "",
        "## Commit Timeline",
        "",
        "| # | SHA | Message | Files Changed |",
        "|---|-----|---------|---------------|",
    ]

    for idx, entry in enumerate(timeline, start=1):
        sha_short = entry.get("sha", "")[:12]
        msg = entry.get("message", "")
        files = ", ".join(f"`{f}`" for f in entry.get("files_changed", []))
        md_lines.append(f"| {idx} | `{sha_short}` | {msg} | {files} |")

    md_lines += [
        "",
        "---",
        "",
        "## Reachable Commits (`git rev-list --all`)",
        "",
    ]
    for sha in result.get("rev_list", []):
        md_lines.append(f"- `{sha}`")

    md_lines += [
        "",
        "---",
        "",
        "## Full Diff Output (`git log -p --all`)",
        "",
        "<details>",
        "<summary>Click to expand</summary>",
        "",
        "```diff",
        result.get("diff_output", ""),
        "```",
        "",
        "</details>",
        "",
        "---",
        "",
        "## Conclusion",
        "",
    ]

    if result.get("status") == "PASS":
        md_lines.append(
            "> **The reproduction confirms that deleting a file containing secrets "
            "does NOT remove the secrets from Git history.** Any user with repository "
            "access can recover the credentials by inspecting past commits. This is "
            "the core problem SecretGuard is designed to detect and remediate."
        )
    else:
        md_lines.append(
            "> ⚠️ **Reproduction FAILED** – the expected conditions were not met. "
            "Review the verification table above for details."
        )

    md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("Markdown artifact saved to %s", md_path)

    return json_path, md_path
