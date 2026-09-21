import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _resolve_gitleaks_binary() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    venv_scripts = repo_root / ".venv" / "Scripts"
    if venv_scripts.exists():
        current_path = os.environ.get("PATH", "")
        entries = [str(venv_scripts)] + ([p for p in current_path.split(os.pathsep) if p] if current_path else [])
        os.environ["PATH"] = os.pathsep.join(entries)

    which_binary = shutil.which("gitleaks")
    if which_binary:
        candidate = Path(which_binary)
        try:
            subprocess.run([str(candidate), "--version"], check=False, capture_output=True, text=True, timeout=10)
        except (OSError, ValueError):
            pass
        else:
            return str(candidate)

    raise RuntimeError("gitleaks binary not found on PATH. Install Gitleaks v8.18+ and ensure it is available in your PATH before running SecretGuard.")


def run_gitleaks(repo_path: str, config_path: str = "gitleaks.toml") -> list[dict]:
    """Invoke the gitleaks binary via subprocess against repo_path with
    `gitleaks detect --source <repo_path> --report-format json --report-path <tmp>`.
    Read the JSON report and return the parsed list of raw findings.
    Must raise a clear RuntimeError (not a bare subprocess exception) if the
    gitleaks binary is not found on PATH, with an actionable message."""
    binary = _resolve_gitleaks_binary()

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        report_path = tmp.name

    command = [
        binary,
        "detect",
        "--source",
        repo_path,
        "--report-format",
        "json",
        "--report-path",
        report_path,
    ]
    if config_path and config_path != "gitleaks.toml":
        command.extend(["--config", config_path])

    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode not in (0, 1):
            raise RuntimeError(f"gitleaks failed for {repo_path}: {completed.stderr.strip() or completed.stdout.strip()}")
        if not Path(report_path).exists():
            return []
        with open(report_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    finally:
        try:
            Path(report_path).unlink(missing_ok=True)
        except OSError:
            pass

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("Leaks"), list):
        return payload["Leaks"]
    return []
