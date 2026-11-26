# Known gaps and manual review tasks

This list distinguishes completed local demonstrations from work that still
requires an external environment, approvals, or repository-owner action.

## Not measured or not run

- Findings and precision/recall on `DEVOPS-LAB-EXAM`: **NOT MEASURED**; the
  repository was not present in the workspace.
- The 10- and 1,000-commit speed runs used generated repositories without
  findings. A 100-commit, 100-distinct-finding-path case exceeded the lifecycle
  parse-stage timeout. High-cardinality production performance needs a fix and
  a repeatable benchmark.
- Docker build/run and `make` targets: **NOT RUN** in this wrap-up.
- The child-process network-isolation check was **NOT MEASURED locally**. CI
  now has an Ubuntu container `--network none` probe; verification is pending
  that job passing.
- Native-vs-wrapper comparison with the AI filter enabled on a non-demo,
  labeled fixture: **NOT MEASURED**. The reported parity comparison disabled
  the filter; the separate demo fixture follows the application's demo path.
- Provider-side validity checks and credential revocation: **NOT IMPLEMENTED**.
  The local rotation mock is not evidence that an external credential is safe.

## Local dependency audit

The requested direct audits ran and their unfiltered command output is saved in
[`docs/evidence/pip-audit.txt`](evidence/pip-audit.txt) and
[`docs/evidence/npm-audit.txt`](evidence/npm-audit.txt). `pip-audit -r
requirements.txt` exited 1 with 50 known vulnerabilities across 3 packages.
`npm audit` exited 1 with 9 vulnerabilities (4 moderate, 4 high, 1 critical).
Review and remediate these findings before treating the dependency set as
cleared; this task did not change dependency versions.

## Manual approval and repository work

- Review and approve the 10-minute guide and the proposed KPI-2/KPI-3 scripted
  reference method before treating either as a frozen evaluation baseline.
- Run the demo on the review machine, confirm its Python/Node/Gitleaks setup,
  and record the machine-specific timings.
- Ask the target team to adopt the scanner and provide representative,
  authorized repositories with independent labels.
- Enable and verify branch protection and required CI checks in the target
  GitHub repository; local snippets alone do not enable policy.
- Have repository owners decide whether to rotate any real credentials found.
  Do not put credentials in the demo fixtures or review artifacts.

## Definitions and status

KPI-2 and KPI-3 remain `N/A` under the existing baseline document. The proposed
local mock-service reference is pending guide approval. This file does not
change KPI definitions or tags.
