# Scanner threat model

| Threat | Control | Test |
|---|---|---|
| Malicious repository content | Bounded source validation and safe text handling | `test_scan_rejects_non_git_directory_with_actionable_error` |
| Malicious hooks | Repository hooks are not trusted for scanning | Hook isolation to be implemented |
| Symlink/path traversal | Resolve repository root; no arbitrary extraction | Not tested |
| Zip/decompression bomb | No repository archive extraction in scanner | Not tested |
| ReDoS | Bounded patterns and per-file timeout | Not tested |
| Raw report exfiltration | Private temp report and sanitized errors | `test_normalizer_hashes_secrets_and_strips_plaintext` |
| Config injection | Owned absolute config plus hash lock | `test_runner_requires_owned_config` |
