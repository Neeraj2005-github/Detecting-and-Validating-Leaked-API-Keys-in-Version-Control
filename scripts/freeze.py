import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CRITERIA = {
    "KPI-1-detection-recall": {"anchor": "recall on the holdout oracle", "0": 0, "50": 50, "80": 80, "100": 100},
    "KPI-1-detection-precision": {"anchor": "precision on the holdout oracle", "0": 0, "50": 50, "80": 80, "100": 100},
    "KPI-1-fixture-coverage": {"anchor": "required edge cases present", "0": 0, "50": 50, "80": 80, "100": 100},
    "KPI-1-determinism": {"anchor": "normalized report hashes match", "0": 0, "50": 50, "80": 80, "100": 100},
    "KPI-1-supply-chain": {"anchor": "versions, checksums, and lockfiles recorded", "0": 0, "50": 50, "80": 80, "100": 100},
}

HOLDOUT = [
    "fixtures/deleted-branch",
    "fixtures/force-push-dropped",
    "fixtures/merge",
    "fixtures/rename",
    "fixtures/tag",
    "fixtures/split-secret",
    "fixtures/pem",
    "fixtures/base64",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm:
        print("Refusing to freeze without --confirm")
        return 2
    roots = [ROOT / "fixtures", ROOT / "testdata", ROOT / "gitleaks.toml", ROOT / "config.lock"]
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "criteria": CRITERIA,
        "holdout": HOLDOUT,
        "files": [
            {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(path)}
            if path.is_file() else {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": "directory"}
            for path in roots
        ],
    }
    target = ROOT / "docs" / "freeze-v1.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "tag", "holdout-v1"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
