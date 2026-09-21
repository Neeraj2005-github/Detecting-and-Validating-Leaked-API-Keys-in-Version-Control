# Dataset Manifest

The manifest format is a JSON list, or an object with a `repos` list. Each
repository entry contains `repo_id`, `split`, `source`, and `planted_secrets`.
Each planted secret records its planting commit, path, type, and removal commit.

Synthetic repositories are created by
`tests/fixtures/make_synthetic_secret_repo.py`; the helper returns real commit
hashes for both planting and removal. `src/shd/dataset.py` validates entries and
rejects repository IDs shared by the `reference` and `eval` splits.

SecretBench provenance and licensing details must be added when the team
selects and vendors its agreed subset. The split should then be frozen in
`docs/eval/dataset_manifest.json` before evaluation metrics are reported.