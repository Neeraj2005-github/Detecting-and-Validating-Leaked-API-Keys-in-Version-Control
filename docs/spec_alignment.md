# Weeks 6–8 Specification Alignment

This record compares the pasted Weeks 6–8 Concept C specification with the repository as it exists on 2026-09-17. The referenced diary/design file was not present in the workspace, so the pasted specification is the working authority.

## Concept C mapping

| Module/objective | Specification requirement | Current repository status | Decision |
| --- | --- | --- | --- |
| O1 | Problem charter, threat model, trust boundary, survey/interview, AC-1 to AC-4 | Charter and threat-model evidence were missing; technical scanner existed | Added [o1_problem_charter.md](o1_problem_charter.md). O1 remains pending interview and acceptance evidence |
| M1 | Complete Git history, commit metadata, diffs, changed/deleted files, recoverable contents | Reachable commit/blob walking and deleted-file recovery exist; metadata/diff endpoint is now available | Keep and extend with tests; do not call it O1 |
| M2 | Gitleaks external subprocess and JSON normalization | Current matcher uses the `detect-secrets` Python library | Conflict. Replace or wrap as the next implementation phase; do not claim Gitleaks baseline |
| M3 | Modular canonical provider/category classification | Narrow detector-name mapping exists in `matcher.py` | Partial. Add a separate classifier after Gitleaks normalization |
| M4 | Asset/context mapping | Repository, file, commit, HEAD status are partly stored | Partial. Branch, exposure age, and asset identity require explicit fields/evidence |
| M5/O3 | Read-only AWS/GitHub/JWT validity adapters | Not implemented | Deferred |
| M8/O3 | Frozen explainable risk formula | Not implemented | Deferred |
| M7/O4 | Re-verification scheduler and MTTR | Not implemented | Deferred |

## Conflicts corrected

1. The previous Review-2 language treated the current-source scanner as O1. The authoritative terminology now treats it as technical M1/M2 pipeline work; O1 is the research/problem-validation objective.
2. The current detector is `detect-secrets`, not Gitleaks. Existing findings and metrics must not be described as the Gitleaks reproducible baseline.
3. Existing API findings use an unsalted SHA-256 fingerprint. The specification requires a salted hash and last-four-character metadata; this must be changed before the M2/M5 persistence claim is complete.
4. Existing historical data can demonstrate Git persistence/removal, but cannot demonstrate provider validity or revocation.
5. Existing local SQLite execution is a development fallback. The target database requirement is MySQL; deployment and database tests must use MySQL-compatible configuration before that requirement is marked complete.

## Current implementation evidence

- M1-era history code: `src/shd/walker.py`
- Existing detector conflict: `src/shd/matcher.py`
- Current API: `src/shd/walker_api.py`
- Current storage: `src/shd/walker_db.py`
- Existing tests: `tests/`
- Existing dataset workflow: `docs/WORKFLOW_M3_TO_M4.md`, `src/shd/dataset.py`, `src/shd/metrics.py`

## Next implementation phase

Implement M2 only after the O1 evidence is collected:

1. Add a Gitleaks executable/configuration contract.
2. Run it as a subprocess without shell interpolation.
3. Parse JSON into the existing internal finding boundary.
4. Add synthetic multi-commit ground truth and detector integration tests.
5. Replace unsalted fingerprints with salted hashes and last-four metadata.
6. Recompute actual baseline metrics from executed runs.

No O3/O4 code or UI should be added as if it were operational before those prerequisites exist.
