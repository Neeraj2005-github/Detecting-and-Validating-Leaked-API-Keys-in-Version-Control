# SHD Review-2 Audit

## Verified baseline

- Backend: `34 passed`, including the API acceptance test.
- Coverage: `86%` for `src/shd` (`pytest --cov=src/shd --cov-report=term-missing`).
- Frontend: `npm run build` passes from `frontend/`.
- Local API: verified with SQLite and a temporary Git repository containing a fake AWS key.
- API result: one blob, one finding, status `completed`.
- Raw credential check: the complete test key was absent from both `/findings` and historical blob responses.

## Technical pipeline status (not O1)

| Technical requirement | Status | Evidence |
| --- | --- | --- |
| Accept local repository path | Complete | `source_scanner.py` validates an existing Git directory |
| Recursive source scan | Complete | Supported extensions, nested directories, empty files |
| Skip generated/vendor paths | Complete | `.git`, `.venv`, `__pycache__`, `node_modules`, `build`, `dist` |
| Binary-safe handling | Complete | NUL and UTF-8 checks count skipped files |
| Secret detection | Partial | `detect-secrets` baseline covers AWS, GitHub, Slack, and entropy detectors |
| Redacted findings | Complete | Fingerprint and masked preview only in source/API/database records |
| Database persistence | Complete for O1 | `repositories`, `scans`, `findings`; history ledger remains separate |
| REST API | Complete for O1 | `/scan`, `/scans`, `/findings`, `/repositories`, `/health` |
| Dashboard findings | Complete for O1 | Existing history UI plus redacted findings panel |
| Unit/integration tests | Partial but usable | 34 passing; API and scanner tests added |
| Dataset split and baseline metrics | Missing as a frozen artifact | Manifest documentation exists, but no authoritative JSON dataset was present |

This table describes the technical M1/M2-era pipeline only. Under the Weeks 6–8 specification, O1 is the problem-charter and threat-model validation objective. Its status is recorded in [o1_problem_charter.md](o1_problem_charter.md), and it is not complete until the interview/survey and AC-1 through AC-4 evidence exist.

## Actual API

- `POST /scan` accepts `{repo_path, repo_id}` and returns scan ID, history blob count, and finding count.
- `GET /scans` returns scan counters and status.
- `GET /findings?repo_id=...` returns redacted findings.
- `GET /repositories` returns indexed repositories.
- Existing history endpoints remain under `/repos/{repo_id}/...`.
- `GET /health` checks database connectivity.

## Database tables

- `repositories`: repository ID, path, created time.
- `scans`: repository, lifecycle timestamps, discovered/scanned/skipped file counts, finding count, status.
- `findings`: scan, path, line, type, detector, confidence, SHA-256 fingerprint, masked preview, status.
- `blob_records`: existing history ledger; detector matches are redacted before persistence.

## Explicit gaps

- No frozen `docs/eval/dataset_manifest.json`, so precision, recall, F1, confusion matrix, and split counts cannot be truthfully reported yet.
- The detector is `detect-secrets`, not the required Gitleaks O2 baseline. Existing detector metrics must not be presented as Gitleaks results.
- The current fingerprint is unsalted SHA-256; the specification requires a salted hash and last-four metadata before the storage contract is complete.
- Detector coverage is narrower than the final target: provider validation, generic password/database-password classification, JWT lifecycle, and authorization semantics remain future work.
- Git history currently covers reachable branch and remote refs, not every tag/unreachable object; merge deletion handling is first-parent based.
- API has no authentication, rate limiting, repository size/time quotas, or authorization boundary. It is suitable for localhost demonstration only.
- Frontend remains a focused history workbench rather than the full sidebar/dashboard/metrics product described in the target specification.

## Review-2 demo

1. Start API with `DATABASE_URL=sqlite:///./runtime/shd-o1-check.sqlite3` and `PYTHONPATH=src`.
2. Start Vite from `frontend/`.
3. Open `http://localhost:5173/`.
4. Scan a synthetic Git repository with a fake credential.
5. Show scan counters and the redacted findings table.
6. Open the API `/findings` response and show the fingerprint/masked preview.
7. Show the existing commit timeline and deleted blobs.
8. Run `pytest -q` and `pytest --cov=src/shd --cov-report=term-missing`.
9. Explain that frozen dataset metrics are the next evidence gate, not an invented result.

## Git history observed

The local branch is `main` with three commits:

- `2c5de7f First commit of phase 1`
- `d394c84 Second commit`
- `1725655 Third commit`

The repository also contains uncommitted project files and generated/local artifacts. Do not rewrite history for Review-2; demonstrate it with:

```powershell
git log --oneline --graph --decorate --all
git status
git diff
```
