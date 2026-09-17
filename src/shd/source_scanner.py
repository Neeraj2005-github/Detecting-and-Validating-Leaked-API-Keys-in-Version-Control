from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import git

from .matcher import match
from .models import BlobRecord, SourceFinding

SUPPORTED_EXTENSIONS = {
    ".c", ".conf", ".config", ".cpp", ".go", ".ini", ".java", ".js",
    ".json", ".jsx", ".pem", ".properties", ".py", ".sh", ".ts", ".tsx",
    ".txt", ".xml", ".yaml", ".yml",
}
SUPPORTED_FILENAMES = {".env", ".env.local", ".env.production", "Dockerfile"}
SKIPPED_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", "build", "dist"}


@dataclass(frozen=True)
class SourceScanResult:
    findings: list[SourceFinding]
    files_discovered: int
    files_scanned: int
    files_skipped: int


def _is_supported(path: Path) -> bool:
    return path.name in SUPPORTED_FILENAMES or path.suffix.lower() in SUPPORTED_EXTENSIONS


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def _mask(value: str) -> str:
    value = value.strip()
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


def scan_source(repo_path: str) -> SourceScanResult:
    if repo_path.startswith(("http://", "https://", "git://", "git@", "ssh://")):
        with tempfile.TemporaryDirectory(prefix="shd_source_clone_") as temporary_path:
            git.Repo.clone_from(repo_path, temporary_path)
            return _scan_local_source(temporary_path)
    return _scan_local_source(repo_path)


def _scan_local_source(repo_path: str) -> SourceScanResult:
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("repository path must be an existing directory")
    if not (root / ".git").exists():
        raise ValueError("repository path must contain a .git directory")

    findings: list[SourceFinding] = []
    files_discovered = files_scanned = files_skipped = 0
    for current_root, directories, filenames in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in SKIPPED_DIRECTORIES)
        for filename in sorted(filenames):
            path = Path(current_root) / filename
            files_discovered += 1
            if not _is_supported(path):
                files_skipped += 1
                continue
            try:
                data = path.read_bytes()
                if _is_binary(data):
                    files_skipped += 1
                    continue
                content = data.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                files_skipped += 1
                continue

            files_scanned += 1
            relative_path = path.relative_to(root).as_posix()
            blob = BlobRecord(
                commit_hash="working-tree",
                commit_timestamp=None,
                file_path=relative_path,
                blob_content=content,
                is_head=True,
            )
            for raw in match(blob):
                findings.append(
                    SourceFinding(
                        finding_id=hashlib.sha256(
                            f"{relative_path}:{raw.line_number}:{raw.secret_type}:{raw.matched_string}".encode("utf-8")
                        ).hexdigest(),
                        repository_path=str(root),
                        file_path=relative_path,
                        line_number=raw.line_number,
                        secret_type=raw.secret_type,
                        detector=raw.detector_source,
                        confidence=raw.detector_confidence,
                        secret_hash=_fingerprint(raw.matched_string),
                        masked_preview=_mask(raw.matched_string),
                        status="open",
                    )
                )

    return SourceScanResult(
        findings=findings,
        files_discovered=files_discovered,
        files_scanned=files_scanned,
        files_skipped=files_skipped,
    )
