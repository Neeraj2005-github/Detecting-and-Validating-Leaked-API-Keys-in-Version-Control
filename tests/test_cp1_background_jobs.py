from __future__ import annotations

import time

from fastapi.testclient import TestClient

from shd.walker_api import app


def _wait_job(client: TestClient, job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = client.get(f"/api/cp1/jobs/{job_id}").json()
        if payload["status"] in {"done", "failed", "timed_out"}:
            return payload
        time.sleep(0.1)
    raise AssertionError("scan job did not reach a terminal state")


def test_cp1_scan_job_returns_done_result_and_stages(monkeypatch) -> None:
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
            json={"synthetic_fixture": True, "use_ai_filter": True},
        )
        assert started.status_code == 200
        job = started.json()
        assert job["status"] == "running"
        assert set(job["job_id"]) <= set("0123456789abcdef")

        terminal = _wait_job(client, job["job_id"])
        assert terminal["status"] == "done"
        assert terminal["result"]["summary"]["total"] >= 1
        assert terminal["result"]["coverage"]["completeness"] in {"complete", "incomplete"}
        assert terminal["result"]["result_explanation"]
        assert terminal["result"]["skipped_files"] == terminal["result"]["coverage"]["skipped"]["items"]
        assert {stage["name"] for stage in terminal["stages"]} == {
            "clone", "preflight", "scan", "parse", "filter", "dedupe",
            "mask", "lifecycle", "report",
        }
        scan_stage = next(stage for stage in terminal["stages"] if stage["name"] == "scan")
        assert "gitleaks_subprocess" in {sub["name"] for sub in scan_stage["sub_steps"]}


def test_cp1_filter_exception_is_sanitized_in_failed_job(monkeypatch) -> None:
    import shd.walker_api as walker_api

    def raising_filter(lines):
        raise RuntimeError("real internal exception text")

    monkeypatch.setattr(walker_api, "detect_lines", raising_filter)
    with TestClient(app) as client:
        started = client.post(
            "/api/cp1/scan",
            json={"synthetic_fixture": True, "use_ai_filter": True},
        )
        terminal = _wait_job(client, started.json()["job_id"])

    assert terminal["status"] == "failed"
    assert terminal["error"]["stage"] == "filter"
    assert "real internal" not in str(terminal["error"])


def test_empty_gitleaks_report_skips_python_history_walk(monkeypatch) -> None:
    import shd.walker_api as walker_api

    monkeypatch.setattr(walker_api, "run_gitleaks", lambda repo: [])

    def unexpected_history_walk(repo):
        raise AssertionError("an empty Gitleaks report must not trigger a second history scan")

    monkeypatch.setattr(walker_api, "walk_history", unexpected_history_walk)
    monkeypatch.setattr(walker_api, "save_cp1_artifact", lambda *args, **kwargs: None)
    with TestClient(app) as client:
        started = client.post(
            "/api/cp1/scan",
            json={"synthetic_fixture": True, "use_ai_filter": True},
        )
        terminal = _wait_job(client, started.json()["job_id"])

    assert terminal["status"] == "done"
    assert terminal["result"]["findings"] == []


def test_timed_out_job_returns_safe_partial_result() -> None:
    import uuid
    import shd.walker_api as walker_api

    job_id = "partial" + uuid.uuid4().hex
    partial_result = {
        "partial": True,
        "findings": [{"masked_value": "[REDACTED]", "file": "config.env", "line": 2, "commit": "abc123"}],
        "summary": {"total": 1},
    }
    with walker_api._scan_jobs_lock:
        walker_api._scan_jobs[job_id] = {
            "job_id": job_id,
            "status": "timed_out",
            "stage": "scan",
            "started_at": time.time(),
            "stages": [{"name": name, "status": "queued", "count": 0, "duration_ms": 0, "sub_steps": []} for name in walker_api.STAGE_NAMES],
            "result": partial_result,
            "error": {"stage": "scan", "reason": "timeout", "sub_step": "coverage_walk"},
        }
    try:
        payload = walker_api.cp1_scan_status(job_id)
    finally:
        with walker_api._scan_jobs_lock:
            walker_api._scan_jobs.pop(job_id, None)

    assert payload["status"] == "timed_out"
    assert payload["result"] == partial_result


def test_cp1_scan_stage_timeout_reports_sub_step(monkeypatch) -> None:
    import time
    import shd.walker_api as walker_api

    def slow_gitleaks(repo):
        time.sleep(0.1)
        return []

    monkeypatch.setattr(walker_api, "run_gitleaks", slow_gitleaks)
    monkeypatch.setitem(walker_api.STAGE_TIMEOUTS, "scan", 0.001)

    with TestClient(app) as client:
        started = client.post(
            "/api/cp1/scan",
            json={"synthetic_fixture": True, "use_ai_filter": True},
        )
        terminal = _wait_job(client, started.json()["job_id"])

    assert terminal["status"] == "timed_out"
    assert terminal["error"]["stage"] == "scan"
    assert terminal["error"]["reason"] == "timeout"
    assert terminal["error"]["sub_step"] == "gitleaks_subprocess"
