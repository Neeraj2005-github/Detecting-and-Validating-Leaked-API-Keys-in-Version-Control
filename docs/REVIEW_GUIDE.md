# Ten-minute review guide

All fixture values are synthetic. Do not paste a real credential into the
scanner during the review. Run commands from the repository root.

## Demo timeline

### 0:00-1:00 - Open the workbench

Run `.\scripts\demo.ps1` on Windows or `bash scripts/demo.sh` in Bash. The script
starts the local API and frontend and opens the scanner page. The page should
show the repository input, Fast scan and AI filter toggles, an empty-state
explanation, and no fabricated findings before a scan is run.

### 1:00-2:30 - Clean repository

Create a small clean repository:

```powershell
$clean = Join-Path $env:TEMP 'secretguard-clean-demo'
New-Item -ItemType Directory -Force (Join-Path $clean 'src') | Out-Null
git -C $clean init --quiet --initial-branch=main
git -C $clean config user.name 'Review Demo'
git -C $clean config user.email 'demo@example.test'
Set-Content -Path (Join-Path $clean 'src\app.py') -Value "def main():`n    return 'ready'" -Encoding utf8
git -C $clean add .
git -C $clean commit --quiet -m 'initial clean fixture'
python -m src.shd.cli scan $clean --format json --out (Join-Path $env:TEMP 'secretguard-clean.json')
```

Observed sample output for the equivalent one-file source fixture:

```text
commits=1 branches=1 tags=0 findings=0 result=no secrets detected skipped=0 lifecycle=VALIDITY_UNKNOWN exit-codes=0 completed, 1 findings (--fail-on-findings), 2 skipped threshold, 3 runtime, 4 invalid
```

Expected: no finding rows and exit code 0. A no-match result only describes
configured patterns and reported coverage; it is not proof that all credentials
are valid or absent.

### 2:30-4:00 - Planted-secret sample

```powershell
python -m src.shd.cli scan --demo --format json --out (Join-Path $env:TEMP 'secretguard-planted.json')
```

Observed sample output from the bundled synthetic repository:

```text
commits=6 branches=2 tags=1 findings=6 result=6 found skipped=3 lifecycle=DETECTED exit-codes=0 completed, 1 findings (--fail-on-findings), 2 skipped threshold, 3 runtime, 4 invalid
```

Expected: masked findings, explicit skipped-file reasons, and a coverage
summary. Exit code 0 is the default when `--fail-on-findings` is not set; it
does not mean there were no findings.

### 4:00-6:00 - Deleted-but-recoverable finding

In the UI, select **Try demo repo**, leave the default AI filter setting
unchanged, and click **Scan repository**. Open **Hidden in Git History** and
expand a row whose lifecycle is **Deleted but recoverable**. The measured API
run on the bundled fixture reported two such findings; the UI should show the
current scan's actual findings and their first/last/removal commits,
recoverability, exposure duration, and risk breakdown.

Expected: the secret remains masked. Gitleaks-only output has no
deleted-but-recoverable lifecycle label; the wrapper adds it from repository
history and coverage data.

### 6:00-7:30 - Shallow repository refusal

```powershell
$source = (Resolve-Path '.\artifacts\synthetic_repo_v1').Path.Replace('\', '/')
$shallow = Join-Path $env:TEMP 'secretguard-shallow-demo'
git clone --quiet --depth 1 --no-local "file:///$source" $shallow
python -m src.shd.cli scan $shallow --format json --out (Join-Path $env:TEMP 'secretguard-shallow.json')
$LASTEXITCODE
```

Expected: the CLI refuses the shallow clone and returns **4** before claiming
complete coverage.

### 7:30-9:00 - Audit-log tamper detection

```powershell
$env:SHD_DEMO_AUDIT = Join-Path $env:TEMP 'secretguard-demo-audit.json'
python -c "import os; from backend.services.audit_log import append_audit; append_audit(os.environ['SHD_DEMO_AUDIT'], 'reviewer', 'scan', 'synthetic-finding')"
python -m src.shd.cli verify-audit --audit $env:SHD_DEMO_AUDIT
$LASTEXITCODE
python -c "import json, os; p=os.environ['SHD_DEMO_AUDIT']; data=json.load(open(p, encoding='utf-8')); data[0]['action']='tampered'; json.dump(data, open(p, 'w', encoding='utf-8'))"
python -m src.shd.cli verify-audit --audit $env:SHD_DEMO_AUDIT
$LASTEXITCODE
```

Expected: the untampered chain returns 0; after changing a signed field, the
verification command returns 3. Remove the temporary audit file after the
review:

```powershell
Remove-Item -LiteralPath $env:SHD_DEMO_AUDIT
Remove-Item -LiteralPath $clean -Recurse -Force
Remove-Item -LiteralPath $shallow -Recurse -Force
```

### 9:00-10:00 - Close

Show the stage tracker, export controls, and the review questions below. State
the measurement limits before presenting the numbers in
[`comparison.md`](comparison.md).

## Q&A defence

### Why wrap Gitleaks instead of replacing it?

Gitleaks supplies the native detection engine. The wrapper adds an auditable
coverage manifest, lifecycle and recoverability analysis, reasoned
suppression, HMAC-based deduplication, masked reports, and a fail-closed local
remediation workflow. The comparison results are synthetic and do not claim
that the wrapper replaces a provider verifier.

### What is new compared with Gitleaks or TruffleHog?

The contribution is the exposure-lifecycle view: first/last-seen and removal
commits, reachable-ref versus local-object recoverability, exposure duration,
and a visible risk-factor breakdown. Gitleaks does not emit this lifecycle
report. TruffleHog has its own verification capabilities; this project does
not claim provider validity checks or parity with those verifiers.

### How do deduplication and HMAC work?

The normalizer computes a keyed HMAC-SHA256 of the matched value. The wrapper
deduplicates by that fingerprint and secret type, then reports only a masked
preview. Configure `SHD_HMAC_KEY` consistently and protect it in deployment;
the CLI's random per-run default is not stable across runs. HMAC identifiers
are not encryption and do not replace access controls.

### Why does exit code 2 exist?

It signals that the configured skipped file/line threshold was exceeded, so
automation can distinguish a scan with excessive skips from one within policy.
Exit code 1 is reserved for findings when `--fail-on-findings` is requested;
exit code 4 refuses an invalid target such as a shallow repository.

### What are the limitations?

Archives are not recursively extracted; submodules and Git LFS objects are not
fetched; and encoded, split, or otherwise unrecognized values can be missed.
Skipped files are listed in the coverage manifest. A `complete` badge means
the configured repository/ref and skip-threshold checks passed, not that every
file format was scanned. High finding counts across many distinct paths can
exceed the current lifecycle-stage timeout.

### What is planned for Semester VIII?

Add a validity check and richer rotation verification against a local mock
service before considering any provider integration. The current mock
state-machine demonstration is fail-closed and does not rotate real
credentials.

### How are KPI-2 and KPI-3 baselines defined?

The existing baseline marks KPI-2 validity and KPI-3 rotation as `N/A` for
Gitleaks. A scripted reference using the owned local mock service is proposed,
but guide approval is pending. This project has not changed either KPI
definition.
