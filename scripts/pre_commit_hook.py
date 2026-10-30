"""Block commits containing likely active secrets in staged additions."""

from __future__ import annotations

import subprocess
import sys

from backend.ml.detector import detect_lines


def staged_lines() -> list[dict[str, object]]:
    result = subprocess.run(["git", "diff", "--cached", "--unified=0", "--diff-filter=AM"], capture_output=True, text=True, check=True)
    current_file, line_number, lines = "", 1, []
    for raw in result.stdout.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
        elif raw.startswith("@@"):
            line_number = int(raw.split("+", 1)[1].split(",", 1)[0].split()[0])
        elif raw.startswith("+") and not raw.startswith("+++"):
            lines.append({"commit_sha": "staged", "file_path": current_file, "line_number": line_number, "added_line": raw[1:], "still_in_head": True, "git_lifecycle_state": "ACTIVE_HEAD"})
            line_number += 1
    return lines


def main() -> int:
    active = [item for item in detect_lines(staged_lines()) if not item.is_false_positive]
    if active:
        print(f"Commit blocked: {len(active)} likely active secret(s) detected.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
