# URL ingestion test evidence

The local test-only flags `allow_loopback_test` and `allow_http_test` are
disabled by default. They allow an isolated test HTTP server to exercise loopback
redirect behavior only.

Measured cases:

- Loopback to `10.0.0.10`: rejected after following an isolated local redirect.
- Clone timeout: rejected with `Repository clone timed out`.
- Oversize clone: rejected with `Repository exceeds the configured size limit`.
- The private token is absent from the clone argv and is supplied through
  `GIT_ASKPASS` and the `SHD_GIT_TOKEN` environment variable.
- DNS rebinding: a controlled resolver changes its answer after validation;
  the redirect probe connects only to the initially validated loopback address.
- Git clone pins the validated DNS answers using libcurl's resolve option.

## Scan subprocess controls

The Gitleaks child receives a minimal environment, an absolute owned config
path, a 60-second timeout, and a 512 MiB process-memory limit. Windows uses a
Job Object with kill-on-close; Linux applies `RLIMIT_DATA`. The
focused runner test hashes the target tree before and after the scan and patches
Python socket connections to assert that the wrapper process makes no outbound
connection during scanning.

Child-process network isolation is **NOT MEASURED locally**. CI is configured
to verify it on `ubuntu-latest` with a container `--network none` probe; this
is considered verified only after that GitHub Actions job passes.
