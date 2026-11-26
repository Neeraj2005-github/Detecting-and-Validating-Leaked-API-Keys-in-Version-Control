# Local sample scan evidence

The requested `DEVOPS-LAB-EXAM` repository was not present in the workspace.
Its scan time, finding count, precision, and recall are **NOT MEASURED**.

The local planted sample `testdata/seeded_repo` produced 17 findings in 0.207
seconds using `backend.detection.gitleaks_runner.run_gitleaks` on the local
Windows host. The measurement records only the count and elapsed time; it does
not persist or print finding values.

Per-category precision, recall, F1, false-positive rates, medians, min/max, and
bootstrap 95% confidence intervals for the synthetic positive and negative
fixtures are in [`../comparison.md`](../comparison.md) and
[`../../artifacts/comparison.json`](../../artifacts/comparison.json). These
results are controlled-fixture evidence, not estimates of production
performance on `DEVOPS-LAB-EXAM`.
