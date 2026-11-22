from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import time

import git
from fastapi.testclient import TestClient

from backend.services.exposure_lifecycle import (
    build_exposure_lifecycle,
    calculate_exposure_risk,
)
from backend.stubs.risk_scoring import compute_risk_score
from shd.walker_api import _cp1_finding_payload, app


def _repo(path: Path) -> git.Repo:
    repo = git.Repo.init(path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Lifecycle Test")
        config.set_value("user", "email", "lifecycle@example.test")
    return repo


def _commit(repo: git.Repo, path: Path, content: str, message: str, date: datetime) -> git.Commit:
    (path / "credentials.env").write_text(content, encoding="utf-8")
    repo.index.add(["credentials.env"])
    return repo.index.commit(message, author_date=date, commit_date=date)


def _exposure(repo: git.Repo, commit: git.Commit, secret: str, now: datetime):
    raw = [{
        "File": "credentials.env",
        "RuleID": "secretguard-generic-assignment",
        "Commit": commit.hexsha,
        "StartLine": 1,
        "Secret": secret,
    }]
    normalized = [SimpleNamespace(matched_string_hash="synthetic-fingerprint")]
    reachable = set(repo.git.rev_list("--all").splitlines())
    return build_exposure_lifecycle(
        repo,
        raw,
        normalized,
        reachable_commit_shas=reachable,
        local_commit_shas=reachable,
        now=now,
    )[("credentials.env", 1, commit.hexsha)]


def test_deleted_secret_reports_exposure_interval_and_recoverability(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first = _commit(
        repo,
        tmp_path,
        "password=LifecycleExample!93Qx",
        "add synthetic credential",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    removed = _commit(
        repo,
        tmp_path,
        "setting=clean",
        "remove synthetic credential",
        datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    exposure = _exposure(
        repo,
        first,
        "LifecycleExample!93Qx",
        datetime(2024, 1, 3, tzinfo=timezone.utc),
    )

    assert exposure["first_seen_commit"] == first.hexsha
    assert exposure["last_seen_commit"] == first.hexsha
    assert exposure["removed_in_commit"] == removed.hexsha
    assert exposure["days_exposed"] == 1.0
    assert exposure["lifecycle_status"] == "DELETED_BUT_RECOVERABLE"
    assert exposure["recoverable_from_fresh_clone"] is True
    assert exposure["recoverable_from_local_objects"] is False
    repo.close()


def test_active_secret_and_local_only_recoverability_are_distinguished(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base = _commit(
        repo, tmp_path, "setting=clean", "base",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    repo.git.checkout("-b", "local-only")
    local = _commit(
        repo,
        tmp_path,
        "password=LocalOnlyExample!93Qx",
        "add local-only credential",
        datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    repo.git.checkout("main")
    repo.git.branch("-D", "local-only")
    raw = [{
        "File": "credentials.env",
        "RuleID": "secretguard-generic-assignment",
        "Commit": local.hexsha,
        "StartLine": 1,
        "Secret": "LocalOnlyExample!93Qx",
    }]
    local_exposure = build_exposure_lifecycle(
        repo,
        raw,
        [SimpleNamespace(matched_string_hash="local-fingerprint")],
        reachable_commit_shas={base.hexsha},
        local_commit_shas={base.hexsha, local.hexsha},
        now=datetime(2024, 1, 3, tzinfo=timezone.utc),
    )[("credentials.env", 1, local.hexsha)]
    assert local_exposure["lifecycle_status"] == "UNREACHABLE_LOCAL_ONLY"
    assert local_exposure["recoverable_from_fresh_clone"] is False
    assert local_exposure["recoverable_from_local_objects"] is True
    repo.close()

    active_repo = _repo(tmp_path / "active")
    active_path = tmp_path / "active"
    active = _commit(
        active_repo,
        active_path,
        "password=ActiveExample!93Qx",
        "active synthetic credential",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    active_exposure = _exposure(
        active_repo,
        active,
        "ActiveExample!93Qx",
        datetime(2024, 1, 3, tzinfo=timezone.utc),
    )
    assert active_exposure["lifecycle_status"] == "ACTIVE_IN_HEAD"
    assert active_exposure["recoverable_from_fresh_clone"] is True
    assert active_exposure["removed_in_commit"] is None
    active_repo.close()


def test_risk_score_is_monotonic_and_exposes_weighted_factors() -> None:
    baseline = {
        "secret_type": "generic_assignment",
        "lifecycle_status": "UNREACHABLE_LOCAL_ONLY",
        "days_exposed": 0,
        "public_repository": False,
        "features": {"entropy": 1.0},
    }
    base_score, breakdown = calculate_exposure_risk(baseline)
    variants = [
        {**baseline, "lifecycle_status": "ACTIVE_IN_HEAD"},
        {**baseline, "secret_type": "private_key"},
        {**baseline, "days_exposed": 365},
        {**baseline, "public_repository": True},
        {**baseline, "features": {"entropy": 4.0}},
    ]

    assert all(calculate_exposure_risk(item)[0] > base_score for item in variants)
    assert breakdown["score"] == base_score
    assert compute_risk_score(baseline) == base_score
    assert set(breakdown["terms"]) == {
        "lifecycle", "secret_severity", "exposure_duration", "public_repository", "entropy",
    }


def test_fast_scan_payload_does_not_return_unmasked_added_lines() -> None:
    secret = "SyntheticValue!93Qx"
    payload = _cp1_finding_payload(
        {
            "file_path": "credentials.env",
            "line_number": 1,
            "commit_sha": "synthetic-commit",
            "secret_type": "generic_assignment",
            "fingerprint": "synthetic-fingerprint",
            "added_line": f"password={secret}",
            "masked_match": "Syn***********3Qx",
        },
        {},
    )

    assert "added_line" not in payload
    assert secret not in json.dumps(payload)


def test_scan_response_exposes_lifecycle_risk_and_rotation_playbook(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_path = tmp_path / "scan-repo"
    repo = _repo(repo_path)
    secret = "LifecycleExample!93Qx"
    first = _commit(
        repo,
        repo_path,
        f"password={secret}",
        "add synthetic credential",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    removed = _commit(
        repo,
        repo_path,
        "setting=clean",
        "remove synthetic credential",
        datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    repo.close()

    import shd.walker_api as walker_api
    monkeypatch.setattr(walker_api, "save_cp1_artifact", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        walker_api,
        "score_findings",
        lambda findings: {"findings": [], "ndcg_at_5": 0.0, "ndcg_at_10": 0.0},
    )
    with TestClient(app) as client:
        started = client.post(
            "/api/cp1/scan",
            json={
                "repo_url": str(repo_path),
                "synthetic_fixture": False,
                "use_ai_filter": False,
                "public_repo": True,
            },
        )
        job_id = started.json()["job_id"]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            job = client.get(f"/api/cp1/jobs/{job_id}").json()
            if job["status"] in {"done", "failed", "timed_out"}:
                break
            time.sleep(0.1)

    assert job["status"] == "done"
    result = job["result"]
    finding = next(item for item in result["findings"] if item["secret_type"] == "generic_assignment")
    assert finding["first_seen_commit"] == first.hexsha
    assert finding["last_seen_commit"] == first.hexsha
    assert finding["removed_in_commit"] == removed.hexsha
    assert finding["lifecycle_status"] == "DELETED_BUT_RECOVERABLE"
    assert finding["recoverable_from_fresh_clone"] is True
    assert finding["risk_breakdown"]["terms"]["public_repository"]["factor"] == 1.0
    assert finding["remediation_playbook"]["rotation_status"] == "ROTATION_NOT_VERIFIED"
    assert "git filter-repo --path 'credentials.env' --invert-paths" in finding["remediation_playbook"]["history_rewrite_commands"]
    assert secret not in json.dumps(result)


def test_rotation_only_resolves_after_mock_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import shd.walker_api as walker_api
    import backend.services.rotation_state_machine as rotation_state_machine

    monkeypatch.setattr(walker_api, "_rotated_findings", set())
    monkeypatch.setattr(walker_api, "ROTATED_FINDINGS_PATH", tmp_path / "rotated.json")
    monkeypatch.setattr(rotation_state_machine, "save_cp1_artifact", lambda *args, **kwargs: None)

    failed = walker_api.cp1_rotate(
        "synthetic-failure",
        walker_api.CP1RotateRequest(force_failure=True),
    )
    assert failed["state"] == "VALIDITY_UNKNOWN"
    assert failed.get("status") != "VERIFIED_REVOKED"

    verified = walker_api.cp1_rotate("synthetic-success")
    assert verified["state"] == "VERIFIED_REVOKED"
    assert verified["status"] == "VERIFIED_REVOKED"
    assert "synthetic-success" in walker_api._rotated_findings
