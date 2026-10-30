from __future__ import annotations

from pathlib import Path

from backend.ml.detector import FEATURE_NAMES, detect_lines, extract_14_features
from backend.scanner.history_walker import walk_history
from backend.services.fixture_generator import generate_fixture


def test_fixture_walker_and_detector_cover_o2_lifecycles(tmp_path: Path) -> None:
    fixture_path = tmp_path / "synthetic_repo_v1"
    oracle_path = tmp_path / "ground_truth_oracle.json"
    oracle = generate_fixture(fixture_path, oracle_path)
    assert oracle["expected_labels"] == {"TP": 6, "FP_DECOY": 4}
    assert len({entry["commit_sha"] for entry in oracle["entries"]}) >= 4

    lines = list(walk_history(fixture_path))
    assert lines
    assert {"ACTIVE_HEAD", "DELETED_HISTORY", "BRANCH_TAG", "REWRITTEN"} <= {
        line.git_lifecycle_state for line in lines
    }
    findings = detect_lines(lines)
    assert findings
    assert any(item.still_in_head for item in findings)
    assert any(not item.still_in_head for item in findings)
    assert all(len(item.feature_vector) == 14 for item in findings)
    assert all("added_line" not in item.as_dict() for item in lines)


def test_feature_math_and_safe_oracle_shape(tmp_path: Path) -> None:
    features = extract_14_features(
        "AKIAIOSFODNN7EXAMPLE",
        "config/prod.env",
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
    )
    assert list(features) == FEATURE_NAMES
    assert features["entropy"] > 0
    assert 0 <= features["normalized_entropy"] <= 1
    assert features["positive_keyword_proximity"] > 0
    assert features["assignment_operator_present"] == 1
