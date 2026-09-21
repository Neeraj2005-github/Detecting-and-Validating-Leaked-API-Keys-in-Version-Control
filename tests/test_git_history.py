import os
from pathlib import Path

import git
import pytest

from backend.extractor.git_history import CommitDiff, extract_history


def test_extract_history_empty_repo(tmp_path):
    repo_path = tmp_path / "empty_repo"
    git.Repo.init(repo_path)

    results = list(extract_history(str(repo_path)))

    assert results == []


def test_extract_history_single_commit(tmp_path):
    repo_path = tmp_path / "single_repo"
    repo = git.Repo.init(repo_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    file_path = repo_path / "notes.txt"
    file_path.write_text("hello secret\n", encoding="utf-8")
    repo.index.add([str(file_path)])
    repo.index.commit("initial")

    results = list(extract_history(str(repo_path)))

    assert len(results) == 1
    assert isinstance(results[0], CommitDiff)
    assert results[0].file_path.endswith("notes.txt")


def test_extract_history_skips_binary_files(tmp_path):
    repo_path = tmp_path / "binary_repo"
    repo = git.Repo.init(repo_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    file_path = repo_path / "data.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03\x04\x05")
    repo.index.add([str(file_path)])
    repo.index.commit("add-binary")

    results = list(extract_history(str(repo_path)))

    assert results == []


def test_extract_history_seeded_repo():
    repo_path = Path("testdata/seeded_repo")
    if not repo_path.exists():
        pytest.skip("seeded repo has not been generated yet")

    results = list(extract_history(str(repo_path)))

    assert len(results) > 0
