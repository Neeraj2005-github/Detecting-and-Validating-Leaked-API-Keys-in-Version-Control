from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import git
import psutil


def repo_size_bytes(repo_path: str | Path) -> int:
    path = Path(repo_path)
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def peak_rss_mb(process: psutil.Process) -> float | None:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, process.pid)
            if handle:
                try:
                    ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                        handle,
                        ctypes.byref(counters),
                        counters.cb,
                    )
                    if ok:
                        return counters.PeakWorkingSetSize / (1024 * 1024)
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
        except (AttributeError, OSError):
            pass
    try:
        import resource
        peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys_platform() == "linux":
            return peak_kb / 1024
        return peak_kb / (1024 * 1024)
    except (ImportError, AttributeError):
        return None


def sys_platform() -> str:
    return platform.system().lower()


def cpu_model_name() -> str:
    if os.name == "nt":
        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False,
            )
            name = completed.stdout.strip()
            if name:
                return name
        except (OSError, subprocess.TimeoutExpired):
            pass
    return platform.processor() or "NOT MEASURED"


def profile_child_process(command: list[str], cwd: str | Path) -> dict[str, Any]:
    """Measure wall, CPU and peak working set for a direct child process."""
    started_wall = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    child = psutil.Process(process.pid)
    peak_rss_mb: float | None = None
    started_cpu = child.cpu_times()
    max_child_cpu = started_cpu.user + started_cpu.system
    try:
        while process.poll() is None:
            try:
                peak_rss_mb = max(
                    peak_rss_mb or 0.0,
                    child.memory_info().rss / (1024 * 1024),
                )
                current_cpu = child.cpu_times()
                max_child_cpu = max(
                    max_child_cpu,
                    current_cpu.user + current_cpu.system,
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(0.005)
        stdout, stderr = process.communicate(timeout=30)
        try:
            cpu = child.cpu_times()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            cpu = started_cpu
        max_child_cpu = max(max_child_cpu, cpu.user + cpu.system)
        try:
            if os.name == "nt":
                peak_rss_mb = peak_rss_mb or 0.0
            else:
                peak_rss_mb = peak_rss_mb or child.memory_info().rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        raise RuntimeError("PROFILED_PROCESS_TIMEOUT")
    wall = time.perf_counter() - started_wall
    return {
        "returncode": process.returncode,
        "wall_time_seconds": wall,
        "cpu_time_seconds": float(
            max(0.0, max_child_cpu - (started_cpu.user + started_cpu.system))
        ),
        "peak_rss_mb": peak_rss_mb,
        "stdout": stdout,
        "stderr": stderr,
    }


def gitleaks_version() -> str:
    binary = shutil.which("gitleaks")
    if not binary:
        return "NOT MEASURED"
    try:
        completed = subprocess.run(
            [binary, "version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )
        return completed.stdout.strip() or completed.stderr.strip() or "NOT MEASURED"
    except (OSError, subprocess.TimeoutExpired):
        return "NOT MEASURED"


def profile_host(repo_path: str | Path) -> dict[str, Any]:
    process = psutil.Process()
    cpu = process.cpu_times()
    repo = git.Repo(repo_path)
    try:
        commit_count = len(set(repo.git.rev_list("--all").splitlines()))
    except git.GitCommandError:
        commit_count = 0
    return {
        "peak_rss_mb": peak_rss_mb(process),
        "cpu_time_seconds": float(cpu.user + cpu.system),
        "wall_time_seconds": "NOT MEASURED",
        "repo_size_bytes": repo_size_bytes(repo_path),
        "commit_count": commit_count,
        "cpu_model": cpu_model_name(),
        "ram_bytes": psutil.virtual_memory().total,
        "os": platform.platform() or "NOT MEASURED",
        "python_version": platform.python_version(),
        "gitleaks_version": gitleaks_version(),
    }


class ResourceRun:
    def __enter__(self) -> "ResourceRun":
        self.process = psutil.Process()
        self.started_wall = time.perf_counter()
        self.started_cpu = self.process.cpu_times()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False

    def finish(self, repo_path: str | Path) -> dict[str, Any]:
        wall = time.perf_counter() - self.started_wall
        cpu = self.process.cpu_times()
        profile = profile_host(repo_path)
        profile["cpu_time_seconds"] = float(
            (cpu.user - self.started_cpu.user) + (cpu.system - self.started_cpu.system)
        )
        profile["wall_time_seconds"] = float(wall)
        return profile
