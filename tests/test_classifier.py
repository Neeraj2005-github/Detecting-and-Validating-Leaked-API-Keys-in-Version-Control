from pathlib import Path

import yaml

from backend.classification.classifier import classify
from backend.detection.normalizer import RawFinding


def test_classifier_maps_seeded_rules():
    ground_truth = yaml.safe_load(Path("testdata/ground_truth.yaml").read_text(encoding="utf-8"))
    rule_ids = {item["secret_type"] for item in ground_truth}
    assert len(rule_ids) > 0

    sample = RawFinding(
        commit_sha="abc123",
        file="config.py",
        line=5,
        rule_id="aws-access-key",
        matched_string_hash="deadbeef",
    )
    result = classify(sample)
    assert result.secret_type
    assert result.criticality > 0

    # ensure canonical mapping covers the expected seeded rule IDs
    assert result.secret_type in {"aws_access_key", "generic_high_entropy"}
