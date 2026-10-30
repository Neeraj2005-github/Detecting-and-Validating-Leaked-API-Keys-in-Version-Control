#!/usr/bin/env python3
"""CLI runner for the O1.1 Problem Reproduction Engine.

Usage
-----
::

    # From the project root (uses defaults):
    python -m scripts.reproduce_problem

    # Or directly:
    python scripts/reproduce_problem.py

    # With custom output directory:
    python scripts/reproduce_problem.py --output-dir ./my_output

Exit codes
----------
* ``0`` – reproduction **PASS** (secret found in history, absent from working tree).
* ``1`` – reproduction **FAIL** or unexpected error.
"""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is importable regardless of invocation method.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.services.o1_reproducer import run_reproduction, save_artifacts  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="reproduce_problem",
        description=textwrap.dedent(
            """\
            O1.1 Problem Reproduction Engine – SecretGuard
            ================================================
            Creates a temporary Git repository with a realistic secret-leak
            scenario and verifies that deleted secrets remain recoverable in
            Git history.
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT,
        help=(
            "Directory where artifact files are written.  "
            "JSON → <output-dir>/artifacts/o1_reproduction_log.json, "
            "Markdown → <output-dir>/docs/o1_reproduction_log.md.  "
            "Defaults to the project root."
        ),
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=None,
        help=(
            "Optional explicit path for the temporary Git repository.  "
            "If omitted a directory is created in the system temp folder."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def _print_summary(result: dict) -> None:
    """Pretty-print a human-readable summary to stdout."""
    sep = "=" * 64
    verification = result.get("verification", {})
    timeline = result.get("timeline", [])

    print(sep)
    print("  O1.1 Problem Reproduction – Summary")
    print(sep)
    print(f"  Status              : {result.get('status', 'UNKNOWN')}")
    print(f"  Repo path           : {result.get('repo_path', 'N/A')}")
    print(f"  Total commits       : {len(timeline)}")
    print(f"  Reachable SHAs      : {len(result.get('rev_list', []))}")
    print()
    print("  Verification:")
    print(
        f"    Secret in history       : "
        f"{'YES' if verification.get('secret_in_history') else 'NO'}"
    )
    print(
        f"    Secret in working tree  : "
        f"{'YES' if verification.get('secret_in_working_tree') else 'NO'}"
    )
    print(
        f"    Secret recoverable      : "
        f"{'YES' if verification.get('secret_recoverable') else 'NO'}"
    )
    print(
        f"    Commit adding secret    : "
        f"{verification.get('commit_adding_secret', 'N/A')[:12]}"
    )
    print(
        f"    Commit removing secret  : "
        f"{verification.get('commit_removing_secret', 'N/A')[:12]}"
    )
    print()

    print("  Commit Timeline:")
    for idx, entry in enumerate(timeline, start=1):
        sha_short = entry.get("sha", "")[:12]
        msg = entry.get("message", "")
        files = ", ".join(entry.get("files_changed", []))
        print(f"    {idx}. [{sha_short}] {msg}  ({files})")

    print(sep)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI runner.

    Parameters
    ----------
    argv:
        Argument list.  ``None`` defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        Exit code: ``0`` on PASS, ``1`` on FAIL or error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Logging -----------------------------------------------------------
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logger = logging.getLogger("reproduce_problem")

    try:
        # Run reproduction -----------------------------------------------
        repo_dir = str(args.repo_dir) if args.repo_dir else None
        result = run_reproduction(repo_dir=repo_dir)

        # Save artifacts -------------------------------------------------
        output_dir: Path = args.output_dir.resolve()
        json_path, md_path = save_artifacts(result, output_dir)
        logger.info("Artifacts saved:")
        logger.info("  JSON     → %s", json_path)
        logger.info("  Markdown → %s", md_path)

        # Print summary --------------------------------------------------
        _print_summary(result)

        if result.get("status") == "PASS":
            logger.info("Reproduction PASSED ✅")
            return 0
        else:
            logger.warning("Reproduction FAILED ❌")
            return 1

    except Exception:
        logger.exception("Fatal error during reproduction")
        return 1


if __name__ == "__main__":
    sys.exit(main())
