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
