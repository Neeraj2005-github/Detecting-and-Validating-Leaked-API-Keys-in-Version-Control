# KPI baseline

| KPI | Status | Evidence |
|---|---|---|
| KPI-1 | NOT MEASURED | Requires an approved 5+ criterion rubric and holdout run |
| KPI-2 validity | N/A | Gitleaks does not determine credential validity |
| KPI-3 rotation | N/A | Gitleaks does not verify revocation or rotation |
| KPI-4 performance | NOT MEASURED | Requires identical corpus, resource envelope, and 5+ runs |
| KPI-5 false-positive rate | NOT MEASURED | Requires real holdout labels and independent oracle |
| KPI-6 lifecycle completeness | NOT MEASURED | Requires the complete lifecycle transition corpus |

KPI-2 and KPI-3 require guide approval before definition freezing. Proposed method: an owned local mock credential service with scripted active/inactive states.
