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

The coverage manifest reports skipped file and line counts by reason. Exit code 2 is returned when commit coverage mismatches or when skipped file plus skipped line count exceeds `SHD_SKIPPED_THRESHOLD` or `--skipped-threshold`.
