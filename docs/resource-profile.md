# Resource profile

Measurements use the native Gitleaks child process, not the Python parent.
Wall, CPU, and peak RSS are collected for the same subprocess PID.

## Native Gitleaks 8.18.4 measurements

Measured in five direct child-process runs on Windows 11.

| Commits | Repo size | Wall median (min-max) | CPU median (min-max) | Peak RSS median (min-max) |
|---:|---:|---|---|---|
| 100 | 89,041 bytes | 0.741 s (0.581-0.826 s) | 0.21875 s (0.15625-0.265625 s) | 20.676 MB (19.332-20.957 MB) |
| 1,000 | 654,820 bytes | 1.800 s (1.590-3.246 s) | 0.375 s (0.28125-0.828125 s) | 22.500 MB (21.863-23.047 MB) |
| 10,000 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED |

The 10,000 repository was not completed; generation stopped at 4,533 commits, so no 10k measurement is claimed. Machine-specific metadata is recorded in `artifacts/resource_profile.json`.
