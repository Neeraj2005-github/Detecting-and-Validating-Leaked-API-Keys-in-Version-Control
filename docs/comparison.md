# Native Gitleaks and wrapper comparison

These are real local runs against synthetic, controlled fixtures. No credential
values are stored in this report or in the associated JSON artifact.

## Same-fixture detection comparison

The native binary and the CP1 API scanned the same checked-in synthetic
repository (`artifacts/synthetic_repo_v1`): six reachable commits, ten labeled
oracle examples, and three skipped files. The wrapper was run with
`use_ai_filter=false` to isolate the detector and wrapper lifecycle/coverage
behavior. Artifact writes and SHAP presentation output were disabled by the
measurement harness; Gitleaks, parsing, coverage, lifecycle analysis, and
deduplication ran through their real code paths.

| Measure | Native Gitleaks | Wrapper |
|---|---:|---:|
| Findings reported | 6 | 6 |
| True positives | 4 | 4 |
| False positives | 1 | 1 |
| False negatives | 2 | 2 |
| Precision | 0.8000 | 0.8000 |
| Recall | 0.6667 | 0.6667 |
| Deleted-but-recoverable findings flagged | Not reported | 2 |
| Coverage manifest | Not provided | Complete; 6 commits scanned; 3 skipped files listed |
| AI-suppressed findings | Not applicable | 0 (AI filter disabled for parity) |

False positives include predictions matching labeled decoys and predictions
outside the oracle's positive/decoy labels. A `complete` coverage status is
subject to the configured skip threshold; it does not mean there were no
skipped files. The wrapper reports the three paths separately.

## 100-commit deduplication

A second real fixture contained the same synthetic AWS-shaped value in one
tracked file, added on each of 100 commits. Native Gitleaks reported 100
commit-level matches. The wrapper scanned all 100 commits and returned one
deduplicated finding.

| Measure | Native Gitleaks | Wrapper |
|---|---:|---:|
| Commits | 100 | 100 |
| Findings after detection/deduplication | 100 | 1 |
| Coverage status | No manifest | Complete |
| Wrapper elapsed time | Not applicable | 1,225 ms |

This case uses one path. A separate 100-commit fixture with findings across
100 distinct paths exceeded the 30-second lifecycle/parse-stage timeout; see
[`limitations.md`](limitations.md). The successful single-path case must not be
generalized to high-cardinality repositories.

## Scope

`DEVOPS-LAB-EXAM` was not present in the workspace and was **NOT MEASURED**.
These fixture results do not establish precision, recall, or speed on that
repository or on production repositories. The 10- and 1,000-commit speed
measurements used generated repositories without findings.
