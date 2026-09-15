from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable

from .dataset import DatasetEntry
from .models import DedupedFinding, RawFinding


def normalize_secret(matched_string: str) -> str:
    """Normalize only surrounding whitespace; secret casing remains significant."""
    return matched_string.strip()


def compute_secret_id(matched_string: str) -> str:
    return hashlib.sha256(normalize_secret(matched_string).encode("utf-8")).hexdigest()


def deduplicate(
    raw_findings: list[RawFinding],
    dataset_entries: Iterable[DatasetEntry] = (),
) -> list[DedupedFinding]:
    groups: dict[str, list[RawFinding]] = defaultdict(list)
    for finding in raw_findings:
        groups[compute_secret_id(finding.matched_string)].append(finding)

    manifest_matches = [
        (entry, planted)
        for entry in dataset_entries
        for planted in entry.planted_secrets
    ]
    results: list[DedupedFinding] = []
    for secret_id, findings in sorted(groups.items()):
        ordered = sorted(
            findings,
            key=lambda finding: (
                finding.commit_timestamp is None,
                finding.commit_timestamp,
                finding.commit_hash,
            ),
        )
        first = ordered[0]
        matching_entries = [
            (entry, planted)
            for entry, planted in manifest_matches
            if any(
                finding.commit_hash == planted.commit_hash
                and finding.file_path == planted.file_path
                and finding.secret_type == planted.secret_type
                for finding in findings
            )
        ]
        results.append(
            DedupedFinding(
                secret_id=secret_id,
                secret_type=first.secret_type,
                commit_hashes=sorted({finding.commit_hash for finding in findings}),
                first_seen_commit=first.commit_hash,
                present_in_head=any(finding.is_head for finding in findings),
                label_ground_truth=bool(matching_entries),
                dataset_split=matching_entries[0][0].split if matching_entries else "reference",
            ),
        )
    return results