from pathlib import Path

import pytest

from shd.source_scanner import scan_source


def test_scan_source_finds_live_fake_key_and_redacts_value(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "config.py").write_text(
        "AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'\n",
        encoding="utf-8",
    )
    (tmp_path / "notes.md").write_text("API_KEY=YOUR_API_KEY\n", encoding="utf-8")
    (tmp_path / "binary.dat").write_bytes(b"prefix\x00secret")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text(
        "AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'\n", encoding="utf-8"
    )

    result = scan_source(str(tmp_path))

    assert result.files_discovered == 3
    assert result.files_scanned == 1
    assert result.files_skipped == 2
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.file_path == "config.py"
    assert finding.secret_type == "aws_access_key"
    assert finding.masked_preview != "AKIAIOSFODNN7EXAMPLE"
    assert finding.secret_hash != "AKIAIOSFODNN7EXAMPLE"


def test_scan_source_requires_git_repository(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=".git"):
        scan_source(str(tmp_path))
