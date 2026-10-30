# Project Overview

## Purpose

This project detects credential-shaped values in current source and historical
Git content, suppresses likely decoys, explains prioritization, and exercises
offline remediation. It is a local research/demo system rather than a
production credential-management service.

## Core problem

A credential deleted from the working tree may remain recoverable in Git
history. The system therefore scans added lines across reachable history and
labels lifecycle context instead of treating current-source matches as the
whole problem.

## Main implementation areas

- [`src/shd/`](../src/shd/) — FastAPI, SQLAlchemy persistence, core repository
  walker, current-source scanner, and API models.
- [`backend/`](../backend/) — CP1/O2 history walker, detection normalization,
  ML/SHAP, benchmarks, fixtures, and rotation services.
- [`frontend/`](../frontend/) — React/Vite workbench.
- [`tests/`](../tests/) — unit and integration coverage.
- [`artifacts/`](../artifacts/) and [`reports/`](../reports/) — generated
  evidence and evaluation outputs.

## Trust boundary

The target repository is untrusted input. The intended controls are bounded
scanning, no repository hook execution, masking/hash boundaries, local
synthetic rotation, and explicit error reporting.
