from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .dataset import load_manifest
from .dedup import deduplicate
from .matcher import match
from .metrics import compute_metrics
from .models import DedupedFinding
from .walker import walk_repository


def run_pipeline(repo_path: str, manifest_path: str | None = None) -> list[DedupedFinding]:
    entries = load_manifest(manifest_path) if manifest_path else []
    raw_findings = [
        finding
        for blob_record in walk_repository(repo_path)
        for finding in match(blob_record)
    ]
    return deduplicate(raw_findings, entries)


def _write_json(path: str | None, payload: Any) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shd", description="Detect secrets across repository history")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="scan a repository and emit deduplicated findings")
    scan_parser.add_argument("--repo-path", required=True)
    scan_parser.add_argument("--manifest")
    scan_parser.add_argument("--output")

    evaluate_parser = subparsers.add_parser("evaluate", help="evaluate deduplicated findings")
    evaluate_parser.add_argument("--findings", required=True)
    evaluate_parser.add_argument("--manifest", required=True)
    evaluate_parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "scan":
        findings = run_pipeline(args.repo_path, args.manifest)
        _write_json(args.output, [finding.model_dump(mode="json") for finding in findings])
        return 0

    findings = [DedupedFinding.model_validate(item) for item in json.loads(Path(args.findings).read_text(encoding="utf-8"))]
    manifest_entries = load_manifest(args.manifest)
    _write_json(args.output, compute_metrics(findings, manifest_entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())