from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("size", choices=("100", "1000", "10000"), type=str)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--initial-branch=main", str(output)], check=True, capture_output=True)

    count = int(args.size)
    stream = bytearray()
    stream.extend(b"reset refs/heads/main\n")
    stream.extend(b"commit refs/heads/main\n")
    stream.extend(b"mark :1\n")
    stream.extend(b"author Fixture <fixture@example.test> 1704067200 +0000\n")
    stream.extend(b"committer Fixture <fixture@example.test> 1704067200 +0000\n")
    stream.extend(b"data 31\nAdd benchmark fixture commit 1\n")
    stream.extend(b"M 100644 inline README.md\n")
    stream.extend(b"data 58\n")
    stream.extend(b"# FAKE benchmark fixture\nClean documentation example: EXAMPLE_ONLY\n")
    for index in range(1, count):
        stream.extend(f"commit refs/heads/main\nmark :{index + 1}\n".encode("ascii"))
        stream.extend(b"author Fixture <fixture@example.test> 1704067200 +0000\n")
        stream.extend(b"committer Fixture <fixture@example.test> 1704067200 +0000\n")
        stream.extend(f"data {len(f'Benchmark commit {index + 1}')}\n".encode("ascii"))
        stream.extend(f"Benchmark commit {index + 1}\n".encode("ascii"))
        stream.extend(b"M 100644 inline README.md\n")
        stream.extend(f"data {18 + len(str(index))}\n".encode("ascii"))
        stream.extend(f"Commit {index + 1} FAKE\n".encode("ascii"))
    subprocess.run(
        ["git", "fast-import", "--quiet"],
        cwd=output,
        input=stream,
        check=True,
        capture_output=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
