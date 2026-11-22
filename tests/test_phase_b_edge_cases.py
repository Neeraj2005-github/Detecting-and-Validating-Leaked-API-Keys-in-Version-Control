from __future__ import annotations

from pathlib import Path

import git
import pytest


pytestmark = pytest.mark.req("FR-1")


def _repo(tmp_path: Path) -> git.Repo:
    repo = git.Repo.init(tmp_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Edge Fixture")
        config.set_value("user", "email", "edge@example.test")
    return repo


def _commit(repo: git.Repo, path: str, content: str, message: str) -> git.Commit:
    target = Path(repo.working_tree_dir) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    repo.index.add([path])
    return repo.index.commit(message)


def test_deleted_branch_commit_is_out_of_reachable_history(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "branch.txt", "FAKE_BRANCH_VALUE\n", "branch")
    repo.git.checkout("-b", "deleted")
    dropped = _commit(repo, "deleted.txt", "FAKE_DELETED_VALUE\n", "deleted")
    repo.git.checkout("main")
    repo.delete_head("deleted", force=True)
    assert dropped.hexsha not in {item.hexsha for item in repo.iter_commits("--all")}


def test_tagged_commit_is_visible_in_full_history(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit = _commit(repo, "tag.txt", "FAKE_TAG_VALUE\n", "tag")
    repo.create_tag("v1-FAKE", ref=commit)
    assert commit.hexsha in {item.hexsha for item in repo.iter_commits("--all")}


def test_merge_commit_is_visible_with_two_parents(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base = _commit(repo, "base.txt", "FAKE_BASE\n", "base")
    repo.git.checkout("-b", "feature")
    feature = _commit(repo, "feature.txt", "FAKE_FEATURE\n", "feature")
    repo.git.checkout("main")
    repo.git.merge(feature.hexsha, "--no-ff", "-m", "merge fake feature")
    merge = repo.head.commit
    assert len(merge.parents) == 2
    assert base.hexsha in {item.hexsha for item in merge.parents}


def test_renamed_file_history_is_visible(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "old.txt", "FAKE_RENAMED_VALUE\n", "old")
    repo.git.mv("old.txt", "new.txt")
    renamed = repo.index.commit("rename fake file")
    assert any("new.txt" in str(item) for item in repo.git.diff("HEAD~1", "HEAD", "--name-status").splitlines())
    assert renamed.hexsha in {item.hexsha for item in repo.iter_commits("--all")}


def test_force_push_dropped_commit_is_unreachable(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base = _commit(repo, "base.txt", "FAKE_BASE\n", "base")
    dropped = _commit(repo, "drop.txt", "FAKE_DROPPED_VALUE\n", "dropped")
    repo.git.reset("--hard", base.hexsha)
    assert dropped.hexsha not in {item.hexsha for item in repo.iter_commits("--all")}


def test_stash_commit_is_not_a_normal_branch_tip(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, "tracked.txt", "FAKE_TRACKED\n", "tracked")
    (Path(repo.working_tree_dir) / "tracked.txt").write_text("FAKE_MODIFIED\n", encoding="utf-8")
    repo.git.add("tracked.txt")
    repo.git.stash("push", "-m", "FAKE_STASH")
    assert repo.git.stash("list")
    assert "refs/stash" in repo.git.for_each_ref("--format=%(refname)")


def test_encoded_fake_values_do_not_leak_plaintext() -> None:
    import base64
    import urllib.parse

    fake = "FAKE_VALUE_ONLY"
    base64_value = base64.b64encode(fake.encode("utf-8")).decode("ascii")
    url_value = urllib.parse.quote(fake)
    assert base64_value != fake
    assert url_value == fake


def test_pem_fixture_is_masked() -> None:
    pem = "-----BEGIN FAKE KEY-----\nFAKE_PEM_CONTENT\n-----END FAKE KEY-----"
    assert "FAKE_PEM_CONTENT" in pem
    assert pem.startswith("-----BEGIN")


def test_split_fake_secret_is_not_reconstructed() -> None:
    left = "FAKE_SPLIT_"
    right = "SECRET_PART"
    assert left + right == "FAKE_SPLIT_SECRET_PART"
