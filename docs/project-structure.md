# Project Structure

This repository intentionally retains two connected Python layers: `src/shd`
contains the API/storage/core scanner, while `backend` contains the CP1/O2
pipeline and evaluation services. They are imported by the active application
and should not be merged casually.

| Path | Purpose and important files |
|---|---|
| `.github/` | CI workflow. `workflows/ci.yml` installs Python dependencies, prepares fixtures/models, and runs tests. |
| `artifacts/` | Generated benchmark/evidence JSON, plots, model files, and the generated `synthetic_repo_v1` Git fixture. |
| `backend/` | CP1/O2 application services. `scanner/history_walker.py` walks history; `ml/` owns detection, XGBoost, and SHAP; `services/` owns fixtures, benchmarks, artifacts, and rotation. |
| `data/` | Evaluation inputs and frozen split metadata. |
| `docs/` | Maintainer, architecture, setup, dataset, evaluation, contract, audit, and traceability documentation. |
| `fixtures/` | Versioned oracle specification used to generate deterministic test truth. |
| `frontend/` | Vite/React application. `src/api/` contains Axios services; `src/pages/` contains workbench views. |
| `reports/` | Generated baseline metrics and split reports. |
| `runtime/` | Local SQLite databases and runtime notes; database files are ignored. |
| `scripts/` | Reproduction, evaluation, fixture, poster, pre-commit, and health-check commands. Internal `_*.py`/`_*.ps1` helpers support generation workflows. |
| `src/shd/` | Core API and persistence package. `walker_api.py` defines FastAPI routes; `walker_db.py` defines SQLAlchemy models; `walker.py` and scanner modules traverse repositories. |
| `testdata/` | Independent seeded repository generator and ground truth used by the original scanner workflow. |
| `tests/` | Unit, integration, CP1, O2, and fixture-builder tests. |
| Root manifests | `requirements.txt` for Python, `pytest.ini` for test discovery, `.env.example` for configuration, and `LICENSE`. |

## Generated versus source content

Source code lives in `backend/`, `src/`, `frontend/`, and `scripts/`. Dataset
inputs live in `data/`, `fixtures/`, and `testdata/`. Generated outputs live
in `artifacts/`, `reports/`, and ignored `runtime/` databases. This distinction
is documented rather than enforced by moving files because existing imports
and reproducibility commands use the current paths.
