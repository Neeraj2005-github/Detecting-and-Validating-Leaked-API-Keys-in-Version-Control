import json
from pathlib import Path


def main() -> int:
    oracle = Path("artifacts/ground_truth_oracle.json")
    if not oracle.exists():
        print("Oracle artifact missing")
        return 2
    payload = json.loads(oracle.read_text(encoding="utf-8"))
    if not isinstance(payload.get("entries"), list):
        print("Oracle entries missing")
        return 3
    print(f"Oracle entries: {len(payload['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
