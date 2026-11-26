# Reproducible local baseline

Run the end-to-end benchmark from a clean Git checkout with Python dependencies,
Gitleaks, and `detect-secrets==1.5.0` available:

```powershell
python scripts/baseline.py
```

On Windows, the PowerShell entry point also works:

```powershell
.\scripts\baseline.ps1
```

The script clones the clean checkout into a temporary directory, generates the
100- and 1,000-commit Git fast-import fixtures, runs five native Gitleaks,
wrapper, and detect-secrets scans per size, and writes the comparison report
back to the checkout. The fixture repositories are temporary; only the
aggregate JSON and Markdown reports persist:

- `artifacts/comparison.json`
- `docs/comparison.md`

The Makefile targets delegate to `scripts/baseline.py`; they are not required
for this workflow. The baseline command itself does not build or run Docker.
The separate `build` task invokes Docker and must only be run in an environment
where Docker is permitted.
