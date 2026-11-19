import ast
import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = [f"FR-{index}" for index in range(1, 8)] + [f"NFR-{index}" for index in range(1, 7)]


def main() -> int:
    covered: dict[str, list[str]] = {item: [] for item in REQUIREMENTS}
    for path in (ROOT / "tests").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        marked = set(re.findall(r'req\(["\'](FR-[1-7]|NFR-[1-6])["\']\)', text))
        tree = ast.parse(text, filename=str(path))
        function_names = [
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]
        for requirement in marked:
            covered[requirement].extend(
                f"{path.relative_to(ROOT).as_posix()}::{name}" for name in function_names
            )
    output = {
        "generated": date.today().isoformat(),
        "requirements": [
            {"id": requirement, "tests": covered[requirement] or ["none"]}
            for requirement in REQUIREMENTS
        ],
    }
    target = ROOT / "docs" / "traceability-generated.json"
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
