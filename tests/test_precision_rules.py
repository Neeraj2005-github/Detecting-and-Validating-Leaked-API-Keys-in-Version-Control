from __future__ import annotations

from pathlib import Path

import git

from backend.ml.detector import detect_lines
from backend.services.coverage import build_coverage


def _repo(tmp_path: Path) -> tuple[git.Repo, Path]:
    repo_path = tmp_path / "precision"
    repo = git.Repo.init(repo_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Precision Test")
        config.set_value("user", "email", "precision@example.test")
    return repo, repo_path


def _commit(repo: git.Repo, repo_path: Path, name: str, content: str) -> None:
    path = repo_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo.index.add([name])
    repo.index.commit("fixture")


def test_literal_positive_and_reference_negative(tmp_path: Path) -> None:
    repo, repo_path = _repo(tmp_path)
    _commit(repo, repo_path, "config.env", "\n".join([
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
        "password=FAKE_Passw0rd123",
        "mysql://dbuser:FAKE_pass@db.example.test/app",
        "this.token=getToken()",
        "MVN_PASSWORD=$MVN_PASSWORD",
        "SPRING_PASSWORD=System.getenv(\"DB_PASSWORD\")",
        "jdbc:mysql://db.example.test/app",
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
    types = [(item.file_path, item.secret_type, item.is_false_positive, item.suppression_reason) for item in findings]

    assert any(item.secret_type in {"aws_access_key", "generic_assignment", "mysql_uri"} for item in findings)
    assert not any("this.token" in str(line) and item.suppression_reason == "" for line in [] for item in findings)
    assert any(item.suppression_reason == "variable reference" for item in findings)


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
