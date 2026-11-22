# Known scanner limitations

## Archives

ZIP, TAR, compressed archives, and similar package formats are not recursively extracted. Archive contents are reported as skipped archive files. This prevents decompression and zip-bomb exposure but may miss secrets stored inside an archive.

## Submodules

Submodule entries in `.gitmodules` are recorded but submodule repositories are not recursively cloned or scanned. A submodule is a known blind spot until its repository is supplied as a separate scan target.

## Git LFS

Git LFS pointer files are recognized and skipped; pointer text is not assumed to contain the referenced object. LFS object storage is not downloaded or scanned unless explicitly mounted and authorized.

## Encoded and split credentials

Base64 and URL-encoded values are not reconstructed or decoded unless a native Gitleaks rule matches the exact text. PEM blocks and credentials split across lines or variables are measured as known misses and must not be reported as complete coverage.

## Coverage impact

The coverage manifest reports skipped file and line counts by reason. Exit code
2 is returned when skipped file plus skipped line count exceeds
`SHD_SKIPPED_THRESHOLD` or `--skipped-threshold`. Shallow repositories are
refused with exit code 4.

`completeness: complete` means reachable-commit traversal passed the shallow,
count-mismatch, and configured skip-threshold checks. It does not mean every
file was inspected: each skipped path and reason remains in the manifest and
must be reviewed.

## Lifecycle performance

Lifecycle analysis uses path-specific history queries. A measured synthetic
100-commit case with one finding in each of 100 distinct paths exceeded the
30-second parse-stage timeout. The repeated-secret case with one path completed
in 1.225 seconds and deduplicated 100 native matches to one wrapper finding.
High finding counts across many distinct paths remain a performance gap; the
timeout returns a stage and reason rather than waiting indefinitely.

The reported 10- and 1,000-commit scan timings used generated repositories
without findings. They do not establish the same timing for repositories with
many distinct findings.

## Provider verification

The local rotation state machine verifies only the mock service. The scanner
does not validate credentials with cloud providers and cannot prove an
external credential has been revoked. Provider-side verification remains
outside the implemented scope.
