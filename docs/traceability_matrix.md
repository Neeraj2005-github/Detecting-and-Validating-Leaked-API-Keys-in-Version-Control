# Traceability Matrix

| Requirement / objective | Implementation | Evidence |
| --- | --- | --- |
| FR-1: walk repository history | `src/shd/walker.py` | `tests/test_walker.py` |
| FR-2 / O2: baseline secret matching | `src/shd/matcher.py` | `tests/test_matcher.py` |
| FR-3: normalize and deduplicate findings | `src/shd/dedup.py` | `tests/test_dedup.py` |
| Dataset split and ground truth validation | `src/shd/dataset.py` | `tests/test_dataset.py` |
| Metrics and evaluation | `src/shd/metrics.py` | `tests/integration/test_metrics.py` |
| End-to-end orchestration | `src/shd/cli.py` | `tests/integration/test_pipeline_e2e.py` |
| NFR-5: reproducible test/coverage execution | `pytest.ini`, `.coveragerc` | Full pytest and coverage commands |
| O3-O5 | Deferred to Semester VIII | Explicitly deferred |

The reference/eval split must be frozen before baseline metrics are reported.