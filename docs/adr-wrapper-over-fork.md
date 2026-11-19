# ADR: Wrap Gitleaks without forking

## Status

Accepted for CP1.

## Decision

SecretGuard uses the official Gitleaks executable as an unmodified O2 reference and adds detection orchestration, parsing, masking, HMAC dedupe, lifecycle, reporting, and audit code in this repository.

## Alternatives considered

- Fork Gitleaks: rejected because it would alter the black-box reference, licence/attribution burden, and update cost.
- Replace Gitleaks: rejected because native Gitleaks remains the comparison reference.
- Reimplement Gitleaks rules: rejected because it would not provide an independent baseline.

## Consequences

Gitleaks upgrades require checksum, schema, and benchmark review. SecretGuard owns and locks only its wrapper configuration and never trusts repository-local Gitleaks configuration.
