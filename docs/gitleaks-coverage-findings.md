# Gitleaks 8.18.4 coverage findings

Measured on Windows 2026-11-19 with native `gitleaks.exe` 8.18.4.

## Fixture

The measured fixture had:

- 4 reachable commits
- one active `main` branch
- one tag: `v1-coverage`
- one feature commit on a branch that was deleted after it was merged
- a merge commit

## Native result

The native scan returned 2 findings:

- AWS example marker on `main.env`
- GitHub example marker on `feature.env`

The feature finding was committed on a branch that was subsequently deleted. The tagged feature commit was reported by native Gitleaks. The tag did not add a separate commit.

## Wrapper compensation

The wrapper enumerates `rev-list --all`, branches, tags, and every commit's diffs. It does not count local reflogs as coverage. This preserves branch/tag/merge/deleted-branch evidence independently of a Gitleaks report. Coverage manifests include shallow state, reachable commit count, scanned commit count, unreachable object count, and completeness status. A shallow repository is refused before reporting results.

## Surface coverage table

| Fixture surface | Secrets planted | Gitleaks findings | Missed | Wrapper compensation |
|---|---:|---:|---:|---|
| Active main commit | 1 | 1 | 0 | Native result plus wrapper lifecycle comparison |
| Branch commit | 1 | 1 | 0 | Enumerate all refs and deleted branch commit identities |
| Tag | 0 additional | 0 additional | 0 additional | Record tag refs; tagged commit is already represented by commit identity |
| Merge commit | 0 additional | 0 additional | 0 additional | Diff every parent/commit and record merge context |
| Deleted branch | 1 | 1 | 0 | Wrapper scans reachable merge history and records branch/tag lifecycle |
| Force-push dropped commit | 1 test | Not measured until fixture run | NOT MEASURED | `git fsck --unreachable --no-reflogs`; unreachable count and completeness evidence |
