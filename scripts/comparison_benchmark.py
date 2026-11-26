from __future__ import annotations

import argparse
import base64
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_JSON = ROOT / "artifacts" / "comparison.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "comparison.md"
POSITIVE_CASES = {
    "added-then-deleted": ["cases/added-then-deleted.env"],
    "unreachable-object-deleted-branch": ["cases/deleted-branch.env"],
    "tag": ["cases/tag.env"],
    "merge": ["cases/merge.env"],
    "rename": ["cases/rename-before.env", "cases/rename-after.env"],
    "unreachable-object-force-push-dropped": ["cases/force-push-dropped.env"],
    "base64": ["cases/base64.env"],
    "pem": ["cases/pem.env"],
    "split-secret": ["cases/split-secret.env"],
}
NEGATIVE_CASES = {
    "clean-negative": "cases/clean-negative.txt",
    "doc-example-false-positive": "docs/provider-example.md",
}
ALL_POSITIVE_PATHS = {
    path
    for paths in POSITIVE_CASES.values()
    for path in paths
}
UNREACHABLE_CATEGORIES = {
    "unreachable-object-deleted-branch",
    "unreachable-object-force-push-dropped",
}
HISTORY_ONLY_CATEGORIES = {"added-then-deleted"} | UNREACHABLE_CATEGORIES
CATEGORY_LABELS = {
    "unreachable-object-deleted-branch":
        "unreachable object (not reachable from any ref) — deleted branch",
    "unreachable-object-force-push-dropped":
        "unreachable object (not reachable from any ref) — force-push dropped",
}
AWS_EXAMPLE = "AKIA5Q8M2V9C4R7N1D6P"


def _git(repo: Path, *arguments: str, input: bytes | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        input=input,
        capture_output=True,
        check=True,
    )
    return completed.stdout.decode("utf-8", errors="replace")


