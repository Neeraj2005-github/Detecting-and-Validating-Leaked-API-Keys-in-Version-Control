"""Runtime dependency and sandbox readiness checks for the O1 gate."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sqlite3
import subprocess
from typing import Any

from sqlalchemy.exc import SQLAlchemyError


def _module_status(module_name: str, package_name: str | None = None) -> dict[str, Any]:
    available = importlib.util.find_spec(module_name) is not None
    return {"available": available, "package": package_name or module_name}


def _binary_status(binary: str, version_args: list[str]) -> dict[str, Any]:
    path = shutil.which(binary)
    if not path:
        return {"available": False, "path": None, "version": None}
    try:
        result = subprocess.run(
            [path, *version_args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "path": path, "version": None, "error": type(exc).__name__}
    version = (result.stdout or result.stderr).strip().splitlines()
    return {"available": result.returncode == 0, "path": path, "version": version[0] if version else None}


def _database_status() -> dict[str, Any]:
    configured_url = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    if configured_url.startswith("sqlite"):
        try:
            connection = sqlite3.connect(":memory:")
            connection.execute("SELECT 1")
            connection.close()
            return {"available": True, "backend": "sqlite", "configured_url": "sqlite:///:memory:"}
        except sqlite3.Error as exc:
            return {"available": False, "backend": "sqlite", "error": type(exc).__name__}

    if not configured_url.startswith(("mysql://", "mysql+pymysql://", "mysql+mysqlconnector://")):
        return {"available": False, "backend": "unsupported", "configured_url": configured_url.split("@")[0]}
    try:
        from sqlalchemy import create_engine

        engine = create_engine(configured_url, connect_args={"connect_timeout": 2})
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        engine.dispose()
        return {"available": True, "backend": "mysql", "configured_url": configured_url.split("@")[0]}
    except (ImportError, OSError, SQLAlchemyError) as exc:
        return {"available": False, "backend": "mysql", "error": type(exc).__name__}


def check_dependencies() -> dict[str, Any]:
    """Return live, non-secret readiness data for all O1 dependencies."""
    return {
        "git_cli": _binary_status("git", ["--version"]),
        "gitpython": _module_status("git", "GitPython"),
        "scikit_learn": _module_status("sklearn", "scikit-learn"),
        "xgboost": _module_status("xgboost"),
        "shap": _module_status("shap"),
        "psutil": _module_status("psutil"),
        "gitleaks": _binary_status("gitleaks", ["version"]),
        "database": _database_status(),
        "docker_rotation_sandbox": _binary_status("docker", ["info"]),
    }


__all__ = ["check_dependencies"]
