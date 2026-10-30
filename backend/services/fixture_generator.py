"""Deterministic Git fixture generation for O2 grading and regression tests."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import shutil
from pathlib import Path
from typing import Any

import git

from backend.services.oracle_loader import OracleEntry, load_oracle

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORY = ROOT / "artifacts" / "synthetic_repo_v1"
DEFAULT_ORACLE_OUTPUT = ROOT / "artifacts" / "ground_truth_oracle.json"
AUTHOR = git.Actor("SecretGuard Fixture Bot", "fixture@example.test")
COMMIT_DATE = "2024-01-01 12:00:00 +0000"


def _commit(repo: git.Repo, message: str, paths: list[str]) -> git.Commit:
    repo.index.add(paths)
    commit = repo.index.commit(
        message,
        head=repo.head.is_valid(),
        author=AUTHOR,
        committer=AUTHOR,
        author_date=COMMIT_DATE,
        commit_date=COMMIT_DATE,
    )
    if not repo.head.is_valid():
        repo.git.update_ref("refs/heads/main", commit.hexsha)
        repo.head.reference = repo.heads.main
        repo.head.reset(index=True, working_tree=False)
    return commit


def _write(repo_path: Path, relative_path: str, content: str) -> None:
    target = repo_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _entry(entries: dict[str, OracleEntry], key: str, fallback: str) -> str:
    return entries[key].value if key in entries else fallback


def _line_number(content: str, needle: str) -> int:
    for number, line in enumerate(content.splitlines(), start=1):
        if needle in line:
            return number
    raise ValueError(f"Fixture value was not written: {needle}")


def _record(
    output: list[dict[str, Any]],
    *,
    entry_id: str,
    commit: git.Commit,
    path: str,
    content: str,
    value: str,
    secret_type: str,
    expected_label: str,
) -> None:
    output.append(
        {
            "entry_id": entry_id,
            "commit_sha": commit.hexsha,
            "file_path": path,
            "line_number": _line_number(content, value),
            "secret_type": secret_type,
            "expected_label": expected_label,
        }
    )


def generate_fixture(
    repository_path: str | Path = DEFAULT_REPOSITORY,
    oracle_output: str | Path = DEFAULT_ORACLE_OUTPUT,
) -> dict[str, Any]:
    """Build the versioned O2 repository and write a safe ground-truth oracle.

    The fixture contains synthetic values only. Existing files outside the
    explicitly generated repository and oracle output are never modified.
    """
    spec = load_oracle()
    entries = {entry.id: entry for entry in spec.entries}
    repo_path = Path(repository_path).resolve()
    oracle_path = Path(oracle_output).resolve()
    if repo_path.exists():
        def _remove_read_only(function: Any, path: str, _exc: object) -> None:
            os.chmod(path, stat.S_IWRITE)
            function(path)

        shutil.rmtree(repo_path, onerror=_remove_read_only)
    repo_path.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.init(repo_path, initial_branch="main")
    repo.git.symbolic_ref("HEAD", "refs/heads/main")
    with repo.config_writer() as config:
        config.set_value("user", "name", AUTHOR.name)
        config.set_value("user", "email", AUTHOR.email)
        config.set_value("core", "hooksPath", (repo_path / ".disabled-hooks").as_posix())

    records: list[dict[str, Any]] = []
    aws = _entry(entries, "oracle-aws-head", "AKIAIOSFODNN7EXAMPLE")
    base64_value = _entry(entries, "oracle-base64", "c2dfYmFzZTY0X3N5bnRoZXRpY19rZXk=")
    base64_plaintext = base64.b64decode(base64_value).decode("utf-8")
    head_content = (
        f"AWS_ACCESS_KEY_ID={aws}\n"
        "APP_NAME=synthetic-service\n"
        f"ENCODED_SECRET={base64_value}\n"
        f"UUID_DECOY=550e8400-e29b-41d4-a716-446655440000\n"
        f"SHA256_DECOY={hashlib.sha256(b'o2-decoy').hexdigest()}\n"
        "MOCK_KEY=AKIAEXAMPLENOTREAL00\n"
    )
    _write(repo_path, "config/application.env", head_content)
    _write(repo_path, "static/app.3f2a9c1d.js", "const bundle='webpack-content-hash-3f2a9c1d';\n")
    first = _commit(repo, "Add active and encoded synthetic configuration", ["config/application.env", "static/app.3f2a9c1d.js"])
    _record(records, entry_id="oracle-aws-head", commit=first, path="config/application.env", content=head_content, value=aws, secret_type="aws_access_key", expected_label="TP")
    _record(records, entry_id="oracle-base64", commit=first, path="config/application.env", content=head_content, value=base64_value, secret_type="encoded_secret", expected_label="TP")
    records.extend(
        [
            {"entry_id": "uuid-decoy", "commit_sha": first.hexsha, "file_path": "config/application.env", "line_number": 4, "secret_type": "uuid", "expected_label": "FP_DECOY"},
            {"entry_id": "sha256-decoy", "commit_sha": first.hexsha, "file_path": "config/application.env", "line_number": 5, "secret_type": "sha256", "expected_label": "FP_DECOY"},
            {"entry_id": "mock-key-decoy", "commit_sha": first.hexsha, "file_path": "config/application.env", "line_number": 6, "secret_type": "mock_key", "expected_label": "FP_DECOY"},
            {"entry_id": "webpack-decoy", "commit_sha": first.hexsha, "file_path": "static/app.3f2a9c1d.js", "line_number": 1, "secret_type": "webpack_hash", "expected_label": "FP_DECOY"},
        ]
    )

    deleted_value = _entry(entries, "oracle-db-deleted", "mysql://user:example-password@db.invalid:3306/app")
    deleted_content = f"DATABASE_URL={deleted_value}\n"
    _write(repo_path, "config/legacy.env", deleted_content)
    deleted_commit = _commit(repo, "Add legacy database configuration", ["config/legacy.env"])
    _record(records, entry_id="oracle-db-deleted", commit=deleted_commit, path="config/legacy.env", content=deleted_content, value=deleted_value, secret_type="mysql_uri", expected_label="TP")
    (repo_path / "config/legacy.env").unlink()
    repo.index.remove(["config/legacy.env"], working_tree=True)
    _commit(repo, "Remove legacy database configuration", [])

    branch_name = "feature/legacy-auth"
    repo.git.checkout("-b", branch_name)
    branch_value = _entry(entries, "oracle-branch-token", "sg_orphan_branch_synthetic_8f71b2")
    branch_content = f"LEGACY_AUTH_TOKEN={branch_value}\n"
    _write(repo_path, "config/legacy_auth.env", branch_content)
    branch_commit = _commit(repo, "Add legacy auth branch fixture", ["config/legacy_auth.env"])
    _record(records, entry_id="oracle-branch-token", commit=branch_commit, path="config/legacy_auth.env", content=branch_content, value=branch_value, secret_type="generic_token", expected_label="TP")
    tag_value = _entry(entries, "oracle-tagged-token", "sg_git_tag_synthetic_4ac91e")
    tag_content = f"TAGGED_TOKEN={tag_value}\n"
    _write(repo_path, "config/tagged.env", tag_content)
    tag_commit = _commit(repo, "Add alpha tag fixture", ["config/tagged.env"])
    repo.create_tag("v0.1-alpha", ref=tag_commit, message="Synthetic annotated alpha fixture")
    _record(records, entry_id="oracle-tagged-token", commit=tag_commit, path="config/tagged.env", content=tag_content, value=tag_value, secret_type="generic_token", expected_label="TP")
    repo.git.checkout("main")

    rewritten_value = _entry(entries, "oracle-rewritten", "sg_rewritten_history_synthetic_2d0c77")
    rewritten_content = f"REWRITTEN_TOKEN={rewritten_value}\n"
    _write(repo_path, "config/rewritten.env", rewritten_content)
    rewritten_commit = _commit(repo, "Temporary rewritten-history fixture", ["config/rewritten.env"])
    _record(records, entry_id="oracle-rewritten", commit=rewritten_commit, path="config/rewritten.env", content=rewritten_content, value=rewritten_value, secret_type="generic_token", expected_label="TP")
    parent = rewritten_commit.parents[0]
    repo.head.reset(parent, index=True, working_tree=True)
    (repo_path / "config/rewritten.env").unlink(missing_ok=True)
    repo.git.reflog("expire", "--expire=never", "--all")
    repo.close()

    oracle_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": spec.version,
        "repository": str(repo_path),
        "source_oracle": "fixtures/oracle_spec.yaml",
        "base64_plaintext_sha256": hashlib.sha256(base64_plaintext.encode("utf-8")).hexdigest(),
        "entries": records,
        "expected_labels": {"TP": sum(item["expected_label"] == "TP" for item in records), "FP_DECOY": sum(item["expected_label"] == "FP_DECOY" for item in records)},
    }
    oracle_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


build_fixture = generate_fixture


if __name__ == "__main__":
    print(json.dumps(generate_fixture(), indent=2))
