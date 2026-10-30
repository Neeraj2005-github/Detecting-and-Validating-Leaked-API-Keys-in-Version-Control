# Detecting Secrets in Version Control

Secret History Detector (SHD) is an academic capstone project for detecting and validating leaked API keys in current source files and Git history.

## Problem

Secrets can remain in old commits even after they are removed from the current working tree. SHD combines Gitleaks detection, Git-history extraction, criticality classification, and an ML filter to produce repository-scoped findings for review.

## Features

- Current-source scanning through the FastAPI API.
- Git-history scanning for deleted or historical secret-bearing files.
- Gitleaks integration for detector rules and raw findings.
- Normalization and criticality classification for supported secret types.
- Optional ML filtering with evaluation reports in `reports/`.
- Repository-scoped findings and scan history stored in SQLite by default.
- React/Vite dashboard for repositories, findings, metrics, and PDF report export.
- Synthetic Git test repository preserved under `testdata/seeded_repo/`.

## Architecture

```text
src/shd/                 API, database models, walkers, metrics, and CLI
backend/                 Gitleaks, normalization, classification, Git history, and ML pipeline
frontend/                React/Vite review dashboard
tests/unit/              Focused unit tests
tests/integration/       API and pipeline integration tests
tests/fixtures/          Reusable test repository builders
testdata/                Ground truth and independent seeded Git repository
reports/                 Evaluation and baseline reports used by the project
docs/                    Capstone specifications, audits, and evaluation notes
scripts/                 Project generation and fixture helper scripts
runtime/                 Ignored local SQLite databases and runtime notes
```

The backend entry point is `src.shd.walker_api:app`. The scan pipeline is in `backend/pipeline.py`; it prepares local or remote repositories, runs Gitleaks, classifies findings, and applies the ML filter. The database layer in `src/shd/walker_db.py` persists repository, scan, current finding, historical finding, and blob records.

## Requirements

- Python 3.11 or newer
- Node.js and npm
- Git
- Gitleaks 8.18 or newer installed on `PATH`

The project does not require the checked-in Gitleaks executable or archives. CI installs Gitleaks separately, and the local runner reports an actionable error when it is unavailable.

## Run the backend

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.shd.walker_api:app --reload --port 8000
```

The same application is available through the compatibility entry point
`uvicorn backend.main:app --reload --port 8000`. The CP1 workbench uses the
REST namespace under `/api/cp1/` for overview, scan, reproduction, benchmark,
and offline rotation actions.

The API documentation is available at `http://127.0.0.1:8000/docs`.

The default development database is `runtime/shd-local.sqlite3`. Set `DATABASE_URL` to use another supported SQLAlchemy database URL.

## CP1 Gate 1 / O1 evidence

Run the deterministic problem reproduction from the repository root:

```powershell
python scripts/reproduce_problem.py
```

This writes the redacted machine-readable evidence to
`artifacts/o1_reproduction_log.json` and the review document to
`docs/o1_reproduction_log.md`. The frozen contract is in
`backend/data/o1_engineering_contract.json` with its readable companion at
`docs/o1_engineering_contract.md`. When the API is running, the complete
structured evidence bundle is available at `GET /o1/evidence` and is rendered
on the frontend's **O1 Evidence** page for inline review and PDF export.

## O2 fixture, history, and detector

Build the versioned synthetic repository and safe grading oracle:

```powershell
python -c "from backend.services.fixture_generator import generate_fixture; generate_fixture()"
```

The added-line walker is available as
`backend.scanner.history_walker.walk_history`; the staged detector is
`backend.ml.detector.detect_lines`. The detector generates
`backend/ml/detector_model.pkl` on first use. It uses `XGBClassifier` when
XGBoost is installed and a deterministic scikit-learn fallback otherwise.
The fixture and oracle are written to `artifacts/synthetic_repo_v1` and
`artifacts/ground_truth_oracle.json`.

## CP1 Extra evidence

`GET /cp1/extras` runs and returns the privacy-safe κ benchmark, frozen-split
XGBoost ablations, TreeSHAP/NDCG risk report, offline rotation MTTR, and
public-repository aggregate counts. Results are persisted in the
`cp1_artifacts` SQLAlchemy table and in `artifacts/` JSON files. The same
bundle is viewable at the frontend's **CP1 Extras** route.

The local pre-commit hook is configured in `.pre-commit-config.yaml` and
blocks staged additions that the detector classifies as likely active
credentials.

## Run the frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

The Vite development server normally runs at `http://localhost:5173`. The frontend uses the local API client configuration and supports `VITE_API_URL` when a different backend URL is required.

## Test data and scans

`testdata/seed_repo.py` creates the synthetic dataset and regenerates the independent Git repository at `testdata/seeded_repo/`. That directory intentionally contains its own `.git` directory and commit history. It is ignored by the outer repository so it is not accidentally staged as an embedded repository.

Run the generator only when you intend to recreate the fixture:

```powershell
python testdata/seed_repo.py
```

The application can scan local paths or remote Git URLs. Repository scans write findings with the repository key and `GET /findings?repo_id=...` filters them to the selected repository. A request to `GET /findings` returns the aggregate findings list.

## Tests and evaluation

Run the complete test suite from the repository root:

```powershell
python -m pytest
```

The ML training and evaluation commands are:

```powershell
python -m backend.ml_filter.train
python -m backend.ml_filter.evaluate
```

The deterministic O2 evaluation corpus is `data/o2_evaluation.json` with 20
labeled examples: 8 training, 4 validation, and 8 test examples. Baseline A
uses Gitleaks only; Baseline B applies the ML filter to the same test examples.

Run the reproducible evaluation and coverage checks with:

```powershell
& ".\.venv\Scripts\python.exe" -c "from backend.evaluation_metrics import evaluate; import json; print(json.dumps(evaluate(), indent=2))"
& ".\.venv\Scripts\python.exe" -m pytest --cov=backend --cov=src --cov-report=term-missing
```

Evaluation outputs are written to `reports/`. Baseline B is intentionally marked invalid when the test set contains a leakage feature that perfectly separates labels; see `reports/baseline_metrics.json` and `backend/ml_filter/evaluate.py` for the validation warning.

## Documentation

Supporting specifications and review material are in `docs/`, including the problem charter, traceability matrix, workflow notes, dataset manifest, and evaluation report.

## Limitations and future work

- The current frontend is designed for a trusted, single-user local deployment and has no authentication or RBAC.
- Gitleaks must be installed separately and available on `PATH`.
- The ML evaluation dataset is synthetic and requires a leakage-free test split before its results can be used as a valid contribution claim.
- Risk scoring, rotation scheduling, and verification adapters remain stubs for future work.
### O2.4-O2.6 one-command reproduction

Run the complete benchmark and evidence suite from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\reproduce_o2.py
```

This regenerates `artifacts\synthetic_repo_v1`, writes
`artifacts\ground_truth_oracle.json` and `artifacts\o2_benchmark_kpis.json`,
and runs `tests\test_cp1_complete.py`. Native Gitleaks is used when available;
otherwise the report records the deterministic rule-set emulator. Test
failures are appended to `artifacts\failure_log.json`.
