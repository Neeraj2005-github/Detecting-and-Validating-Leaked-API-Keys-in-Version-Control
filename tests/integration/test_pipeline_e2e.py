from pathlib import Path

from src.shd.cli import run_pipeline
from src.shd.dataset import DatasetEntry
from tests.fixtures.make_synthetic_secret_repo import make_synthetic_secret_repo


def test_full_pipeline_on_synthetic_fixture(tmp_path: Path) -> None:
    repo_path, payload = make_synthetic_secret_repo(str(tmp_path))
    entry = DatasetEntry.model_validate(payload)
    findings = run_pipeline(repo_path)

    assert any(finding.secret_type == "aws_access_key" for finding in findings)
    assert any(finding.present_in_head is False for finding in findings)

    labeled = run_pipeline_with_manifest(repo_path, entry)

    assert any(finding.label_ground_truth for finding in labeled)
    assert all(finding.dataset_split == "reference" for finding in labeled)


def run_pipeline_with_manifest(repo_path: str, entry: DatasetEntry):
    from src.shd.cli import run_pipeline

    manifest_path = Path(repo_path).parent / "manifest.json"
    manifest_path.write_text(
        '{"repos": [' + entry.model_dump_json() + ']}',
        encoding="utf-8",
    )
    return run_pipeline(repo_path, str(manifest_path))