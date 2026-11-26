# Comparative scanner benchmark

Generated from identical synthetic Git fast-import repositories. All credential-shaped values are synthetic test data; no real secret values are included in this report.

- Generated: `2026-11-26T09:56:30Z`
- Native Gitleaks: `8.18.4`
- Wrapper: Gitleaks `8.18.4` via `run_gitleaks`
- detect-secrets: `1.5.0`
- Repetitions: five per scanner and repository size; bootstrap 95% CIs use 2,000 resamples of the median.
- Positive categories are evaluated one-vs-known-negative examples; the clean-negative and documentation-example rows are negative-only, so precision, recall, and F1 are not applicable for those rows.

## 100 commits

Verified commit objects: 100; reachable commits: 98.

| Scanner | Category | Precision median [95% CI] | Recall median [95% CI] | F1 median [95% CI] | FP rate median [95% CI] |
|---|---|---:|---:|---:|---:|
| native-gitleaks | added-then-deleted | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | deleted-branch | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | tag | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | merge | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | rename | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | force-push-dropped | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | base64 | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | pem | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | split-secret | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | clean-negative | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | doc-example-false-positive | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | added-then-deleted | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | deleted-branch | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | tag | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | merge | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | rename | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | force-push-dropped | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | base64 | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | pem | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | split-secret | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | clean-negative | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | doc-example-false-positive | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | added-then-deleted | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | deleted-branch | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | tag | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | merge | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | rename | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | force-push-dropped | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | base64 | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | pem | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | split-secret | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | clean-negative | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | doc-example-false-positive | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 1.000 [1.000, 1.000] (min 1.000, max 1.000) |

## 1000 commits

Verified commit objects: 1000; reachable commits: 998.

| Scanner | Category | Precision median [95% CI] | Recall median [95% CI] | F1 median [95% CI] | FP rate median [95% CI] |
|---|---|---:|---:|---:|---:|
| native-gitleaks | added-then-deleted | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | deleted-branch | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | tag | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | merge | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | rename | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | force-push-dropped | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | base64 | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | pem | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | split-secret | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | clean-negative | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | doc-example-false-positive | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | added-then-deleted | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | deleted-branch | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | tag | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | merge | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | rename | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | force-push-dropped | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | base64 | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | pem | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | split-secret | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | clean-negative | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | doc-example-false-positive | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | added-then-deleted | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | deleted-branch | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | tag | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | merge | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | rename | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | force-push-dropped | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | base64 | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | pem | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | split-secret | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | clean-negative | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | doc-example-false-positive | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 1.000 [1.000, 1.000] (min 1.000, max 1.000) |

## Method and limitations

The fixtures include added-then-deleted content, an unreachable deleted branch, a tag, a merge, rename, force-push-dropped content, base64 and PEM-shaped examples, a split credential, clean text, and a documentation example. `detect-secrets` is invoked as its pinned CLI on each current checkout; it does not natively walk unreachable Git history, which is intentionally reflected in its results.

Precision and recall are based on the single labeled credential path for each positive scenario and the two labeled negative paths plus any unrecognized reported paths. These synthetic outcomes are not estimates of production performance.
