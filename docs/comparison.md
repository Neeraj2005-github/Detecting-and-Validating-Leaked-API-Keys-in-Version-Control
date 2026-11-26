# Comparative scanner benchmark

Generated from identical synthetic Git fast-import repositories. All credential-shaped values are synthetic test data; no real secret values are included in this report.

- Generated: `2026-11-26T10:19:26Z`
- Native Gitleaks: `8.18.4`
- Wrapper: Gitleaks `8.18.4` via `run_gitleaks`
- detect-secrets: `1.5.0`
- Repetitions: five per scanner and repository size; bootstrap 95% CIs use 2,000 resamples of the median.
- Positive categories are evaluated one-vs-known-negative examples; the clean-negative and documentation-example rows are negative-only, so precision, recall, and F1 are not applicable for those rows.

## 100 commits

Verified commit objects: 100; reachable commits: 98.

| Scanner | Category | Applicability | Precision median [95% CI] | Recall median [95% CI] | F1 median [95% CI] | FP rate median [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| native-gitleaks | added-then-deleted | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | unreachable object (not reachable from any ref) — deleted branch | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| native-gitleaks | tag | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | merge | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | rename | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | unreachable object (not reachable from any ref) — force-push dropped | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| native-gitleaks | base64 | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | pem | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | split-secret | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | clean-negative | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | doc-example-false-positive | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | added-then-deleted | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | unreachable object (not reachable from any ref) — deleted branch | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| wrapper | tag | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | merge | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | rename | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | unreachable object (not reachable from any ref) — force-push dropped | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| wrapper | base64 | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | pem | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | split-secret | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | clean-negative | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | doc-example-false-positive | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | added-then-deleted | NOT APPLICABLE: detect-secrets scans checked-out files, not Git history; this case is not represented in the checkout. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| detect-secrets | unreachable object (not reachable from any ref) — deleted branch | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| detect-secrets | tag | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | merge | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | rename | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | unreachable object (not reachable from any ref) — force-push dropped | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| detect-secrets | base64 | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | pem | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | split-secret | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | clean-negative | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | doc-example-false-positive | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 1.000 [1.000, 1.000] (min 1.000, max 1.000) |

## 1000 commits

Verified commit objects: 1000; reachable commits: 998.

| Scanner | Category | Applicability | Precision median [95% CI] | Recall median [95% CI] | F1 median [95% CI] | FP rate median [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| native-gitleaks | added-then-deleted | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | unreachable object (not reachable from any ref) — deleted branch | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| native-gitleaks | tag | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | merge | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | rename | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | unreachable object (not reachable from any ref) — force-push dropped | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| native-gitleaks | base64 | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | pem | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | split-secret | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | clean-negative | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| native-gitleaks | doc-example-false-positive | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | added-then-deleted | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | unreachable object (not reachable from any ref) — deleted branch | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| wrapper | tag | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | merge | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | rename | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | unreachable object (not reachable from any ref) — force-push dropped | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| wrapper | base64 | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | pem | MEASURED | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | split-secret | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | clean-negative | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| wrapper | doc-example-false-positive | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | added-then-deleted | NOT APPLICABLE: detect-secrets scans checked-out files, not Git history; this case is not represented in the checkout. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| detect-secrets | unreachable object (not reachable from any ref) — deleted branch | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| detect-secrets | tag | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | merge | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | rename | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | unreachable object (not reachable from any ref) — force-push dropped | NOT APPLICABLE: The commit object is unreachable from every ref and is outside this scanner's input. | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| detect-secrets | base64 | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | pem | MEASURED | 0.500 [0.500, 0.500] (min 0.500, max 0.500) | 1.000 [1.000, 1.000] (min 1.000, max 1.000) | 0.667 [0.667, 0.667] (min 0.667, max 0.667) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | split-secret | MEASURED | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.000 [0.000, 0.000] (min 0.000, max 0.000) | 0.500 [0.500, 0.500] (min 0.500, max 0.500) |
| detect-secrets | clean-negative | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 0.000 [0.000, 0.000] (min 0.000, max 0.000) |
| detect-secrets | doc-example-false-positive | MEASURED | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE | 1.000 [1.000, 1.000] (min 1.000, max 1.000) |

## Lifecycle comparison (measured fixture runs)

| Measure | Native Gitleaks | Gitleaks wrapper | SecretGuard pipeline |
|---|---|---|---|
| Deleted-but-recoverable finding flagged | flagged | flagged | Reported through the same scanner result |
| Coverage manifest | Not provided | Not provided by `run_gitleaks` | complete; 98 scanned / 98 reachable commits; 6 unreachable objects |
| Repeated synthetic finding across 100 commits | 1 raw findings | 1 raw findings | 100 history matches → 1 deduplicated finding(s) |
| Invalid configuration | yes (exit 1; invalid config rejected: true) | yes (rejects non-owned config) | yes (uses the same owned-config wrapper) |

The lifecycle rows are direct fixture observations. Native Gitleaks and `run_gitleaks` use the same scanner, so identical raw detections are expected; deduplication and coverage-manifest reporting are separate SecretGuard pipeline capabilities. The coverage manifest records reachable refs and reports unreachable objects separately; `complete` does not mean unreachable objects were scanned.

## Method and limitations

The fixtures include added-then-deleted content, two unreachable-object scenarios, a tag, a merge, rename, base64 and PEM-shaped examples, a split credential, clean text, and a documentation example. The two unreachable-object categories mean exactly that their commits are not reachable from any ref; ref-walking scanners cannot inspect those objects, so their precision/recall/F1 are not applicable rather than zero. `detect-secrets scan --all-files` scans the checked-out working tree, not Git history; history-only cases absent from the checkout are not applicable.

Precision and recall are based on the single labeled credential path for each positive scenario and the two labeled negative paths plus any unrecognized reported paths. These synthetic outcomes are not estimates of production performance.
