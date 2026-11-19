from __future__ import annotations

import subprocess

import git
import pytest

from backend.services.coverage import assert_scan_complete, build_coverage


def _git(repo: git.Repo, *args: str) -> str:
    return repo.git.execute(["git", *args])


def test_branch_tag_merge_deleted_branch_and_merge_commit_coverage(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "CP1 Test")
        config.set_value("user", "email", "cp1@example.test")

    base = tmp_path / "base.txt"
    base.write_text("base\n", encoding="utf-8")
    repo.index.add(["base.txt"])
    root = repo.index.commit("root")
    main_branch = repo.active_branch.name

    repo.git.checkout("-b", "deleted-feature")
    feature = tmp_path / "feature.txt"
    feature.write_text("feature\n", encoding="utf-8")
    repo.index.add(["feature.txt"])
    feature_commit = repo.index.commit("feature")
    repo.create_tag("v1")

    repo.git.checkout(main_branch)
    repo.git.merge("deleted-feature", "--no-ff", "-m", "merge feature")
    merge_commit = repo.head.commit.hexsha

    repo.git.branch("-D", "deleted-feature")
    manifest = build_coverage(tmp_path)

    assert "v1" in manifest["refs"]["tags"]
    assert merge_commit in manifest["commits_reachable_shas"]
    assert feature_commit.hexsha in manifest["commits_reachable_shas"]
    assert manifest["commits_reachable"] >= 3
    assert manifest["shallow"] is False
    assert manifest["completeness"] in {"complete", "incomplete"}


def test_shallow_repository_is_refused(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    repo = git.Repo.init(source)
    with repo.config_writer() as config:
        config.set_value("user", "name", "CP1 Test")
        config.set_value("user", "email", "cp1@example.test")
    first = source / "first.txt"
    first.write_text("first\n", encoding="utf-8")
    repo.index.add(["first.txt"])
    repo.index.commit("first")
    second = source / "second.txt"
    second.write_text("second\n", encoding="utf-8")
    repo.index.add(["second.txt"])
    repo.index.commit("second")

    shallow = tmp_path / "shallow"
    repo.git.execute(
        ["git", "clone", "--depth", "1", "--no-local", source.as_uri(), str(shallow)]
    )
    manifest = build_coverage(shallow)
    assert manifest["shallow"] is True
    with pytest.raises(ValueError, match="SHALLOW_REPOSITORY_REFUSED"):
        assert_scan_complete(shallow)


def test_coverage_mismatch_fires_when_scanned_count_is_lower(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "CP1 Test")
        config.set_value("user", "email", "cp1@example.test")
    path = tmp_path / "main.txt"
    path.write_text("main\n", encoding="utf-8")
    repo.index.add(["main.txt"])
    repo.index.commit("main")

    expected = build_coverage(tmp_path)
    with pytest.raises(RuntimeError, match="SCAN_COVERAGE_MISMATCH"):
        assert_scan_complete(
            tmp_path,
            commits_scanned=expected["commits_reachable"] - 1,
        )


def test_force_push_dropped_commit_is_unreachable(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "CP1 Test")
        config.set_value("user", "email", "cp1@example.test")
    path = tmp_path / "history.txt"
    path.write_text("A\n", encoding="utf-8")
    repo.index.add(["history.txt"])
    first = repo.index.commit("A")
    path.write_text("B\n", encoding="utf-8")
    repo.index.add(["history.txt"])
    dropped = repo.index.commit("B")
    repo.head.reset(first, index=True, working_tree=True)

    manifest = build_coverage(tmp_path)
    assert dropped.hexsha not in manifest["commits_reachable_shas"]
    assert manifest["unreachable_object_count"] >= 1
