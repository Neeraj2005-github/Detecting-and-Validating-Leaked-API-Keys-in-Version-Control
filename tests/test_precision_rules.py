from __future__ import annotations

from pathlib import Path

import git

from backend.ml.detector import detect_lines
from backend.detection.gitleaks_runner import run_gitleaks
from backend.scanner.history_walker import walk_history
from backend.services.coverage import build_coverage


def _repo(tmp_path: Path) -> tuple[git.Repo, Path]:
    repo_path = tmp_path / "precision"
    repo = git.Repo.init(repo_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Precision Test")
        config.set_value("user", "email", "precision@example.test")
    return repo, repo_path


def _commit(repo: git.Repo, repo_path: Path, name: str, content: str) -> git.Commit:
    path = repo_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo.index.add([name])
    return repo.index.commit("fixture")


def test_literal_positive_and_reference_negative(tmp_path: Path) -> None:
    repo, repo_path = _repo(tmp_path)
    _commit(repo, repo_path, "config.env", "\n".join([
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
        "password=Literal_Password-9Qx!",
        "mysql://dbuser:FAKE_pass@db.example.test/app",
        "this.token=getToken()",
        "MVN_PASSWORD=$MVN_PASSWORD",
        "SPRING_PASSWORD=System.getenv(\"DB_PASSWORD\")",
        "jdbc:mysql://db.example.test/app",
        "password=ConfigValueXYZ",
        "password=application.password",
        "password=changeme",
    ]))

    lines = []
    for line_number, line in enumerate((repo_path / "config.env").read_text(encoding="utf-8").splitlines(), 1):
        lines.append({
            "commit_sha": "fake",
            "file_path": "config.env",
            "line_number": line_number,
            "added_line": line,
            "still_in_head": True,
            "git_lifecycle_state": "ACTIVE_HEAD",
        })
    findings = detect_lines(lines)
    real_lines = {
        item.line_number
        for item in findings
        if not item.is_false_positive and not item.suppression_reason
    }

    assert {1, 2, 3} <= real_lines
    assert not {4, 5, 6, 7, 8, 9, 10} & real_lines
    assert any(item.line_number in {5, 6, 8, 9} and item.suppression_reason == "variable reference" for item in findings)
    assert any(item.line_number == 10 and item.suppression_reason == "placeholder" for item in findings)


def test_dependency_and_generated_paths_are_counted_as_skipped(tmp_path: Path) -> None:
    repo, repo_path = _repo(tmp_path)
    (repo_path / "node_modules/pkg").mkdir(parents=True)
    (repo_path / "node_modules/pkg/index.js").write_text("password=FAKE_Passw0rd123\n", encoding="utf-8")
    (repo_path / "target").mkdir()
    (repo_path / "target/app.jar").write_bytes(b"\x00\x01")
    (repo_path / "docs").mkdir()
    (repo_path / "docs/package.md").write_text("password=changeme\n", encoding="utf-8")

    coverage = build_coverage(repo_path)
    reasons = coverage["skipped"]["by_reason"]
    assert "dependency_path" in reasons
    assert "generated_or_dependency_file" in reasons


def test_positive_secret_types_are_found_after_later_deletion(tmp_path: Path) -> None:
    repo, repo_path = _repo(tmp_path)
    fixture_path = repo_path / "credentials.env"
    fixture_path.write_text("\n".join([
        "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF",
        "-----BEGIN RSA PRIVATE KEY-----",
        "mysql://dbuser:FAKE_pass@db.example.test/app",
        "password=FAKE_Passw0rd123",
    ]), encoding="utf-8")
    (repo_path / "node_modules" / "pkg").mkdir(parents=True)
    (repo_path / "node_modules" / "pkg" / "settings.py").write_text(
        "password=FAKE_Passw0rd123", encoding="utf-8"
    )
    repo.index.add(["credentials.env", "node_modules/pkg/settings.py"])
    added_commit = repo.index.commit("synthetic secrets")

    fixture_path.unlink()
    repo.index.remove(["credentials.env"])
    repo.index.commit("remove synthetic secrets")

    findings = detect_lines(walk_history(repo_path))
    historical = {
        item.secret_type
        for item in findings
        if item.commit_sha == added_commit.hexsha and not item.is_false_positive
    }

    assert {"aws_access_key", "private_key", "mysql_uri", "generic_assignment"} <= historical
    assert not any(
        item.file_path.startswith("node_modules/")
        and not item.is_false_positive
        for item in findings
    )


def test_gitleaks_finds_positive_fixtures_in_deleted_history(tmp_path: Path) -> None:
    repo, repo_path = _repo(tmp_path)
    added_commit = _commit(repo, repo_path, "credentials.env", "\n".join([
        "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF",
        "-----BEGIN RSA PRIVATE KEY-----",
        "mysql://dbuser:FAKE_pass@db.example.test/app",
        "password=Literal_Password-9Qx!",
        "spring.datasource.password=SpringLiteral_9Qx!",
        "DB_PASSWORD=DatabaseLiteral-9Qx!",
    ]))
    (repo_path / "node_modules" / "pkg").mkdir(parents=True)
    (repo_path / "node_modules" / "pkg" / "settings.py").write_text(
        "password=FAKE_Passw0rd123", encoding="utf-8"
    )
    repo.index.add(["node_modules/pkg/settings.py"])
    repo.index.commit("add synthetic dependency fixture")
    (repo_path / "credentials.env").unlink()
    repo.index.remove(["credentials.env"])
    repo.index.commit("delete synthetic credential file")
    repo.close()

    findings = run_gitleaks(str(repo_path))
    observed = {
        (item["RuleID"], item["StartLine"])
        for item in findings
        if item["File"] == "credentials.env" and item["Commit"] == added_commit.hexsha
    }

    assert {
        ("aws-access-token", 1),
        ("secretguard-private-key", 2),
        ("secretguard-db-connection-uri", 3),
        ("secretguard-generic-assignment", 4),
        ("secretguard-db-password-assignment", 5),
        ("secretguard-db-password-assignment", 6),
    } <= observed
    assert not any(item["File"].startswith("node_modules/") for item in findings)
