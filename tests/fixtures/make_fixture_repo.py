from __future__ import annotations

import tempfile
from pathlib import Path

import git


def make_fixture_repo(base_dir: str | None = None) -> str:
    repo_dir = tempfile.mkdtemp(prefix="shd_fixture_", dir=base_dir)
    repo = git.Repo.init(repo_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test Author")
        cw.set_value("user", "email", "test@example.com")
    root = Path(repo_dir)

    root.joinpath("README.md").write_text("# Fixture Repo\n", encoding="utf-8")
    root.joinpath("config.py").write_text('SECRET_KEY = "abc123"\n', encoding="utf-8")
    repo.index.add(["README.md", "config.py"])
    repo.index.commit("Initial commit: add config.py")

    root.joinpath("config.py").write_text('SECRET_KEY = "xyz789"\n', encoding="utf-8")
    repo.index.add(["config.py"])
    repo.index.commit("Update config.py with new secret")

    root.joinpath("config.py").unlink()
    repo.index.remove(["config.py"])
    repo.index.commit("Remove config.py")

    repo.close()
    return repo_dir


if __name__ == "__main__":
    path = make_fixture_repo()
    print(f"Fixture repo created at: {path}")
