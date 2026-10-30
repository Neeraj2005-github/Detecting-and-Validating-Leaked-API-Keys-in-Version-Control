# Installation Guide

## Requirements

Install Python 3.11+, Node.js/npm, Git, and optionally Gitleaks. Native
Gitleaks is used when available by the comparison benchmark; the repository
also contains an emulator path for benchmark continuity.

## Python setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment

```powershell
Copy-Item .env.example .env
```

The default is local SQLite at `runtime/shd-local.sqlite3`. Set
`DATABASE_URL` only when a different SQLAlchemy backend is configured. Keep
real values out of `.env.example`, documentation, fixtures, and commits.

## Frontend setup

```powershell
Set-Location frontend
npm install
```

The frontend defaults to `http://localhost:8000`; set `VITE_API_URL` for a
different API origin.

## Start

Backend:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Frontend, in another terminal:

```powershell
Set-Location frontend
npm run dev
```

## Verify

```powershell
python scripts/verify_system_health.py
```

The verifier requires the backend to be running.
