# Combined backend and wrapper coverage gap

The full suite completed with **165 passed** and **913 warnings**. The requested
combined command was:

```text
python -m pytest --cov=backend --cov=src.shd --cov-report=term-missing:skip-covered --cov-fail-under=75
```

Result: **57.06%** (2,194 of 3,845 statements covered); the 75% gate failed.
At least 690 additional statement executions are needed to reach 75% overall
with the current statement denominator. The table gives the exact module
coverage and the additional statements each module individually needs to
reach 75%; reaching 75% module-by-module would require 901 additional
executions because modules already above 75% cannot offset module-specific
gaps.

| Module | Statements | Missed | Coverage | Additional executions for 75% |
|---|---:|---:|---:|---:|
| `backend/detection/gitleaks_runner.py` | 136 | 26 | 81% | 0 |
| `backend/detection/normalizer.py` | 36 | 4 | 89% | 0 |
| `backend/evaluation.py` | 39 | 8 | 79% | 0 |
| `backend/evaluation_metrics.py` | 70 | 47 | 33% | 30 |
| `backend/extractor/git_history.py` | 57 | 16 | 72% | 2 |
| `backend/main.py` | 2 | 2 | 0% | 2 |
| `backend/ml/dataset_kappa.py` | 60 | 20 | 67% | 5 |
| `backend/ml/detector.py` | 223 | 43 | 81% | 0 |
| `backend/ml/shap_risk_scorer.py` | 35 | 2 | 94% | 0 |
| `backend/ml_filter/evaluate.py` | 91 | 7 | 92% | 0 |
| `backend/ml_filter/features.py` | 29 | 1 | 97% | 0 |
| `backend/ml_filter/train.py` | 66 | 3 | 95% | 0 |
| `backend/pipeline.py` | 82 | 25 | 70% | 5 |
| `backend/scanner/history_walker.py` | 134 | 34 | 75% | 1 |
| `backend/services/artifact_store.py` | 38 | 17 | 55% | 8 |
| `backend/services/audit_log.py` | 33 | 1 | 97% | 0 |
| `backend/services/benchmark_engine.py` | 127 | 26 | 80% | 0 |
| `backend/services/coverage.py` | 121 | 22 | 82% | 0 |
| `backend/services/dependency_checker.py` | 45 | 13 | 71% | 2 |
| `backend/services/exposure_lifecycle.py` | 98 | 13 | 87% | 0 |
| `backend/services/fixture_generator.py` | 107 | 6 | 94% | 0 |
| `backend/services/o1_reproducer.py` | 117 | 34 | 71% | 5 |
| `backend/services/oracle_loader.py` | 48 | 9 | 81% | 0 |
| `backend/services/report_parser.py` | 17 | 3 | 82% | 0 |
| `backend/services/repository_ingestion.py` | 170 | 31 | 82% | 0 |
| `backend/services/resource_profile.py` | 134 | 35 | 74% | 2 |
| `backend/services/rotation_state_machine.py` | 51 | 1 | 98% | 0 |
| `src/shd/cli.py` | 174 | 43 | 75% | 0 |
| `src/shd/dataset.py` | 33 | 1 | 97% | 0 |
| `src/shd/dedup.py` | 27 | 1 | 96% | 0 |
| `src/shd/matcher.py` | 29 | 17 | 41% | 10 |
| `src/shd/metrics.py` | 43 | 12 | 72% | 2 |
| `src/shd/source_scanner.py` | 98 | 21 | 79% | 0 |
| `src/shd/walker.py` | 129 | 112 | 13% | 80 |
| `src/shd/walker_api.py` | 787 | 787 | 0% | 591 |
| `src/shd/walker_db.py` | 208 | 208 | 0% | 156 |

No coverage threshold or `no cover` pragma was changed. The largest gaps are
`src/shd/walker_api.py`, `src/shd/walker_db.py`, and `src/shd/walker.py`.
