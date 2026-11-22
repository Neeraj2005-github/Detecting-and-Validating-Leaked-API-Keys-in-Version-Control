from __future__ import annotations

import argparse
import json
import html
import hashlib
import hmac
import os
import shutil
import subprocess
import secrets
import tempfile
from pathlib import Path
from typing import Any

from .dataset import load_manifest
from .dedup import deduplicate
from .matcher import match
from .metrics import compute_metrics
from .models import DedupedFinding
from .walker import walk_repository
from backend.detection.gitleaks_runner import run_gitleaks
from backend.detection.normalizer import normalize
from backend.services.coverage import build_coverage
from backend.services.repository_ingestion import clone_https_repository


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


def _render_report(report: dict[str, Any], report_format: str) -> str:
    if report_format == "json":
        return json.dumps(report, indent=2, sort_keys=True) + "\n"
    if report_format == "sarif":
        results = []
        for finding in report["findings"]:
            results.append({
                "ruleId": finding["rule_id"],
                "level": "error",
                "message": {"text": f"Secret detected; masked preview: {finding['masked_preview']}"},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding["file"]},
                        "region": {"startLine": finding["line"]},
                    }
                }],
                "properties": {
                    "commit": finding["commit"],
                    "secret_hash": finding["secret_hash"],
                    "lifecycle_status": report["lifecycle_status"],
                },
            })
        payload = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"name": "SecretGuard SHD", "version": "1.0"}},
                "results": results,
                "properties": {"coverage": report["coverage"]},
            }],
        }
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    rows = []
    for finding in report["findings"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(finding['rule_id'])}</td>"
            f"<td>{html.escape(finding['file'])}</td>"
            f"<td>{finding['line']}</td>"
            f"<td>{html.escape(finding['masked_preview'])}</td>"
            f"<td>{html.escape(finding['commit'])}</td>"
            "</tr>"
        )
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>SHD scan report</title></head>"
        "<body><h1>SHD scan report</h1>"
        f"<p>{html.escape(report['coverage']['human_summary'])}</p>"
        f"<p>Lifecycle: {html.escape(report['lifecycle_status'])}</p>"
        "<table border=\"1\"><thead><tr><th>Rule</th><th>File</th><th>Line</th><th>Masked</th><th>Commit</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></body></html>\n"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shd", description="Detect secrets across repository history")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="scan a local path or https repository URL")
    scan_parser.add_argument("target", help="local repository path or https:// repository URL")
    scan_parser.add_argument("--format", choices=("json", "sarif", "html"), default="json")
    scan_parser.add_argument("--out", help="write the report to this path")
    scan_parser.add_argument("--fail-on-findings", action="store_true")
    scan_parser.add_argument("--skipped-threshold", type=int, default=None)
    scan_parser.add_argument("--manifest")
    scan_parser.add_argument("--output")
    scan_parser.add_argument("--repo-path", dest="legacy_repo_path", help=argparse.SUPPRESS)

    evaluate_parser = subparsers.add_parser("evaluate", help="evaluate deduplicated findings")
    evaluate_parser.add_argument("--findings", required=True)
    evaluate_parser.add_argument("--manifest", required=True)
    evaluate_parser.add_argument("--output")
    audit_parser = subparsers.add_parser("verify-audit", help="verify a hash-chained audit log")
    audit_parser.add_argument("--audit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "scan":
        target = args.target if hasattr(args, "target") else args.legacy_repo_path
        if not target:
            return 4
        temporary_repo = None
        temporary_wrapper = None
        repo_path: str
        repo = None
        try:
            import git
            if target.lower().startswith("https://"):
                repo, temporary_wrapper, scan_path = clone_https_repository(
                    target,
                )
                temporary_repo = scan_path
                repo_path = str(scan_path)
            else:
                for forbidden in ("file://", "ssh://", "ext::", "git://"):
                    if target.lower().startswith(forbidden):
                        return 4
                local = Path(target).expanduser().resolve()
                repo = git.Repo(str(local), search_parent_directories=False)
                repo_path = str(local)

            if repo.git.rev_parse("--is-shallow-repository").strip() == "true":
                print("invalid target: shallow repositories are not accepted")
                return 4

            coverage = build_coverage(
                repo_path,
                skipped_threshold=args.skipped_threshold,
            )
            commits_scanned = coverage["commits_reachable"]
            raw_findings = run_gitleaks(repo_path)
            if not os.environ.get("SHD_HMAC_KEY"):
                os.environ["SHD_HMAC_KEY"] = secrets.token_hex(32)
            normalized = normalize(raw_findings)
            redacted_findings = [
                {
                    "commit": finding.commit_sha,
                    "file": finding.file,
                    "line": finding.line,
                    "rule_id": finding.rule_id,
                    "secret_hash": finding.matched_string_hash,
                    "masked_preview": finding.masked_preview,
                }
                for finding in normalized
            ]

            report = {
                "coverage": coverage,
                "findings": redacted_findings,
                "lifecycle_status": "DETECTED" if redacted_findings else "VALIDITY_UNKNOWN",
                "exit_code_meaning": {
                    "0": "no findings and skips below threshold",
                    "1": "findings present",
                    "2": "skipped-item threshold exceeded",
                    "3": "scan runtime error",
                    "4": "invalid target",
                },
            }
            text = _render_report(report, args.format)
            if args.out:
                Path(args.out).write_text(text, encoding="utf-8")
            else:
                print(text, end="" if text.endswith("\n") else "\n")

            skipped_exceeded = bool(coverage["skipped_threshold_exceeded"])
            summary = (
                f"commits={commits_scanned} "
                f"branches={coverage['refs']['branch_count']} "
                f"tags={coverage['refs']['tag_count']} "
                f"findings={len(redacted_findings)} "
                f"lifecycle={report['lifecycle_status']} "
                f"exit-code=0 clean, 1 findings, 2 skipped, 3 runtime, 4 invalid"
            )
            print(summary)

            if skipped_exceeded:
                return 2
            if redacted_findings and args.fail_on_findings:
                return 1
            return 0
        except (ValueError, OSError, git.InvalidGitRepositoryError):
            return 4
        except Exception:
            return 3
        finally:
            if repo is not None:
                repo.close()
            if temporary_wrapper is not None:
                temporary_wrapper.cleanup()

    if args.command == "verify-audit":
        from backend.services.audit_log import verify_chain
        return 0 if verify_chain(args.audit) else 3

    findings = [DedupedFinding.model_validate(item) for item in json.loads(Path(args.findings).read_text(encoding="utf-8"))]
    manifest_entries = load_manifest(args.manifest)
    _write_json(args.output, compute_metrics(findings, manifest_entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())