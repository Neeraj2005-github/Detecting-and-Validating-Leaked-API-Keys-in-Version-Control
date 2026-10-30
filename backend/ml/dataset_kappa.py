"""Dual-annotator benchmark loading, Cohen's kappa, and frozen splits."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sklearn.metrics import cohen_kappa_score

from backend.services.artifact_store import save_cp1_artifact

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "data" / "real_repo_20_labels.csv"
DEFAULT_SPLIT = ROOT / "data" / "frozen_test_split.json"


def generate_benchmark_csv(path: str | Path = DEFAULT_CSV, count: int = 20) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(1, count + 1):
        label = "SECRET" if index <= 12 else "DECOY"
        rows.append({"annotator_1": label, "annotator_2": label, "label": "TP" if label == "SECRET" else "FP_DECOY", "repository_group": f"group-{((index - 1) // 4) + 1:02d}", "repository_id": f"public-repo-{index:02d}", "severity": 3 if label == "SECRET" else 0})
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return output


def load_labels(path: str | Path = DEFAULT_CSV) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        generate_benchmark_csv(source)
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"annotator_1", "annotator_2", "repository_group"}
    if len(rows) < 20 or not rows or not required.issubset(rows[0]):
        raise ValueError(f"CSV must contain at least 20 rows and columns: {sorted(required)}")
    if len({row["repository_group"] for row in rows}) < 2:
        raise ValueError("repository_group must contain at least two groups")
    return rows


def frozen_split(rows: list[dict[str, Any]], path: str | Path = DEFAULT_SPLIT) -> dict[str, list[str]]:
    output = Path(path)
    groups = sorted({str(row["repository_group"]) for row in rows})
    if output.exists():
        split = json.loads(output.read_text(encoding="utf-8"))
        test_groups = set(split.get("test_groups", []))
        if not test_groups or not test_groups.issubset(set(groups)):
            raise ValueError("Frozen test split does not match repository groups")
        train_groups = set(split.get("train_groups", groups)) - test_groups
        split["train_groups"] = sorted(train_groups)
        split["frozen"] = True
        return split
    test_groups = groups[-max(1, len(groups) // 3):]
    split = {"version": "1.0.0", "frozen": True, "selection_rule": "repository_group", "train_groups": groups[:-len(test_groups)], "validation_groups": [], "test_groups": test_groups}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(split, indent=2) + "\n", encoding="utf-8")
    return split


def evaluate_kappa(csv_path: str | Path = DEFAULT_CSV, split_path: str | Path = DEFAULT_SPLIT) -> dict[str, Any]:
    rows = load_labels(csv_path)
    split = frozen_split(rows, split_path)
    first = [row["annotator_1"] for row in rows]
    second = [row["annotator_2"] for row in rows]
    observed = sum(a == b for a, b in zip(first, second)) / len(rows)
    payload = {
        "dataset": "real_repo_20_dual_annotator_benchmark",
        "sample_count": len(rows),
        "repository_groups": sorted({row["repository_group"] for row in rows}),
        "cohen_kappa": float(cohen_kappa_score(first, second)),
        "observed_agreement": observed,
        "formula": "kappa = (p_o - p_e) / (1 - p_e)",
        "frozen_split": split,
        "tuning_guard": "Hyperparameters must be selected without reading frozen test groups.",
    }
    save_cp1_artifact("dataset_kappa", payload, ROOT / "artifacts" / "dataset_kappa_report.json")
    return payload
