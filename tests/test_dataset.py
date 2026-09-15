import json

import pytest
import git

from src.shd.dataset import DatasetEntry, load_manifest, validate_split_disjoint, write_manifest
from tests.fixtures.make_synthetic_secret_repo import make_synthetic_secret_repo


def write_payload(tmp_path, payload: object):
    path = tmp_path / "dataset_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_manifest_loads_and_validates(tmp_path) -> None:
    path = write_payload(tmp_path, {"repos": [
        {
            "repo_id": "synthetic-001",
            "split": "reference",
            "source": "synthetic",
            "planted_secrets": [{
                "commit_hash": "plant-1",
                "file_path": "config.py",
                "secret_type": "aws_access_key",
                "removed_in_commit": "remove-1",
            }],
        },
    ]})

    entries = load_manifest(path)

    assert entries[0].repo_id == "synthetic-001"
    assert entries[0].planted_secrets[0].removed_in_commit == "remove-1"
    validate_split_disjoint(entries)


def test_reference_and_eval_repo_ids_cannot_overlap(tmp_path) -> None:
    path = write_payload(tmp_path, [
        {"repo_id": "same", "split": "reference", "source": "synthetic", "planted_secrets": []},
        {"repo_id": "same", "split": "eval", "source": "synthetic", "planted_secrets": []},
    ])

    with pytest.raises(ValueError, match="both dataset splits"):
        validate_split_disjoint(load_manifest(path))


def test_invalid_split_is_rejected(tmp_path) -> None:
    path = write_payload(tmp_path, [
        {"repo_id": "bad", "split": "training", "source": "synthetic", "planted_secrets": []},
    ])

    with pytest.raises(ValueError):
        load_manifest(path)


def test_synthetic_manifest_removal_commit_exists(tmp_path) -> None:
    repo_path, payload = make_synthetic_secret_repo(str(tmp_path))
    entry = load_manifest(write_payload(tmp_path, [payload]))[0]
    repo = git.Repo(repo_path)

    for planted_secret in entry.planted_secrets:
        assert repo.commit(planted_secret.commit_hash)
        assert repo.commit(planted_secret.removed_in_commit)

    repo.close()


def test_manifest_writer_round_trips_entries(tmp_path) -> None:
    path = tmp_path / "written_manifest.json"
    entries = [DatasetEntry.model_validate({
        "repo_id": "synthetic-001",
        "split": "reference",
        "source": "synthetic",
        "planted_secrets": [{
            "commit_hash": "plant-1",
            "file_path": "config.py",
            "secret_type": "aws_access_key",
            "removed_in_commit": "remove-1",
        }],
    })]

    write_manifest(entries, path)

    assert load_manifest(path) == entries