# Usage Guide

## Workbench

Open `http://localhost:5173/vaultguard/scanner`. The workbench provides Home,
Detection & Validation, Architecture & Security, Benchmarks & Accuracy, and
CI/CD & Automation views.

The scanner can load the deterministic synthetic fixture, scan a local path, or
accept an HTTPS Git URL. Use synthetic data for demonstrations unless a
repository is explicitly authorized. Fast scan and AI filtering are separate
options.

## API workflow

```powershell
$body = '{"repo_url":null,"synthetic_fixture":true,"use_ai_filter":true}'
$started = Invoke-RestMethod http://localhost:8000/api/cp1/scan -Method Post `
  -ContentType 'application/json' -Body $body
$started
Invoke-RestMethod "http://localhost:8000/api/cp1/jobs/$($started.job_id)"
```

The first request starts a background job. Poll its job route for stage
progress, elapsed time, sanitized errors, and the final result. Completed
findings contain masked matches, lifecycle/recoverability fields, and a visible
risk breakdown.

## Rotation demonstration

Use the finding's rotate action in the UI or call:

```powershell
Invoke-RestMethod http://localhost:8000/api/cp1/rotate/<finding_id> `
  -Method Post -ContentType 'application/json' -Body '{}'
```

The sandbox is local and synthetic. A `VERIFIED_REVOKED` result confirms only
the local mock-service state transition; it does not prove that a real
provider credential has been revoked.

## Reproducible evidence

- O1 reproduction: `python scripts/reproduce_problem.py`
- O2 fixture and benchmark: `python scripts/reproduce_o2.py`
- CP1 extras: `GET /cp1/extras`
- API documentation: `GET /docs`
