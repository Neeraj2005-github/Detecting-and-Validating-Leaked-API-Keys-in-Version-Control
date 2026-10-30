from __future__ import annotations

import json
from pathlib import Path

import git

from backend.ml.detector import FEATURE_NAMES, detect_lines, extract_14_features, shannon_entropy
from backend.ml.shap_risk_scorer import score_findings
from backend.scanner.history_walker import walk_history
from backend.services.benchmark_engine import run_benchmark
from backend.services.fixture_generator import generate_fixture
from backend.services.o1_reproducer import run_reproduction
from backend.services.rotation_state_machine import rotate


def _repo(path: Path) -> git.Repo:
    repo = git.Repo.init(path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "CP1 Test")
        config.set_value("user", "email", "cp1@example.test")
    return repo


def _commit(repo: git.Repo, path: Path, content: str, message: str = "fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo.index.add([str(path.relative_to(Path(repo.working_tree_dir)))])
    repo.index.commit(message)


def test_o1_reproduction_verifies_history_and_head_absence() -> None:
    result = run_reproduction()
    assert result["status"] == "PASS"
    assert result["verification"]["secret_in_history"] is True
    assert result["verification"]["secret_in_working_tree"] is False
    assert result["verification"]["secret_recoverable"] is True


def test_o2_fixture_oracle_and_still_in_head_accuracy(tmp_path: Path) -> None:
    repo_path = tmp_path / "synthetic_repo_v1"
    oracle_path = tmp_path / "ground_truth_oracle.json"
    oracle = generate_fixture(repo_path, oracle_path)
    persisted = json.loads(oracle_path.read_text(encoding="utf-8"))
    assert persisted["entries"] == oracle["entries"]
    lines = list(walk_history(repo_path))
    assert any(line.still_in_head and line.file_path == "config/application.env" for line in lines)
    assert any(not line.still_in_head and line.file_path == "config/legacy.env" for line in lines)
    assert {"ACTIVE_HEAD", "DELETED_HISTORY", "BRANCH_TAG", "REWRITTEN"} <= {line.git_lifecycle_state for line in lines}


def test_entropy_features_xgboost_and_shap_payload(tmp_path: Path) -> None:
    assert shannon_entropy("aaaa") == 0
    assert shannon_entropy("abcd") == 2
    features = extract_14_features("AKIAIOSFODNN7EXAMPLE", "config/prod.env", "KEY=AKIAIOSFODNN7EXAMPLE")
    assert list(features) == FEATURE_NAMES
    findings = detect_lines([{
        "commit_sha": "test",
        "file_path": "config/prod.env",
        "line_number": 1,
        "added_line": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
        "still_in_head": True,
        "git_lifecycle_state": "ACTIVE_HEAD",
    }])
    assert findings and 0 <= findings[0].ml_probability <= 1
    report = score_findings(findings)
    assert report["findings"][0]["contributors"]
    assert 0 <= report["ndcg_at_5"] <= 1


def test_rotation_transitions_and_positive_mttr() -> None:
    success = rotate("cp1-success")
    failure = rotate("cp1-failure", force_failure=True)
    assert [item["state"] for item in success["transitions"]] == [
        "DETECTED", "SANDBOX_VALIDATING", "ROTATING_CREDENTIAL", "VERIFIED_SAFE"
    ]
    assert failure["state"] == "FAILED_ROLLBACK"
    assert success["mttr_ms"] > 0


def test_nt1_empty_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "empty")
    assert list(walk_history(repo.working_tree_dir)) == []


def test_nt2_ten_mb_single_line(tmp_path: Path) -> None:
    repo_path = tmp_path / "large"
    repo = _repo(repo_path)
    _commit(repo, repo_path / "bundle.js", "A" * (10 * 1024 * 1024), "large line")
    assert list(walk_history(repo_path))


def test_nt3_binary_file(tmp_path: Path) -> None:
    repo_path = tmp_path / "binary"
    repo = _repo(repo_path)
    binary = repo_path / "image.bin"
    binary.write_bytes(b"\x00\x01\x02secret")
    repo.index.add(["image.bin"])
    repo.index.commit("binary")
    lines = list(walk_history(repo_path))
    assert all(line.file_path != "image.bin" or "\x00" not in line.added_line for line in lines)


def test_nt4_detached_head(tmp_path: Path) -> None:
    repo_path = tmp_path / "detached"
    repo = _repo(repo_path)
    _commit(repo, repo_path / "a.txt", "token=AKIAIOSFODNN7EXAMPLE\n")
    repo.git.checkout("--detach", "HEAD")
    assert list(walk_history(repo_path))


def test_nt5_malformed_encoding(tmp_path: Path) -> None:
    repo_path = tmp_path / "encoding"
    repo = _repo(repo_path)
    malformed = repo_path / "bad.txt"
    malformed.write_bytes(b"\xff\xfe\x00\x81")
    repo.index.add(["bad.txt"])
    repo.index.commit("malformed encoding")
    assert list(walk_history(repo_path)) == []


def test_benchmark_generates_all_kpis_and_provenance(tmp_path: Path) -> None:
    repo_path = tmp_path / "synthetic_repo_v1"
    oracle_path = tmp_path / "oracle.json"
    generate_fixture(repo_path, oracle_path)
    report = run_benchmark(repo_path, oracle_path)
    assert len(report["approaches"]) == 4
    assert {item["name"] for item in report["approaches"]} == {
        "Baseline A: Regex + Entropy",
        "Baseline B: Gitleaks",
        "Baseline C: detect-secrets/trufflehog pattern baseline",
        "Our O2 Engine",
    }
    for approach in report["approaches"]:
        assert {"precision", "recall", "f1_score", "false_positive_rate", "scan_wall_clock_ms", "peak_rss_mb"} <= set(approach["metrics"])
    assert "tradeoff_analysis" in report
