import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from backend.services.report_parser import validate_gitleaks_report


REPO_ROOT = Path(__file__).resolve().parents[2]
OWNED_CONFIG = REPO_ROOT / "gitleaks.toml"
CONFIG_LOCK = REPO_ROOT / "config.lock"
PROCESS_MEMORY_LIMIT_BYTES = 512 * 1024 * 1024


class _WindowsJob:
    def __init__(self, memory_limit_bytes: int) -> None:
        import ctypes
        from ctypes import wintypes

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        self._ctypes = ctypes
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        self._kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.INT,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        self._kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        self._kernel32.SetInformationJobObject.restype = wintypes.BOOL
        self._kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._handle = self._kernel32.CreateJobObjectW(None, None)
        if not self._handle:
            raise OSError(ctypes.get_last_error(), "Could not create Gitleaks job")

        limit = ExtendedLimitInformation()
        limit.BasicLimitInformation.LimitFlags = 0x2000 | 0x100
        limit.ProcessMemoryLimit = memory_limit_bytes
        ok = self._kernel32.SetInformationJobObject(
            self._handle,
            9,
            ctypes.byref(limit),
            ctypes.sizeof(limit),
        )
        if not ok:
            self.close()
            raise OSError(ctypes.get_last_error(), "Could not configure Gitleaks job limits")

    def assign(self, process: subprocess.Popen[str]) -> None:
        if not self._kernel32.AssignProcessToJobObject(self._handle, process._handle):
            raise OSError(self._ctypes.get_last_error(), "Could not assign Gitleaks to its job")

    def close(self) -> None:
        if getattr(self, "_handle", None):
            self._kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> "_WindowsJob":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


def _set_linux_memory_limit() -> None:
    import resource

    resource.setrlimit(
        resource.RLIMIT_DATA,
        (PROCESS_MEMORY_LIMIT_BYTES, PROCESS_MEMORY_LIMIT_BYTES),
    )


def _run_limited_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    job = _WindowsJob(PROCESS_MEMORY_LIMIT_BYTES) if os.name == "nt" else None
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            env=env,
            preexec_fn=(
                _set_linux_memory_limit
                if sys.platform.startswith("linux")
                else None
            ),
        )
        if job is not None:
            job.assign(process)
        try:
            stdout, stderr = process.communicate(timeout=60)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            raise RuntimeError("Gitleaks timed out") from exc
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except OSError as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
        raise RuntimeError("Gitleaks could not be started or sandboxed") from exc
    finally:
        if job is not None:
            job.close()


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

    binary = str(Path(_resolve_gitleaks_binary()).resolve())
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

    system_root = os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR", "")
    path_entries = [str(Path(binary).parent)]
    git_binary = shutil.which("git")
    if git_binary:
        path_entries.append(str(Path(git_binary).parent))
    if system_root:
        path_entries.append(str(Path(system_root) / "System32"))
    env = {
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "WINDIR": os.environ.get("WINDIR", ""),
        "PATH": os.pathsep.join(path_entries),
        "TEMP": private_dir.name,
        "TMP": private_dir.name,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
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
        completed = _run_limited_process(command, cwd=source, env=env)
        if completed.returncode not in (0, 1):
            raise RuntimeError("Gitleaks failed; subprocess diagnostics are suppressed")
        if not report_path.exists():
            raise RuntimeError("Gitleaks report is missing")
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gitleaks returned an invalid report") from exc
    finally:
        private_dir.cleanup()

    if isinstance(payload, dict) and isinstance(payload.get("Leaks"), list):
        payload = payload["Leaks"]
    return validate_gitleaks_report(payload)
