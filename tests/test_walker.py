from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import git

import src.shd.walker as walker
from src.shd.walker import walk_repository
from tests.fixtures.make_fixture_repo import make_fixture_repo


def test_deleted_file_last_content_is_recorded(tmp_path: Path) -> None:
    repo_path = make_fixture_repo(str(tmp_path))
    config_records = [record for record in walk_repository(repo_path) if record.file_path == "config.py"]

    assert any(record.blob_content.strip() == 'SECRET_KEY = "xyz789"' for record in config_records)
    assert any(record.blob_content.strip() == 'SECRET_KEY = "abc123"' for record in config_records)
    assert any(not record.is_head for record in config_records)


def test_records_have_no_duplicate_commit_and_path_pairs(tmp_path: Path) -> None:
    repo_path = make_fixture_repo(str(tmp_path))
    repo = git.Repo(repo_path)
    repo.create_head("feature", repo.commit("HEAD~2"))
    repo.close()

    records = list(walk_repository(repo_path))
    pairs = [(record.commit_hash, record.file_path) for record in records]

    assert len(pairs) == len(set(pairs))


def test_empty_repository_returns_no_records(tmp_path: Path) -> None:
    repo_path = tmp_path / "empty"
    git.Repo.init(repo_path)

    assert list(walk_repository(str(repo_path))) == []


def test_single_commit_repository_does_not_require_a_parent(tmp_path: Path) -> None:
    repo_path = tmp_path / "single"
    repo = git.Repo.init(repo_path)
    (repo_path / "README.md").write_text("single commit\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    repo.close()

    records = list(walk_repository(str(repo_path)))

    assert len(records) == 1
    assert records[0].file_path == "README.md"


def test_binary_blob_decodes_with_replacement(tmp_path: Path) -> None:
    repo_path = tmp_path / "binary"
    repo = git.Repo.init(repo_path)
    (repo_path / "binary.dat").write_bytes(b"prefix\xffsuffix")
    repo.index.add(["binary.dat"])
    repo.index.commit("Add binary blob")
    repo.close()

    records = list(walk_repository(str(repo_path)))

    assert records[0].blob_content == "prefix" + chr(0xFFFD) + "suffix"


def test_head_flag_matches_current_tree_only(tmp_path: Path) -> None:
    repo_path = make_fixture_repo(str(tmp_path))
    records = list(walk_repository(repo_path))

    readme_records = [record for record in records if record.file_path == "README.md"]
    config_records = [record for record in records if record.file_path == "config.py"]

    assert readme_records
    assert all(record.is_head for record in readme_records)
    assert config_records
    assert all(not record.is_head for record in config_records)


def test_decode_blob_failure_returns_empty_string() -> None:
    class BrokenStream:
        def read(self) -> bytes:
            raise OSError("read failed")

    assert walker._decode_blob(SimpleNamespace(data_stream=BrokenStream())) == ""


def test_missing_blob_path_returns_none(tmp_path: Path) -> None:
    repo_path = make_fixture_repo(str(tmp_path))
    repo = git.Repo(repo_path)

    assert walker._blob_at_path(repo.head.commit.tree, "missing.txt") is None
    repo.close()


def test_remote_repository_clone_is_cleaned_up(monkeypatch) -> None:
    fake_repo = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(walker.git.Repo, "clone_from", lambda *_args: fake_repo)
    monkeypatch.setattr(walker.tempfile, "mkdtemp", lambda **_kwargs: "clone-dir")
    removed: list[str] = []
    monkeypatch.setattr(walker.shutil, "rmtree", lambda path, **_kwargs: removed.append(path))
    monkeypatch.setattr(walker, "_walk_repo", lambda _repo: iter(()))

    assert list(walker.walk_repository("https://example.test/repo.git")) == []
    assert removed == ["clone-dir"]
