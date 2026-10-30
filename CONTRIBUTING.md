# Contributing

## Before opening a change

1. Read the relevant design and evaluation documents in [`docs/`](docs/).
2. Keep credentials synthetic and masked. Never commit `.env`, provider tokens,
   passwords, or unreviewed generated data.
3. Preserve existing source boundaries unless a migration includes all import,
   script, test, and documentation references.
4. Update documentation when changing API routes, commands, schemas, or
   evaluation interpretation.

## Local checks

```powershell
python -m pytest
Set-Location frontend
npm run build
Set-Location ..
git diff --check
```

With the API running, also run:

```powershell
python scripts/verify_system_health.py
```

The pre-commit configuration runs
[`scripts/pre_commit_hook.py`](scripts/pre_commit_hook.py) against staged
additions. It is a detection gate, not a replacement for tests.

## Pull requests

Describe the behavior changed, tests run, fixture/artifact changes, and any
known limitations. Do not rewrite Git history or include real secret material.
If metrics change, identify the exact input corpus, split, command, and output
artifact.
