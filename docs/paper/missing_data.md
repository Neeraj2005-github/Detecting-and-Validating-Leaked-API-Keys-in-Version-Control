# Missing Data

## F3 Per-stage duration breakdown

- Status: NOT MEASURED
- Reason: No measured per-stage clone/preflight/scan/parse/filter/dedupe/mask/lifecycle/report durations for a small and larger repository
- Producing command: `python -m src.shd.cli scan <repo> --format json --verbose`

## F4 DEVOPS-LAB-EXAM precision fix

- Status: NOT MEASURED
- Reason: DEVOPS-LAB-EXAM and category-split before/after findings are not present
- Producing command: `python -m src.shd.cli scan DEVOPS-LAB-EXAM --format json --out artifacts/devops_lab_exam_scan.json --verbose`

## F5 Detection per case category

- Status: NOT MEASURED
- Reason: Planted/found counts for rename, force-push dropped, base64, PEM, split secret, and other categories are incomplete
- Producing command: `python scripts/research_benchmark.py --sizes 100 1000 --runs 5 --output artifacts/research_benchmark_categories.json; python -m pytest tests/test_phase_b_edge_cases.py tests/test_precision_rules.py -q`

## F1 10000-commit point

- Status: NOT MEASURED
- Reason: The 10000 repository generation stopped at 4533 commits
- Producing command: `python scripts/research_benchmark.py --sizes 100 1000 10000 --runs 5 --output artifacts/research_benchmark_100_1000_10000.json`

