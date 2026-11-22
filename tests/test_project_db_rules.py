from __future__ import annotations

import hashlib
from pathlib import Path

import git

from backend.detection.gitleaks_runner import run_gitleaks


def _commit_file(repo: git.Repo, repo_path: Path, relative: str, content: str) -> None:
    path = repo_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo.index.add([relative])
    repo.index.commit(f"fixture {relative}")


def test_db_project_rules_detect_and_allowlist(tmp_path: Path) -> None:
    repo_path = tmp_path / "db-rules"
    repo = git.Repo.init(repo_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "DB Rule Test")
        config.set_value("user", "email", "db-rule@example.test")

    _commit_file(repo, repo_path, ".env", "DB_PASSWORD=AlphaDb_Secret_123\n")
    _commit_file(repo, repo_path, "config.yml", "mysql:\n  password: AlphaMysql_Secret_123\n")
    _commit_file(repo, repo_path, "database.json", '{"POSTGRES_PASSWORD":"AlphaPostgres_Secret_123"}\n')
    _commit_file(repo, repo_path, "connection.py", "url = 'mongodb://dbuser:AlphaMongo_Secret_123@mongo.example.test/app'\n")
    _commit_file(repo, repo_path, "redis.py", "REDIS_URL = 'redis://dbuser:AlphaRedis_Secret_123@redis.example.test/0'\n")
    _commit_file(repo, repo_path, ".env.example", "MYSQL_PWD=placeholder\nPOSTGRES_PASSWORD=changeme\n")
    _commit_file(repo, repo_path, "safe.yml", "DB_PASSWORD: <password>\nMYSQL_PWD: ${MYSQL_PASSWORD}\nPOSTGRES_PASSWORD: EXAMPLE\n")

    findings = run_gitleaks(str(repo_path))
    assert any(item.get("RuleID") == "secretguard-db-password-assignment" for item in findings)
    assert any(item.get("RuleID") == "secretguard-db-connection-uri" for item in findings)
    assert any("redis://" in str(item.get("Secret", "")) for item in findings)
    assert all("placeholder" not in str(item.get("Secret", "")).lower() for item in findings)
    assert all("changeme" not in str(item.get("Secret", "")).lower() for item in findings)


def test_config_lock_matches_gitleaks_toml() -> None:
    root = Path(__file__).resolve().parents[1]
    actual = hashlib.sha256((root / "gitleaks.toml").read_bytes()).hexdigest()
    locked = (root / "config.lock").read_text(encoding="ascii").strip()
    assert actual == locked
