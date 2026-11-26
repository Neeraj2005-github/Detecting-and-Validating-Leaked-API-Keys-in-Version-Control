# Resource profile

Measurements use the native Gitleaks child process, not the Python parent.
Wall, CPU, and peak RSS are collected for the same subprocess PID.

## Native Gitleaks 8.18.4 measurements

Measured in five direct child-process runs on Windows 11.

| Commits | Repo size | Wall median (min-max) | CPU median (min-max) | Peak RSS median (min-max) |
|---:|---:|---|---|---|
| 100 | 89,041 bytes | 0.741 s (0.581-0.826 s) | 0.21875 s (0.15625-0.265625 s) | 20.676 MB (19.332-20.957 MB) |
| 1,000 | 654,820 bytes | 1.800 s (1.590-3.246 s) | 0.375 s (0.28125-0.828125 s) | 22.500 MB (21.863-23.047 MB) |
| 10,000 | 1,853,654 bytes | 0.2863 s (0.2759-0.2887 s) | 0.203125 s (0.125-0.296875 s) | 25.555 MB (25.109-27.875 MB) |

The 10,000-commit table row summarizes five new direct-child runs against the
same fast-import fixture (10,000 commit objects, 9,998 reachable), each with a
600-second timeout. The original one-run result remains sample 1 in the JSON
artifact: wall 1.5437 s, CPU 0.40625 s, peak RSS 28.293 MB, and repository size
2,028,963 bytes. That first sample used a different-size fixture and is retained
but excluded from the five-run summary. Machine-specific metadata and all six
samples are recorded in
[`artifacts/resource_profile_10000.json`](../artifacts/resource_profile_10000.json).
The older `artifacts/resource_profile.json` entry still records the earlier
incomplete generated repository; it is not the source of the 10,000-commit
measurement above.
