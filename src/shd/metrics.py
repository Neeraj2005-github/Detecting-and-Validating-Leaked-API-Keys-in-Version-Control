from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .dataset import DatasetEntry
from .models import DedupedFinding


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _measure(findings: Sequence[DedupedFinding], planted_count: int) -> dict[str, float | int]:
    true_positive = sum(finding.label_ground_truth for finding in findings)
    false_positive = len(findings) - true_positive
    false_negative = max(planted_count - true_positive, 0)
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall)
    # TN is undefined for an unbounded non-secret population. This is the
    # finite-candidate false-positive rate used by this project.
    fpr = _ratio(false_positive, true_positive + false_positive)
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
    }


def _manifest_counts(manifest: Any) -> Counter[str]:
    if isinstance(manifest, Mapping):
        if "repos" in manifest:
            manifest = manifest["repos"]
        elif "total_planted_secrets" in manifest:
            return Counter({"__overall__": int(manifest["total_planted_secrets"])})
        elif "eval" in manifest and isinstance(manifest["eval"], Mapping):
            return Counter({"__overall__": int(manifest["eval"].get("total_planted_secrets", 0))})

    entries = list(manifest or [])
    counts: Counter[str] = Counter()
    for entry in entries:
        if isinstance(entry, DatasetEntry):
            secrets = entry.planted_secrets
        else:
            secrets = entry.get("planted_secrets", [])
        for secret in secrets:
            secret_type = secret.secret_type if hasattr(secret, "secret_type") else secret["secret_type"]
            counts[secret_type] += 1
    return counts


def compute_metrics(
    deduped_findings: list[DedupedFinding],
    manifest: Any,
) -> dict[str, Any]:
    """Compute overall and per-secret-type metrics from deduped output.

    FPR is defined as FP / (TP + FP), the false-positive share of emitted
    findings, because true negatives are not enumerable in secret scanning.
    """
    counts = _manifest_counts(manifest)
    overall_planted = counts.get("__overall__", sum(counts.values()))
    by_type: dict[str, list[DedupedFinding]] = {}
    for finding in deduped_findings:
        by_type.setdefault(finding.secret_type, []).append(finding)

    type_names = sorted(set(counts) - {"__overall__"} | set(by_type))
    return {
        "overall": _measure(deduped_findings, overall_planted),
        "per_type": {
            secret_type: _measure(
                by_type.get(secret_type, []),
                counts.get(secret_type, 0),
            )
            for secret_type in type_names
        },
        "fpr_definition": "false_positive / (true_positive + false_positive)",
    }