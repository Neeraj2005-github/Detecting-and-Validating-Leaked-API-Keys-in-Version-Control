# O1 Problem Charter and Threat Model

## Project identity

**Project:** SecretGuard — Risk-Prioritized Detection and Rotation Verification of Leaked Credentials in Version Control History

**Selected concept:** Concept C, Hybrid Pipeline.

The technical implementation currently lives in the SHD (Secret History Detector) repository. SHD is the existing product/interface name; SecretGuard is the research project name used by the Weeks 6–8 specification.

## Problem statement

A credential removed from the current working tree can remain recoverable in Git history, deleted blobs, old branches, or other reachable objects. Removing a line is therefore evidence of source removal only; it is not evidence that the provider credential was revoked or rotated.

The project will build a reproducible historical detection pipeline, classify findings, preserve safe evidence, and later support authorized provider verification and rotation measurement. Plaintext credentials are never persisted, logged, returned by the API, or displayed in the frontend.

## Research question

Can a reproducible Git-history detection pipeline identify synthetic leaked credentials, preserve enough redacted evidence to distinguish current from historical exposure, and provide a sound basis for later validity and rotation verification without claiming that Git deletion equals revocation?

## O1 validation plan

The O1 claim is problem and threat-model validation, not implementation of the current-source scanner. The following evidence is required before O1 is marked complete:

- A short structured survey/interview with 2–3 developers or senior engineers, where participants and consent permit.
- A completed threat model and trust-boundary review.
- Acceptance evidence for AC-1 through AC-4 below.
- Explicit scope and out-of-scope decisions.

No participant responses are invented in this document. The interview instrument and evidence table are ready for completion.

### Interview instrument

Ask each participant the same questions and record anonymized role, date, consent status, and summarized response. Do not record credentials or confidential repository contents.

1. Have you seen a credential removed from source control but remain available in history?
2. What evidence would convince you that a detected credential was actually rotated or revoked?
3. Which false positives are most costly in your workflow?
4. What information must a finding preserve for an incident review?
5. What would make a historical secret report unsafe or unusable?

### Evidence register

| Evidence | Status | Notes |
| --- | --- | --- |
| Interview/survey with 2–3 participants | Pending | Complete only with authorized participants and anonymized notes |
| Threat model | Complete as design baseline | Review after M1/M2 integration |
| Trust boundary | Complete as design baseline | No provider calls are in the current implementation |
| AC-1 to AC-4 | Pending validation | Criteria below define the required evidence |

## Threat model

### Assets

- Git repository paths, URLs, commit metadata, diffs, and deleted-file history.
- Credential findings and their classification context.
- Salted fingerprints and last-four-character previews.
- Ground-truth labels and evaluation artifacts.
- Later provider verification results and verification history.

### Adversaries and failure modes

- An attacker who can read repository history or application responses.
- An attacker who can submit an arbitrary local path or remote URL to a networked deployment.
- Accidental plaintext leakage through logs, database rows, API responses, reports, frontend state, or test output.
- False positives that cause unnecessary rotation or alert fatigue.
- False negatives caused by unsupported credential formats, binary/encoding issues, or incomplete Git reachability.
- Incorrect claims that deletion, replacement, or a matching pattern proves revocation or validity.

### Security properties

- No plaintext secret storage or display.
- Detection is reproducible from repository evidence and detector version.
- Current presence and historical presence are distinct states.
- Provider verification is read-only, authorized, rate-limited, and explicitly represented as unknown when it cannot safely run.
- Git evidence never substitutes for provider revocation evidence.
- Evaluation splits prevent repository/file/commit-family leakage.

## Trust boundary

```text
[Analyst browser]
       |
       | masked API requests/responses
       v
[SecretGuard API and worker]
       |                    \
       | safe metadata         \ authorized read-only verification (future O3)
       v                       v
[MySQL metadata store]     [Provider sandbox APIs]
       ^
       |
[Local repository or approved remote clone]
```

The repository and provider systems are external/untrusted inputs. The API must validate paths/URLs, constrain resources, avoid shell interpolation, and redact detector values before persistence or response. The current localhost implementation is not an authenticated production service.

## Acceptance criteria

### AC-1: Problem distinction

Given a synthetic credential committed and later removed, the evidence and documentation clearly distinguish:

- present in current source,
- present only in history,
- removed from source,
- verified revoked, and
- validity unknown.

Git deletion alone must never produce a revoked/invalid status.

### AC-2: Reproducible historical evidence

Given the same synthetic repository and configuration, M1/M2 produce stable commit SHA, path, line, detector/rule, and finding identity outputs. Deleted files and historical contents are recoverable where Git makes them reachable.

### AC-3: Safe handling

Plaintext synthetic or real credentials do not appear in MySQL, logs, API responses, frontend state, reports, or test output. Findings contain only safe metadata, salted hash/fingerprint, and last-four-character preview.

### AC-4: Evidence-backed evaluation

The synthetic ground-truth file, dataset split, test results, and baseline metrics are generated from executed tests. No metric, participant result, provider validity result, or rotation result is reported without evidence.

## Scope

### In scope for the current research sequence

- M1 complete Git-history extraction.
- M2 Gitleaks subprocess integration and normalized JSON findings.
- M3 modular provider/category classification.
- M4 repository, commit, file, branch, HEAD/history context.
- Synthetic ground truth, leakage-safe evaluation, and baseline metrics.
- MySQL persistence of safe metadata.
- Existing SHD React/FastAPI interface connected to real evidence.

### Explicitly out of scope until later phases

- O3 provider validity verification before M2/M3 are stable.
- O3 explainable risk scoring before validity/context inputs are available.
- O4 scheduling, rotation confirmation, and MTTR before verification history exists.
- Mutating provider API calls, automatic revocation, or automatic secret rotation.
- Production authentication/authorization claims for the current localhost demo.

## O1 decision

O1 is **not complete yet**. The charter, threat model, trust boundary, scope, and acceptance criteria are now documented. Survey/interview evidence and executed AC-1–AC-4 validation remain pending. The existing technical scanner implementation is recorded as M1/M2-era work, not O1 completion.
