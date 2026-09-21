from pathlib import Path

import pytest

from backend.pipeline import run_pipeline


def test_run_pipeline_seeded_repo():
    repo_path = Path("testdata/seeded_repo")
    if not repo_path.exists():
        pytest.skip("seeded repo has not been generated yet")

    results = run_pipeline(str(repo_path))
    assert isinstance(results, list)
    assert 10 <= len(results) <= 20
