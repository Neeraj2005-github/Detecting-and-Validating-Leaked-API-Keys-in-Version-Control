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
