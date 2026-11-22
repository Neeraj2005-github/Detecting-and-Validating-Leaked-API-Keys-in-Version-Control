# Edge-case matrix

| Case | Status | Evidence |
|---|---|---|
| Secret added then deleted | Tested | `test_o1_reproduction_verifies_history_and_head_absence` |
| Deleted branch | Tested | `test_deleted_branch_commit_is_out_of_reachable_history` |
| Tag | Tested | `test_tagged_commit_is_visible_in_full_history` |
| Merge commit | Tested | `test_merge_commit_is_visible_with_two_parents` |
| Renamed file | Tested | `test_renamed_file_history_is_visible` |
| Force-push/squash | Tested | `test_force_push_dropped_commit_is_unreachable` |
| Stash | Tested | `test_stash_commit_is_not_a_normal_branch_tip` |
| Shallow clone | Partial — refusal test planned | `test_nt2_shallow_repository_must_be_refused` |
| Empty repo | Tested | `test_ec1_empty_repository` |
| Large repo | Partial | `test_ec2_ten_mb_single_line` |
| Corrupt object | Not tested | None |
| Submodule | Not tested | None |
| LFS pointer | Not tested | None |
| Binary file | Tested | `test_ec3_binary_file` |
| Very long minified line | Tested | `test_ec2_ten_mb_single_line` |
| Base64/URL encoded | Tested | `test_encoded_fake_values_do_not_leak_plaintext` |
| Multi-line PEM | Tested | `test_pem_fixture_is_masked` |
| Split secret | Tested | `test_split_fake_secret_is_not_reconstructed` |
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
