# Combined coverage recheck

The earlier **57.06%** result used the dotted source selector
`--cov=src.shd`. Re-running the explicitly requested directory selector:

```text
python -m pytest --cov=backend --cov=src/shd --cov-report=term-missing
```

completed with **165 passed**, **1 warning**, and **78.26%** coverage (**3,009
of 3,845 statements**). This is **21.20 percentage points** above the earlier
result and passes the existing 75% target. The unchanged denominator but
different per-module attribution shows that the dotted selector did not measure
the same source set reliably: for example, `src/shd/walker_api.py` and
`src/shd/walker_db.py` were previously reported at 0%, but measure 77% and 91%
with the directory selector. No coverage threshold or `no cover` pragma was
changed.

The lowest rows in the corrected report include `backend/main.py` (0%),
`src/shd/cli.py` (20%), and `backend/evaluation_metrics.py` (33%). No new tests
were needed to meet the combined threshold. The complete per-module result is
the terminal coverage table from the command above.
