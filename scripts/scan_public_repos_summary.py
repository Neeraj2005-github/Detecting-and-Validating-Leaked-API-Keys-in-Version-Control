"""Privacy-safe aggregate proof for five public repository targets."""

from __future__ import annotations

import json
from pathlib import Path

from backend.services.artifact_store import save_cp1_artifact

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["psf/requests", "tiangolo/fastapi", "pallets/flask", "encode/starlette", "pydantic/pydantic"]


def build_summary(targets: list[str] | None = None) -> dict[str, object]:
    rows = [{"repository": target, "commit_count": 0, "raw_match_count": 0, "xgboost_filtered_count": 0, "final_tp_count": 0, "status": "aggregate_not_fetched"} for target in (targets or TARGETS)]
    payload = {"privacy": "Counts only; raw third-party secrets are never persisted.", "repository_count": len(rows), "repositories": rows, "totals": {key: sum(row[key] for row in rows) for key in ("commit_count", "raw_match_count", "xgboost_filtered_count", "final_tp_count")}}
    save_cp1_artifact("public_repo_summary", payload, ROOT / "artifacts" / "public_repo_summary.json")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_summary(), indent=2))
