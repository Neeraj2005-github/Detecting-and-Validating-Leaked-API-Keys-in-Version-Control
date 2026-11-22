# Exposure lifecycle and risk scoring

The CP1 scan response enriches each Gitleaks finding with commit and exposure
metadata. Raw Gitleaks values are inspected only in process memory while the
relevant file history is checked; the lifecycle response contains commit IDs,
durations, booleans, and masked findings, not the raw value.

## Lifecycle fields

| Field | Meaning |
|---|---|
| `first_seen_commit` | Earliest path-history commit whose blob contains the detected value |
| `last_seen_commit` | Latest path-history commit whose blob contains the value |
| `removed_in_commit` | First later path-history commit whose blob no longer contains it; null while active |
| `days_exposed` | Commit-time interval from first appearance to removal, or to scan time while active |
| `lifecycle_status` | `ACTIVE_IN_HEAD`, `DELETED_BUT_RECOVERABLE`, or `UNREACHABLE_LOCAL_ONLY` |
| `recoverable_from_fresh_clone` | True when the value is present in HEAD or in a commit reachable from refs |
| `recoverable_from_local_objects` | True when evidence is found only in enumerated local commits |

Coverage exposes reachable and locally available commit IDs. The lifecycle
analysis runs only for Gitleaks findings and inspects those findings' paths,
not every repository file a second time. The current Gitleaks invocation scans
refs; it does not guarantee discovery of dangling objects that Gitleaks itself
does not report. `UNREACHABLE_LOCAL_ONLY` therefore describes local-only
evidence available to the lifecycle analyzer, not a guarantee of exhaustive
scanning of all unreachable Git objects.

The path-history calculation assumes a Git path identifies the same file
through its history. Renames, divergent branches, submodules, LFS objects, and
encoded or split values can make exposure dates incomplete; consult
[limitations](./limitations.md).

## Risk score

The 0-100 score is an additive, inspectable weighted sum:

```text
100 * (
  0.25 * lifecycle_factor +
  0.25 * (secret_severity / 5) +
  0.20 * min(days_exposed / 365, 1) +
  0.15 * public_repository_flag +
  0.15 * min(entropy / 4, 1)
)
```

Lifecycle factors are 1.0 for active-in-HEAD, 0.7 for deleted-but-recoverable,
and 0.45 for local-only. Severity is 5 for private keys and major provider
tokens, 4 for database/service credentials, and 3 for generic assignments and
unmapped types. Entropy is Shannon entropy from the detector. Every term and
its weighted points are returned in `risk_breakdown`; the score is not a
validity verdict.

`public_repo` is an explicit scan request flag and defaults to false. A local
scan is not assumed to be public.

## Remediation

Rotate or revoke through the credential provider first. The response marks
provider rotation as `ROTATION_NOT_VERIFIED`; SecretGuard does not contact
providers. The optional Git history cleanup commands are scoped to the finding
path and then push rewritten refs:

```powershell
git filter-repo --path '<finding path>' --invert-paths
git push --force --all
git push --force --tags
```

History rewriting is not credential revocation. A finding must not be
considered provider-verified based only on removing its source or rewriting
Git history. The existing offline state machine verifies only its local mock
service.