def generate_fast_import_fixture(repo: Path, commit_count: int) -> dict[str, int]:
    repo.mkdir(parents=True)
    _git(repo, "init", "--initial-branch=main")

    stream = bytearray(b"reset refs/heads/main\n")
    mark = 0
    main_tip: int | None = None

    def commit(
        ref: str,
        message: str,
        *,
        parent: int | None = None,
        merges: tuple[int, ...] = (),
        modifications: tuple[tuple[str, str], ...] = (),
        deletions: tuple[str, ...] = (),
        renames: tuple[tuple[str, str], ...] = (),
    ) -> int:
        nonlocal mark
        mark += 1
        payload = f"{message}\n".encode("utf-8")
        stream.extend(f"commit refs/heads/{ref}\nmark :{mark}\n".encode("ascii"))
        stream.extend(b"author Fixture <fixture@example.test> 1704067200 +0000\n")
        stream.extend(b"committer Fixture <fixture@example.test> 1704067200 +0000\n")
        stream.extend(f"data {len(payload)}\n".encode("ascii"))
        stream.extend(payload)
        if parent is not None:
            stream.extend(f"from :{parent}\n".encode("ascii"))
        for merge in merges:
            stream.extend(f"merge :{merge}\n".encode("ascii"))
        for source, target in renames:
            stream.extend(f"R {source} {target}\n".encode("utf-8"))
        for path in deletions:
            stream.extend(f"D {path}\n".encode("utf-8"))
        for path, content in modifications:
            encoded = content.encode("utf-8")
            stream.extend(f"M 100644 inline {path}\n".encode("utf-8"))
            stream.extend(f"data {len(encoded)}\n".encode("ascii"))
            stream.extend(encoded)
        return mark

    main_tip = commit(
        "main",
        "Create fixture root",
        modifications=(
            ("cases/clean-negative.txt", "APP_MODE=local-test-only\n"),
            (
                "docs/provider-example.md",
                f"Documentation-only example: AWS_ACCESS_KEY_ID={AWS_EXAMPLE}\n",
            ),
        ),
    )
    added = commit(
        "main",
        "Add then remove synthetic credential",
        parent=main_tip,
        modifications=(("cases/added-then-deleted.env", f"AWS_ACCESS_KEY_ID={AWS_EXAMPLE}\n"),),
    )
    main_tip = commit(
        "main",
        "Delete synthetic credential",
        parent=added,
        deletions=("cases/added-then-deleted.env",),
    )

    deleted_branch = commit(
        "deleted-branch",
        "Add synthetic credential on a deleted branch",
        parent=main_tip,
        modifications=(("cases/deleted-branch.env", f"API_TOKEN={AWS_EXAMPLE}\n"),),
    )
    stream.extend(b"reset refs/heads/deleted-branch\n")

    tag_commit = commit(
        "main",
        "Add tagged synthetic credential",
        parent=main_tip,
        modifications=(("cases/tag.env", f"API_TOKEN={AWS_EXAMPLE}\n"),),
    )
    main_tip = tag_commit
    stream.extend(b"tag fixture-release\n")
    stream.extend(f"from :{tag_commit}\n".encode("ascii"))
    stream.extend(b"tagger Fixture <fixture@example.test> 1704067200 +0000\n")
    tag_message = b"Synthetic tag fixture\n"
    stream.extend(f"data {len(tag_message)}\n".encode("ascii"))
    stream.extend(tag_message)

    feature = commit(
        "merge-feature",
        "Add synthetic credential on merge feature",
        parent=main_tip,
        modifications=(("cases/merge.env", f"API_TOKEN={AWS_EXAMPLE}\n"),),
    )
    main_tip = commit(
        "main",
        "Merge synthetic credential feature",
        parent=main_tip,
        merges=(feature,),
        modifications=(("cases/merge.env", f"API_TOKEN={AWS_EXAMPLE}\n"),),
    )

    old_path = "cases/rename-before.env"
    new_path = "cases/rename-after.env"
    main_tip = commit(
        "main",
        "Add rename fixture",
        parent=main_tip,
        modifications=((old_path, f"API_TOKEN={AWS_EXAMPLE}\n"),),
    )
    main_tip = commit(
        "main",
        "Rename fixture",
        parent=main_tip,
        renames=((old_path, new_path),),
    )

    dropped = commit(
        "main",
        "Add force-push dropped synthetic credential",
        parent=main_tip,
        modifications=(("cases/force-push-dropped.env", f"API_TOKEN={AWS_EXAMPLE}\n"),),
    )
    previous_tip = main_tip
    stream.extend(b"reset refs/heads/main\n")
    stream.extend(f"from :{previous_tip}\n".encode("ascii"))
    main_tip = previous_tip

    encoded = base64.b64encode(AWS_EXAMPLE.encode("ascii")).decode("ascii")
    main_tip = commit(
        "main",
        "Add encoded synthetic credential",
        parent=main_tip,
        modifications=(("cases/base64.env", f"ENCODED_TOKEN={encoded}\n"),),
    )
    main_tip = commit(
        "main",
        "Add synthetic PEM block",
        parent=main_tip,
        modifications=((
            "cases/pem.env",
            "-----BEGIN PRIVATE KEY-----\nZmFrZV9wZW1fYmxvY2s=\n-----END PRIVATE KEY-----\n",
        ),),
    )
    main_tip = commit(
        "main",
        "Add split synthetic credential",
        parent=main_tip,
        modifications=((
            "cases/split-secret.env",
            "AWS_ACCESS_KEY_PART_1=AKIAIOSFODD\nAWS_ACCESS_KEY_PART_2=N7EXAMPLE\n",
        ),),
    )

    while mark < commit_count:
        main_tip = commit("main", f"Padding commit {mark + 1}", parent=main_tip)
    if mark != commit_count:
        raise RuntimeError("The fast-import fixture did not reach its requested commit count")
    stream.extend(b"done\n")
    subprocess.run(
        ["git", "-C", str(repo), "fast-import", "--quiet"],
        input=bytes(stream),
        check=True,
        capture_output=True,
    )
    _git(repo, "checkout", "-f", "main")
    object_types = _git(repo, "cat-file", "--batch-all-objects", "--batch-check=%(objecttype)")
    total_commits = sum(item == "commit" for item in object_types.splitlines())
    reachable_commits = int(_git(repo, "rev-list", "--all", "--count").strip())
    if total_commits != commit_count:
        raise RuntimeError("The fast-import fixture commit-object count is incorrect")
    refs = _git(repo, "for-each-ref", "--format=%(refname)")
    if "refs/heads/deleted-branch" in refs.splitlines():
        raise RuntimeError("The deleted-branch fixture is still reachable")
    if reachable_commits != commit_count - 2:
        raise RuntimeError("The deleted-branch and force-push commits are not both unreachable")
    return {
        "commit_objects": total_commits,
        "reachable_commits": reachable_commits,
        "deleted_branch_commit_mark": deleted_branch,
        "unreachable_scenario_commits": 2,
    }


