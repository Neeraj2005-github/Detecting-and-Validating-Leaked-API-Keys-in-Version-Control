# M3 to M4 Workflow

M3 produces `DedupedFinding` objects and a frozen dataset manifest. M4 consumes
those artifacts to calculate precision, recall, F1, and false-positive rate.

M4 does not re-derive labels, normalization, or secret IDs. M3 owns the
reference/eval split and the `label_ground_truth` value on each deduplicated
finding.

The split is a one-way decision: after `eval/dataset_manifest.json` is frozen,
labeling defects are documented rather than silently changing the split and
invalidating baseline comparisons.