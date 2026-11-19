from pathlib import Path


def test_targeted_stored_data_uses_fake_markers():
    targets = [
        Path("fixtures/oracle_spec.yaml"),
        Path("data/o2_evaluation.json"),
        Path("backend/services/o1_reproducer.py"),
        Path("testdata/seed_repo.py"),
    ]
    for target in targets:
        text = target.read_text(encoding="utf-8")
        assert "AKIAIOSFODNN7EXAMPLE" not in text
        assert "ghp_abcdefghijklmnop" not in text