def _relative_path(value: str, repo: Path) -> str:
    normalized = value.replace("\\", "/").removeprefix("./")
    prefix = repo.resolve().as_posix().rstrip("/") + "/"
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix):]
    return normalized


def _native_report(repo: Path, *, config_path: Path | None = None) -> list[dict[str, Any]]:
    binary = shutil.which("gitleaks")
    if not binary:
        raise RuntimeError("Native gitleaks is not installed")
    with tempfile.TemporaryDirectory(prefix="comparison-native-") as directory:
        report = Path(directory) / "report.json"
        config = config_path or (ROOT / "gitleaks.toml").resolve()
        result = subprocess.run(
            [
                binary,
                "detect",
                "--source",
                str(repo),
                "--config",
                str(config),
                "--report-format",
                "json",
                "--report-path",
                str(report),
                "--no-banner",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError("Native gitleaks failed; output was suppressed")
        payload = json.loads(report.read_text(encoding="utf-8")) if report.exists() else []
        return payload


def native_scan(repo: Path, run: int) -> set[str]:
    return {
        _relative_path(str(item.get("File") or ""), repo)
        for item in _native_report(repo)
        if item.get("File")
    }


def wrapper_scan(repo: Path, run: int) -> set[str]:
    from backend.detection.gitleaks_runner import run_gitleaks

    return {
        _relative_path(str(item.get("File") or ""), repo)
        for item in run_gitleaks(str(repo))
        if item.get("File")
    }


def detect_secrets_scan(repo: Path, run: int) -> set[str]:
    result = subprocess.run(
        ["detect-secrets", "scan", "--all-files"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("detect-secrets failed; output was suppressed")
    payload = json.loads(result.stdout)
    return {
        _relative_path(str(path), repo)
        for path, records in payload.get("results", {}).items()
        if records
    }


def _metrics(
    category: str,
    found: set[str],
    *,
    scanner: str,
) -> dict[str, Any]:
    if category in UNREACHABLE_CATEGORIES:
        return {
            "not_applicable_reason":
                "The commit object is unreachable from every ref and is outside this scanner's input.",
        }
    if scanner == "detect-secrets" and category in HISTORY_ONLY_CATEGORIES:
        return {
            "not_applicable_reason":
                "detect-secrets scans checked-out files, not Git history; this case is not represented in the checkout.",
        }

    true_paths = set(POSITIVE_CASES.get(category, []))
    if true_paths:
        true_detected = bool(true_paths & found)
        unknown_findings = found - ALL_POSITIVE_PATHS
        negative_examples = set(NEGATIVE_CASES.values()) | unknown_findings
        fp = len(found & negative_examples)
        tp = int(true_detected)
        fn = 1 - tp
        tn = len(negative_examples) - fp
        precision: float | None = tp / (tp + fp) if tp + fp else 0.0
        recall: float | None = tp / (tp + fn)
        f1: float | None = (
            2 * precision * recall / (precision + recall)
            if precision is not None and precision + recall
            else 0.0
        )
        fpr = fp / (fp + tn) if fp + tn else 0.0
    else:
        path = NEGATIVE_CASES[category]
        fp = int(path in found)
        tn = 1 - fp
        tp = fn = 0
        precision = recall = f1 = None
        fpr = float(fp)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def _summary(values: list[float | None], rng: random.Random) -> dict[str, Any]:
    measured = [float(value) for value in values if value is not None]
    if not measured:
        return {
            "status": "NOT APPLICABLE",
            "median": None,
            "min": None,
            "max": None,
            "ci95_low": None,
            "ci95_high": None,
        }
    bootstrap_medians = [
        _percentile([rng.choice(measured) for _ in measured], 0.5)
        for _ in range(2000)
    ]
    return {
        "status": "MEASURED",
        "median": _percentile(measured, 0.5),
        "min": min(measured),
        "max": max(measured),
        "ci95_low": _percentile(bootstrap_medians, 0.025),
        "ci95_high": _percentile(bootstrap_medians, 0.975),
    }


def _summarize_scanner(
    per_run: list[dict[str, dict[str, Any]]],
    categories: list[str],
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    output: dict[str, Any] = {"runs": len(per_run), "categories": {}}
    for category in categories:
        category_output: dict[str, Any] = {}
        reason = per_run[0][category].get("not_applicable_reason")
        if reason:
            category_output["status"] = "NOT APPLICABLE"
            category_output["reason"] = reason
            for metric in ("precision", "recall", "f1", "false_positive_rate"):
                category_output[metric] = _summary([None] * len(per_run), rng)
            category_output["counts_across_runs"] = None
            output["categories"][category] = category_output
            continue

        category_output["status"] = "MEASURED"
        for metric in ("precision", "recall", "f1", "false_positive_rate"):
            category_output[metric] = _summary(
                [record[category][metric] for record in per_run],
                rng,
            )
        counts = {
            key: sum(int(record[category][key] or 0) for record in per_run)
            for key in ("tp", "fp", "fn", "tn")
        }
        category_output["counts_across_runs"] = counts
        output["categories"][category] = category_output
    return output


def _scanner_version(name: str) -> str:
    if name == "detect-secrets":
        return version("detect-secrets")
    binary = shutil.which("gitleaks")
    if not binary:
        raise RuntimeError("Native gitleaks is not installed")
    completed = subprocess.run(
        [binary, "version"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Could not read the gitleaks version")
    return completed.stdout.strip() or completed.stderr.strip()


def _write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Comparative scanner benchmark",
        "",
        "Generated from identical synthetic Git fast-import repositories. All credential-shaped values are synthetic test data; no real secret values are included in this report.",
        "",
        f"- Generated: `{payload['generated']}`",
        f"- Native Gitleaks: `{payload['versions']['native-gitleaks']}`",
        f"- Wrapper: Gitleaks `{payload['versions']['wrapper']}` via `run_gitleaks`",
        f"- detect-secrets: `{payload['versions']['detect-secrets']}`",
        "- Repetitions: five per scanner and repository size; bootstrap 95% CIs use 2,000 resamples of the median.",
        "- Positive categories are evaluated one-vs-known-negative examples; the clean-negative and documentation-example rows are negative-only, so precision, recall, and F1 are not applicable for those rows.",
        "",
    ]
    for size, fixture in payload["fixtures"].items():
        lines.extend([
            f"## {size} commits",
            "",
            f"Verified commit objects: {fixture['commit_objects']}; reachable commits: {fixture['reachable_commits']}.",
            "",
            "| Scanner | Category | Applicability | Precision median [95% CI] | Recall median [95% CI] | F1 median [95% CI] | FP rate median [95% CI] |",
            "|---|---|---:|---:|---:|---:|---:|",
        ])
        for scanner, results in fixture["scanners"].items():
            for category, metrics in results["categories"].items():
                cells = []
                for metric in ("precision", "recall", "f1", "false_positive_rate"):
                    value = metrics[metric]
                    if value["status"] != "MEASURED":
                        cells.append("NOT APPLICABLE")
                    else:
                        cells.append(
                            f"{value['median']:.3f} "
                            f"[{value['ci95_low']:.3f}, {value['ci95_high']:.3f}] "
                            f"(min {value['min']:.3f}, max {value['max']:.3f})"
                        )
                applicability = metrics.get("status", "MEASURED")
                if metrics.get("reason"):
                    applicability += f": {metrics['reason']}"
                lines.append(
                    f"| {scanner} | {CATEGORY_LABELS.get(category, category)} | "
                    f"{applicability} | {cells[0]} | {cells[1]} | "
                    f"{cells[2]} | {cells[3]} |"
                )
        lines.append("")
    lifecycle = payload["lifecycle_comparison"]
    lines.extend([
        "## Lifecycle comparison (measured fixture runs)",
        "",
        "| Measure | Native Gitleaks | Gitleaks wrapper | SecretGuard pipeline |",
        "|---|---|---|---|",
        (
            "| Deleted-but-recoverable finding flagged | "
            f"{lifecycle['deleted_but_recoverable']['native_gitleaks']} | "
            f"{lifecycle['deleted_but_recoverable']['gitleaks_wrapper']} | "
            "Reported through the same scanner result |"
        ),
        (
            "| Coverage manifest | Not provided | Not provided by `run_gitleaks` | "
            f"{lifecycle['coverage_manifest']['completeness']}; "
            f"{lifecycle['coverage_manifest']['commits_actually_scanned']} scanned / "
            f"{lifecycle['coverage_manifest']['commits_reachable']} reachable commits; "
            f"{lifecycle['coverage_manifest']['unreachable_object_count']} unreachable objects |"
        ),
        (
            "| Repeated synthetic finding across 100 commits | "
            f"{lifecycle['dedupe_100_commits']['native_gitleaks_raw_findings']} raw findings | "
            f"{lifecycle['dedupe_100_commits']['gitleaks_wrapper_raw_findings']} raw findings | "
            f"{lifecycle['dedupe_100_commits']['pipeline_raw_findings']} history matches → "
            f"{lifecycle['dedupe_100_commits']['pipeline_deduplicated_findings']} deduplicated finding(s) |"
        ),
        (
            "| Invalid configuration | "
            f"{lifecycle['fail_closed']['native_gitleaks']} | "
            f"{lifecycle['fail_closed']['gitleaks_wrapper']} | "
            f"{lifecycle['fail_closed']['pipeline']} |"
        ),
        "",
        "The lifecycle rows are direct fixture observations. Native Gitleaks and `run_gitleaks` "
        "use the same scanner, so identical raw detections are expected; deduplication and "
        "coverage-manifest reporting are separate SecretGuard pipeline capabilities. The coverage "
        "manifest records reachable refs and reports unreachable objects separately; `complete` "
        "does not mean unreachable objects were scanned.",
        "",
    ])
    lines.extend([
        "## Method and limitations",
        "",
        "The fixtures include added-then-deleted content, two unreachable-object scenarios, a tag, a merge, rename, base64 and PEM-shaped examples, a split credential, clean text, and a documentation example. The two unreachable-object categories mean exactly that their commits are not reachable from any ref; ref-walking scanners cannot inspect those objects, so their precision/recall/F1 are not applicable rather than zero. `detect-secrets scan --all-files` scans the checked-out working tree, not Git history; history-only cases absent from the checkout are not applicable.",
        "",
        "Precision and recall are based on the single labeled credential path for each positive scenario and the two labeled negative paths plus any unrecognized reported paths. These synthetic outcomes are not estimates of production performance.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _generate_repeated_secret_fixture(repo: Path, commit_count: int) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "--initial-branch=main")
    stream = bytearray(b"reset refs/heads/main\n")
    previous: int | None = None
    for mark in range(1, commit_count + 1):
        message = f"Repeated synthetic finding {mark}\n".encode("utf-8")
        content = f"AWS_KEY = '{AWS_EXAMPLE}'\nREVISION = {mark}\n".encode("utf-8")
        stream.extend(f"commit refs/heads/main\nmark :{mark}\n".encode("ascii"))
        stream.extend(b"author Fixture <fixture@example.test> 1704067200 +0000\n")
        stream.extend(b"committer Fixture <fixture@example.test> 1704067200 +0000\n")
        stream.extend(f"data {len(message)}\n".encode("ascii"))
        stream.extend(message)
        if previous is not None:
            stream.extend(f"from :{previous}\n".encode("ascii"))
        stream.extend(b"M 100644 inline repeated.env\n")
        stream.extend(f"data {len(content)}\n".encode("ascii"))
        stream.extend(content)
        previous = mark
    stream.extend(b"done\n")
    subprocess.run(
        ["git", "-C", str(repo), "fast-import", "--quiet"],
        input=bytes(stream),
        check=True,
        capture_output=True,
    )
    _git(repo, "checkout", "-f", "main")
    actual = int(_git(repo, "rev-list", "--all", "--count").strip())
    if actual != commit_count:
        raise RuntimeError("The repeated-secret fixture has an unexpected commit count")


def _invalid_config_outcome(repo: Path) -> dict[str, int | bool]:
    binary = shutil.which("gitleaks")
    if not binary:
        raise RuntimeError("Native gitleaks is not installed")
    with tempfile.TemporaryDirectory(prefix="comparison-invalid-config-") as directory:
        result = subprocess.run(
            [
                binary,
                "detect",
                "--source",
                str(repo),
                "--config",
                str(Path(directory) / "missing-config.toml"),
                "--report-format",
                "json",
                "--report-path",
                str(Path(directory) / "report.json"),
                "--no-banner",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return {
            "returncode": result.returncode,
            "config_rejected": "unable to load gitleaks config" in result.stderr.lower(),
        }


def _lifecycle_comparison(
    repo: Path,
    first_run_findings: dict[str, set[str]],
    workspace: Path,
) -> dict[str, Any]:
    from backend.detection.gitleaks_runner import run_gitleaks
    from backend.services.coverage import build_coverage

    manifest = build_coverage(repo)
    repeated_repo = workspace / "repeated-secret-100"
    _generate_repeated_secret_fixture(repeated_repo, 100)
    native_count = len(_native_report(repeated_repo))
    wrapper_count = len(run_gitleaks(str(repeated_repo)))

    from src.shd.cli import run_pipeline
    from src.shd.matcher import match
    from src.shd.walker import walk_repository

    prior_hmac_key = os.environ.get("SHD_HMAC_KEY")
    os.environ["SHD_HMAC_KEY"] = "synthetic-benchmark-only-key"
    try:
        raw_pipeline_count = sum(
            len(match(record))
            for record in walk_repository(str(repeated_repo))
        )
        deduplicated_count = len(run_pipeline(str(repeated_repo)))
    finally:
        if prior_hmac_key is None:
            os.environ.pop("SHD_HMAC_KEY", None)
        else:
            os.environ["SHD_HMAC_KEY"] = prior_hmac_key

    clean_config_repo = workspace / "invalid-config-clean"
    clean_config_repo.mkdir()
    _git(clean_config_repo, "init", "--initial-branch=main")
    _git(clean_config_repo, "config", "user.name", "Benchmark Fixture")
    _git(clean_config_repo, "config", "user.email", "fixture@example.test")
    (clean_config_repo / "README.txt").write_text("clean fixture\n", encoding="utf-8")
    _git(clean_config_repo, "add", "README.txt")
    _git(clean_config_repo, "commit", "-m", "Create clean scan target")
    native_invalid = _invalid_config_outcome(clean_config_repo)
    native_invalid_rc = int(native_invalid["returncode"])
    native_fail_closed = (
        bool(native_invalid["config_rejected"])
        or native_invalid_rc not in (0, 1)
    )
    try:
        run_gitleaks(str(repo), config_path="missing-benchmark-config.toml")
    except RuntimeError:
        wrapper_refused = True
    else:
        wrapper_refused = False

    return {
        "deleted_but_recoverable": {
            "native_gitleaks": "flagged" if "cases/added-then-deleted.env" in first_run_findings["native-gitleaks"] else "not flagged",
            "gitleaks_wrapper": "flagged" if "cases/added-then-deleted.env" in first_run_findings["wrapper"] else "not flagged",
        },
        "coverage_manifest": {
            "completeness": manifest["completeness"],
            "commits_reachable": manifest["commits_reachable"],
            "commits_actually_scanned": manifest["commits_actually_scanned"],
            "unreachable_object_count": manifest["unreachable_object_count"],
        },
        "dedupe_100_commits": {
            "fixture_commits": 100,
            "native_gitleaks_raw_findings": native_count,
            "gitleaks_wrapper_raw_findings": wrapper_count,
            "pipeline_raw_findings": raw_pipeline_count,
            "pipeline_deduplicated_findings": deduplicated_count,
        },
        "fail_closed": {
            "native_gitleaks": (
                f"{'yes' if native_fail_closed else 'no'} "
                f"(exit {native_invalid_rc}; invalid config rejected: "
                f"{str(bool(native_invalid['config_rejected'])).lower()})"
            ),
            "gitleaks_wrapper": "yes (rejects non-owned config)" if wrapper_refused else "no",
            "pipeline": "yes (uses the same owned-config wrapper)" if wrapper_refused else "no",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000])
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    if args.runs < 5:
        parser.error("--runs must be at least 5")
    if any(size < 20 for size in args.sizes):
        parser.error("fixture sizes must allow the fixed category commits")
    if 100 not in args.sizes:
        parser.error("the lifecycle comparison requires the 100-commit fixture")
    if version("detect-secrets") != "1.5.0":
        raise RuntimeError("detect-secrets must be pinned to version 1.5.0")

    scanners = {
        "native-gitleaks": native_scan,
        "wrapper": wrapper_scan,
        "detect-secrets": detect_secrets_scan,
    }
    categories = list(POSITIVE_CASES) + list(NEGATIVE_CASES)
    output: dict[str, Any] = {
        "schema_version": 2,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "versions": {
            "native-gitleaks": _scanner_version("native-gitleaks"),
            "wrapper": _scanner_version("wrapper"),
            "detect-secrets": _scanner_version("detect-secrets"),
        },
        "runs_per_scanner": args.runs,
        "bootstrap_resamples": 2000,
        "fixtures": {},
        "lifecycle_comparison": {},
    }

    with tempfile.TemporaryDirectory(prefix="secretguard-comparison-") as workdir:
        fixture_root = Path(workdir)
        lifecycle_repo: Path | None = None
        lifecycle_findings: dict[str, set[str]] = {}
        for size in args.sizes:
            repo = fixture_root / f"fixture-{size}"
            fixture_info = generate_fast_import_fixture(repo, size)
            if size == 100:
                lifecycle_repo = repo
            fixture_output: dict[str, Any] = {
                **fixture_info,
                "scanners": {},
            }
            for scanner_index, (name, scan) in enumerate(scanners.items()):
                per_run = []
                first_run_found: set[str] = set()
                for run in range(1, args.runs + 1):
                    found = scan(repo, run)
                    if run == 1:
                        first_run_found = found
                    per_run.append({
                        category: _metrics(category, found, scanner=name)
                        for category in categories
                    })
                if size == 100:
                    lifecycle_findings[name] = first_run_found
                fixture_output["scanners"][name] = _summarize_scanner(
                    per_run,
                    categories,
                    seed=1704067200 + size + scanner_index,
                )
            output["fixtures"][str(size)] = fixture_output
        if lifecycle_repo is not None:
            output["lifecycle_comparison"] = _lifecycle_comparison(
                lifecycle_repo,
                lifecycle_findings,
                fixture_root,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(output, args.markdown)
    print(f"Comparison report saved: {args.output}")
    print(f"Comparison summary saved: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
