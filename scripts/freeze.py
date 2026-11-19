import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
