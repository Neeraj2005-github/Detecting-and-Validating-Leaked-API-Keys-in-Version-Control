# Planted sample scan evidence

Scanned `testdata/seeded_repo` with `backend.detection.gitleaks_runner.run_gitleaks` on the local Windows host. Finding values are not persisted or printed.

- Scan time: **0.181583 s**
- Raw Gitleaks findings: **17**
- Unmatched findings outside the labeled fixture keys: **0**
- Positive fixtures: **15/15 found**
- Negative fixtures: **15/15 correctly clean**
- Labeled-fixture confusion counts: TP=15, FP=0, TN=15, FN=0
- Positive-class precision: **1.000**; recall: **1.000**
- Negative-class precision: **1.000**; recall: **1.000**

Metrics use the 30 labeled records in `testdata/ground_truth.yaml` keyed by commit and file. Positive-class metrics treat the 15 `true_secret` records as positive; negative-class metrics treat the 15 `false_positive` records as negative. Unmatched raw findings are reported separately and are not silently assigned labels.
