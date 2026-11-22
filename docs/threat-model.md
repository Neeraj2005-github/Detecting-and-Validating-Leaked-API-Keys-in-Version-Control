# Scanner threat model

| Threat | Control | Test |
|---|---|---|
| Malicious repository content | Bounded source validation and safe text handling | `test_scan_rejects_non_git_directory_with_actionable_error` |
| Malicious hooks | Repository hooks are disabled by core.hooksPath and source clone isolation | `test_hook_marker_never_created` |
| Symlink/path traversal | Resolve repository root; no arbitrary extraction | `test_symlink_outside_repo_is_skipped`, `test_path_traversal_filename_is_not_resolved_outside` |
| Zip/decompression bomb | No repository archive extraction in scanner | `test_zip_archive_is_not_extracted_and_large_file_is_skipped` |
| ReDoS | Bounded patterns and per-file timeout | `test_redos_style_long_line_is_skipped` |
| Raw report exfiltration | Private temp report and sanitized errors | `test_normalizer_hashes_secrets_and_strips_plaintext` |
| Config injection | Owned absolute config plus hash lock | `test_runner_requires_owned_config` |
