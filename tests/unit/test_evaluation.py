from backend.evaluation import Classification, ValidationStatus, classify_path, criticality_level
from backend.evaluation_metrics import _metrics


def test_fixture_classification_is_explicit_and_not_validity():
    assert classify_path("tests/test_config.py") == Classification.TEST_FIXTURE
    assert classify_path("testdata/seed_repo.py") == Classification.TEST_FIXTURE
    assert classify_path("docs/example.md") == Classification.EXAMPLE_DOCUMENTATION
    assert classify_path("src/config.py") == Classification.UNKNOWN


def test_fixture_criticality_is_low_without_validation():
    assert criticality_level(
        secret_type="aws_access_key",
        confidence=1.0,
        classification=Classification.TEST_FIXTURE,
        is_current=True,
        is_historical=False,
        validation_status=ValidationStatus.NOT_CHECKED,
    ) == "LOW"


def test_metric_calculation_has_confusion_counts():
    result = _metrics([True, True, False, False], [True, False, True, False])
    assert result["tp"] == 1
    assert result["fp"] == 1
    assert result["fn"] == 1
    assert result["tn"] == 1
    assert result["precision"] == 0.5
    assert result["recall"] == 0.5
    assert result["f1"] == 0.5
    assert result["false_positive_rate"] == 0.5