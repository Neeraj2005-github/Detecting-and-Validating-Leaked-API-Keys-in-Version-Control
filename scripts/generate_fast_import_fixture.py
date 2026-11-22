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
    fake_secret = "AKIAIOSFODNN7EXAMPLE"
    stream = bytearray()
    stream.extend(b"reset refs/heads/main\n")
    for index in range(1, count + 1):
        stream.extend(b"commit refs/heads/main\n")
        stream.extend(f"mark :{index}\n".encode("ascii"))
        stream.extend(b"author Fixture <fixture@example.test> 1704067200 +0000\n")
        stream.extend(b"committer Fixture <fixture@example.test> 1704067200 +0000\n")
        message = f"Benchmark fixture commit {index}\n"
        stream.extend(f"data {len(message.encode('utf-8'))}\n".encode("ascii"))
        stream.extend(message.encode("utf-8"))
        if index == 1:
            config = f"AWS_ACCESS_KEY_ID={fake_secret}\n"
            stream.extend(b"M 100644 inline config.env\n")
            stream.extend(f"data {len(config.encode('utf-8'))}\n".encode("ascii"))
            stream.extend(config.encode("utf-8"))
            readme = "# FAKE benchmark fixture\nClean documentation example: EXAMPLE_ONLY\n"
            stream.extend(b"M 100644 inline README.md\n")
            stream.extend(f"data {len(readme.encode('utf-8'))}\n".encode("ascii"))
            stream.extend(readme.encode("utf-8"))
        elif index == 2:
            stream.extend(b"D config.env\n")
        elif index % 10 == 0:
            evidence = f"clean_negative_{index}=NOT_A_SECRET\n"
            stream.extend(b"M 100644 inline evidence.txt\n")
            stream.extend(f"data {len(evidence.encode('utf-8'))}\n".encode("ascii"))
            stream.extend(evidence.encode("utf-8"))
    stream.extend(b"tag v1-FAKE\n")
    stream.extend(f"from :{count}\n".encode("ascii"))
    stream.extend(b"tagger Fixture <fixture@example.test> 1704067200 +0000\n")
    tag_message = "Synthetic benchmark tag\n"
    stream.extend(f"data {len(tag_message.encode('utf-8'))}\n".encode("ascii"))
    stream.extend(tag_message.encode("utf-8"))
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
