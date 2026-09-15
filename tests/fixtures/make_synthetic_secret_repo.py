from __future__ import annotations

import tempfile
from pathlib import Path

import git


def make_synthetic_secret_repo(
    base_dir: str | None = None,
    *,
    repo_id: str = "synthetic-001",
    split: str = "reference",
) -> tuple[str, dict[str, object]]:
    """Create a plant/remove history and return its manifest entry."""
    repo_dir = tempfile.mkdtemp(prefix=f"{repo_id}_", dir=base_dir)
    repo = git.Repo.init(repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Synthetic Fixture")
        config.set_value("user", "email", "fixture@example.test")

    config_path = Path(repo_dir) / "config.py"
    config_path.write_text(
        "AWS_ACCESS_KEY = '" + "AKIA" + "IOSFODNN7EXAMPLE'\n",
        encoding="utf-8",
    )
    repo.index.add(["config.py"])
    planted_commit = repo.index.commit("Plant synthetic AWS key").hexsha

    config_path.unlink()
    repo.index.remove(["config.py"])
    removed_commit = repo.index.commit("Remove synthetic AWS key").hexsha
    repo.close()

    return repo_dir, {
        "repo_id": repo_id,
        "split": split,
        "source": "synthetic",
        "planted_secrets": [{
            "commit_hash": planted_commit,
            "file_path": "config.py",
            "secret_type": "aws_access_key",
            "removed_in_commit": removed_commit,
        }],
    }