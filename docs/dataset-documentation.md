# Dataset Documentation

## Synthetic oracle

[`fixtures/oracle_spec.yaml`](../fixtures/oracle_spec.yaml) defines six
synthetic secrets across lifecycle types and two high-entropy decoys. It is a
specification, not a production credential source. The fixture generator writes
the versioned repository and benchmark oracle to
`artifacts/synthetic_repo_v1/` and `artifacts/ground_truth_oracle.json`.

## Evaluation inputs

- `data/o2_evaluation.json` — earlier labeled examples and train/validation/test
  split.
- `data/real_repo_20_labels.csv` — repository-group labels for frozen-split
  XGBoost evaluation.
- `data/frozen_test_split.json` — frozen split metadata.
- `testdata/seed_repo.py` — independent seeded repository generator.
- `tests/fixtures/` — test-only repository builders.

The dataset manifest notes in
[`docs/eval/dataset_manifest.md`](eval/dataset_manifest.md) describe the
planned repository manifest format and provenance requirements.

## Reproducibility

```powershell
python -c "from backend.services.fixture_generator import generate_fixture; generate_fixture()"
python scripts/reproduce_o2.py
```

Generated artifacts should be reviewed for masking and provenance before
external publication. The corpus is synthetic/small and does not establish
production prevalence or provider validity.
