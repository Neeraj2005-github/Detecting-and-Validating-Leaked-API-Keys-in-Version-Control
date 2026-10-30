# Usage Guide

## Workbench

Open `http://localhost:5173/vaultguard/home`. The workbench provides Home,
Detection & Validation, Architecture & Security, Benchmarks & Accuracy, and
CI/CD & Automation views.

The scanner can load the deterministic synthetic fixture, scan a local path, or
accept a Git URL. Use synthetic data for demonstrations unless a repository is
explicitly authorized.

## API workflow

```powershell
$body = '{"repo_url":null,"synthetic_fixture":true,"use_ai_filter":true}'
Invoke-RestMethod http://localhost:8000/api/cp1/scan -Method Post `
  -ContentType 'application/json' -Body $body
```

The response contains prioritized findings, suppressed findings, lifecycle
summary counts, and NDCG values. Finding values are masked.

## Rotation demonstration

Use the finding's rotate action in the UI or call:

```powershell
Invoke-RestMethod http://localhost:8000/api/cp1/rotate/<finding_id> `
  -Method Post -ContentType 'application/json' -Body '{}'
```

The sandbox is in-memory SQLite and synthetic. A `VERIFIED_SAFE` result is not
proof that a real provider credential has been revoked.

## Reproducible evidence

- O1 reproduction: `python scripts/reproduce_problem.py`
- O2 fixture and benchmark: `python scripts/reproduce_o2.py`
- CP1 extras: `GET /cp1/extras`
- API documentation: `GET /docs`
