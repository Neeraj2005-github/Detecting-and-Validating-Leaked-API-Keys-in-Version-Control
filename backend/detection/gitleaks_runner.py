import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.services.report_parser import validate_gitleaks_report


REPO_ROOT = Path(__file__).resolve().parents[2]
OWNED_CONFIG = REPO_ROOT / "gitleaks.toml"
CONFIG_LOCK = REPO_ROOT / "config.lock"


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
    """Run Gitleaks against a repository using only SecretGuard-owned configuration."""
    import hashlib

    binary = _resolve_gitleaks_binary()
    requested = (REPO_ROOT / config_path).resolve() if not Path(config_path).is_absolute() else Path(config_path).resolve()
    if requested != OWNED_CONFIG or not OWNED_CONFIG.is_file():
        raise RuntimeError("Gitleaks config refusal: SecretGuard-owned gitleaks.toml is required")
    if not CONFIG_LOCK.is_file():
        raise RuntimeError("Gitleaks config refusal: config.lock is missing")
    actual = hashlib.sha256(OWNED_CONFIG.read_bytes()).hexdigest()
    locked = CONFIG_LOCK.read_text(encoding="ascii").strip().lower()
    if actual != locked:
        raise RuntimeError("Gitleaks config refusal: gitleaks.toml hash differs from config.lock")

    source = Path(repo_path).resolve()
    if not source.is_dir():
        raise RuntimeError("Gitleaks source refusal: repository path is missing")

    private_dir = tempfile.TemporaryDirectory(prefix="secretguard-gitleaks-")
    report_path = Path(private_dir.name) / "report.json"
    try:
        os.chmod(private_dir.name, 0o700)
    except (AttributeError, OSError):
        pass

    env = {
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "WINDIR": os.environ.get("WINDIR", ""),
        "PATH": os.environ.get("PATH", ""),
    }
    command = [
        binary,
        "detect",
        "--source",
        str(source),
        "--report-format",
        "json",
        "--report-path",
        str(report_path),
        "--config",
        str(OWNED_CONFIG.resolve()),
        "--no-banner",
    ]

    try:
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
                shell=False,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Gitleaks timed out") from exc
        except OSError as exc:
            raise RuntimeError("Gitleaks could not be started") from exc
        if completed.returncode not in (0, 1):
            raise RuntimeError("Gitleaks failed; subprocess diagnostics are suppressed")
        if not report_path.exists():
            return []
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gitleaks returned an invalid report") from exc
    finally:
        private_dir.cleanup()

    if isinstance(payload, dict) and isinstance(payload.get("Leaks"), list):
        payload = payload["Leaks"]
    return validate_gitleaks_report(payload)
