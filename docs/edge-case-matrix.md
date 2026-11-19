# Edge-case matrix

| Case | Status | Evidence |
|---|---|---|
| Secret added then deleted | Tested | `test_o1_reproduction_verifies_history_and_head_absence` |
| Deleted branch | Not tested | None |
| Tag | Not tested | None |
| Merge commit | Not tested | None |
| Renamed file | Not tested | None |
| Force-push/squash | Not tested | None |
| Stash | Not tested | None |
| Shallow clone | Partial — refusal test planned | `test_nt2_shallow_repository_must_be_refused` |
| Empty repo | Tested | `test_ec1_empty_repository` |
| Large repo | Partial | `test_ec2_ten_mb_single_line` |
| Corrupt object | Not tested | None |
| Submodule | Not tested | None |
| LFS pointer | Not tested | None |
| Binary file | Tested | `test_ec3_binary_file` |
| Very long minified line | Tested | `test_ec2_ten_mb_single_line` |
| Base64/URL encoded | Partial | O2 fixture |
| Multi-line PEM | Not tested | None |
| Split secret | Not tested | None |
| Comment/JSON/YAML/.env | Partial | walker and source scanner fixtures |
| False positives: example keys/UUID/hash/lockfile | Tested | matcher and O2 decoy tests |
| Same secret in 100 commits | Not tested | 3-commit dedupe test only |
| Symlink | Not tested | None |
| Path traversal | Not tested | None |
| Malicious git hook | Not tested | Hook isolation not implemented |
| Zip bomb | Not tested | None |
| ReDoS | Not tested | No per-file timeout |
| Timeout | Not tested | Runner timeout exists but no timeout test |
| No read permission | Not tested | None |
| Bad config | Partial | owned-config rejection test |
| Disk full | Not tested | None |
