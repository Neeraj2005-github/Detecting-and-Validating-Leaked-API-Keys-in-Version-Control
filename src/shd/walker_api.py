from __future__ import annotations

import json
import hashlib
import logging
import urllib.parse
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Literal

import git
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from .walker_db import (
    BlobRecordRow,
    FindingRow,
    HistoricalFindingRow,
    RepositoryRow,
    ScanRow,
    SessionLocal,
    check_database,
    get_blobs_for_commit,
    get_commits,
    get_deleted_blobs,
    get_historical_findings,
    ingest_repo,
    init_db,
    persist_source_scan,
)
from .walker import get_commit_details, validate_repository
from backend.pipeline import run_pipeline
from backend.evaluation import Classification
from backend.evaluation_metrics import evaluate
from backend.services.dependency_checker import check_dependencies
from backend.services.oracle_loader import load_oracle
from backend.ml.dataset_kappa import evaluate_kappa
from backend.ml.xgboost_rigour import run_rigour
from backend.ml.shap_risk_scorer import score_findings
from backend.ml.detector import detect_lines
from backend.scanner.history_walker import walk_history
from backend.services.benchmark_engine import run_benchmark
from backend.services.rotation_state_machine import rotate
from backend.services.artifact_store import save_cp1_artifact
from backend.services.fixture_generator import generate_fixture
from scripts.scan_public_repos_summary import build_summary

logger = logging.getLogger(__name__)
BASELINE_METRICS_PATH = Path(__file__).resolve().parents[2] / "reports" / "baseline_metrics.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
O1_REPRODUCTION_PATH = PROJECT_ROOT / "artifacts" / "o1_reproduction_log.json"
O1_CONTRACT_PATH = PROJECT_ROOT / "backend" / "data" / "o1_engineering_contract.json"
ROTATED_FINDINGS_PATH = PROJECT_ROOT / "artifacts" / "cp1_rotated_findings.json"
_rotated_findings: set[str] = set()
if ROTATED_FINDINGS_PATH.exists():
    try:
        stored_rotations = json.loads(ROTATED_FINDINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(stored_rotations, dict):
            stored_rotations = stored_rotations.get("finding_ids", [])
        _rotated_findings = set(stored_rotations)
    except (OSError, json.JSONDecodeError, TypeError):
        _rotated_findings = set()

app = FastAPI(title="Secret History Detector")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    """Provide a friendly landing response for the API root."""
    return {
        "service": "Detecting Secrets Across Version Control",
        "status": "ok",
        "frontend": "http://127.0.0.1:5173/vaultguard/home",
        "docs": "/docs",
        "health": "/health",
    }


class ScanRequest(BaseModel):
    repo_path: str
    repo_id: str
    analysis_mode: Literal["current", "history", "full"] = "full"


class RepositoryRequest(BaseModel):
    url: str


class CP1ScanRequest(BaseModel):
    repo_url: str | None = None
    synthetic_fixture: bool = True
    use_ai_filter: bool = True


class CP1RotateRequest(BaseModel):
    force_failure: bool = False


class APIRotateRequest(BaseModel):
    finding_id: str
    force_failure: bool = False


def _cp1_fixture_path() -> Path:
    return PROJECT_ROOT / "artifacts" / "synthetic_repo_v1"


def _cp1_repo_path(request: CP1ScanRequest) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if request.synthetic_fixture or not request.repo_url:
        return _cp1_fixture_path(), None
    value = _validate_repository_url(request.repo_url)
    if value.startswith(("http://", "https://", "git://", "git@", "ssh://")):
        temp_dir = tempfile.TemporaryDirectory(prefix="cp1-scan-")
        git.Repo.clone_from(value, temp_dir.name)
        return Path(temp_dir.name), temp_dir
    return Path(value).expanduser().resolve(), None


def _cp1_finding_payload(finding: object, shap_by_key: dict[tuple[str, int], dict[str, object]]) -> dict[str, object]:
    item = finding.as_dict()
    item.pop("feature_vector", None)
    item["risk_score"] = shap_by_key.get((str(item["file_path"]), int(item["line_number"])), {}).get("risk_score", 0)
    item["shap"] = shap_by_key.get((str(item["file_path"]), int(item["line_number"])), {}).get("contributors", [])
    item["lifecycle_badge"] = {
        "ACTIVE_HEAD": "Active in HEAD",
        "DELETED_HISTORY": "Deleted in History",
        "BRANCH_TAG": "Branch/Tag",
        "REWRITTEN": "Rewritten History",
    }.get(str(item.get("git_lifecycle_state")), str(item.get("git_lifecycle_state")))
    if str(item.get("fingerprint")) in _rotated_findings:
        item["status"] = "ROTATED_SAFE"
        item["lifecycle_badge"] = "Rotated & Safe"
        item["still_in_head"] = False
        item["risk_score"] = 0.0
        item["shap"] = []
    elif item.get("is_false_positive"):
        item["status"] = "SUPPRESSED_DECOY"
        item["lifecycle_badge"] = "Suppressed Decoy"
        item["risk_score"] = 0.0
    return item


def _validate_repository_url(value: str) -> str:
    url = value.strip()
    if not url:
        raise HTTPException(status_code=400, detail="repository URL is required")
    if url.startswith("git@"):
        return url
    parsed = urllib.parse.urlparse(url)
    is_remote_url = parsed.scheme.lower() in {"http", "https", "git", "ssh"} and bool(parsed.netloc)
    is_local_path = (
        url.startswith((".", "/", "~"))
        or "\\" in url
        or "/" in url
        or (len(url) >= 2 and url[1] == ":")
    )
    if not (is_remote_url or is_local_path):
        raise HTTPException(status_code=400, detail="repository URL is malformed")
    return url


class ScanResponse(BaseModel):
    scan_id: int
    analysis_mode: str
    blobs_written: int
    findings_count: int


class MetricsResponse(BaseModel):
    repositories: int
    scans: int
    commits_analyzed: int
    files_scanned: int
    historical_files_recovered: int
    secrets_detected: int
    current_secrets: int
    historical_secrets: int | None
    high_confidence_findings: int
    historical_findings: int
    total_findings: int
    true_secrets: int = 0
    false_positives: int = 0
    test_fixtures: int = 0
    unknown_findings: int = 0
    current_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0


class FindingResponse(BaseModel):
    id: int
    finding_id: str
    scan_id: int
    repository_id: str
    file_path: str
    line_number: int
    secret_type: str
    detector: str
    confidence: float | None
    secret_hash: str
    masked_preview: str
    status: str
    detector_name: str = "gitleaks"
    rule_id: str = "unknown"
    classification: str = "UNKNOWN"
    validation_status: str = "NOT_CHECKED"
    criticality: str = "UNKNOWN"
    features: dict[str, int | float] = {}
    ml_verdict: str = "NOT_AVAILABLE"
    detected: bool = True
    is_current: bool = True
    is_historical: bool = False
    commit_sha: str = ""
    masked_match: str = ""


class ScanSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: str
    files_discovered: int
    files_scanned: int
    files_skipped: int
    findings_count: int
    status: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int


class BlobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: str
    commit_hash: str
    commit_timestamp: datetime
    file_path: str
    blob_content: str
    is_head: bool
    change_type: str


class CommitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    commit_hash: str
    commit_timestamp: datetime
    message: str | None = None
    author: str | None = None
    parent_hash: str | None = None
    short_hash: str | None = None
    parents: list[str] = []


class CommitDetailsResponse(BaseModel):
    commit_hash: str
    message: str
    author: str
    commit_timestamp: datetime
    parent_hash: str | None
    short_hash: str | None = None
    parents: list[str] = []
    changed_files: list[dict[str, object]]


class HistoricalFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: str
    repository_id: str
    commit_hash: str
    commit_timestamp: datetime
    file_path: str
    line_number: int
    secret_type: str
    detector: str
    confidence: float
    secret_hash: str
    masked_preview: str
    status: str
    classification: str = "UNKNOWN"
    validation_status: str = "NOT_CHECKED"
    criticality: str = "UNKNOWN"
    features: dict[str, int | float] = {}
    ml_verdict: str = "NOT_AVAILABLE"
    is_current: bool = False
    is_historical: bool = True
    commit_message: str | None = None
    author: str | None = None
    first_seen_commit: str | None = None
    last_seen_commit: str | None = None
    removed_from_current_source: bool = True


def _finding_response(row: FindingRow) -> FindingResponse:
    confidence = row.confidence if row.ml_verdict != "NOT_AVAILABLE" else None
    return FindingResponse(
        id=row.id,
        finding_id=row.finding_id,
        scan_id=row.scan_id,
        repository_id=row.repository_id,
        file_path=row.file_path,
        line_number=row.line_number,
        secret_type=row.secret_type,
        detector="gitleaks",
        confidence=confidence,
        secret_hash=row.secret_hash,
        masked_preview=row.masked_preview,
        status=row.status,
        detector_name="gitleaks",
        rule_id=row.detector,
        classification=row.classification,
        validation_status=row.validation_status,
        criticality=row.criticality,
        features=row.features or {},
        ml_verdict=row.ml_verdict,
        detected=True,
        is_current=row.is_current,
        is_historical=row.is_historical,
        commit_sha=row.commit_sha,
        masked_match=row.masked_preview,
    )


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.on_event("startup")
def startup() -> None:
    init_db()
    if not (_cp1_fixture_path() / ".git").exists():
        generate_fixture()


def _read_json_file(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("O1 evidence file unavailable: path=%s error=%s", path, type(exc).__name__)
        raise HTTPException(status_code=503, detail="O1 evidence is not available") from exc


@app.get("/o1/reproduction")
def o1_reproduction() -> dict[str, object]:
    """Return the redacted, structured O1.1 reproduction artifact."""
    return _read_json_file(O1_REPRODUCTION_PATH)


@app.get("/o1/contract")
def o1_contract() -> dict[str, object]:
    """Return the frozen machine-readable O1 engineering contract."""
    return _read_json_file(O1_CONTRACT_PATH)


@app.get("/o1/dependencies")
def o1_dependencies() -> dict[str, object]:
    """Return live dependency and sandbox readiness status."""
    return check_dependencies()


@app.get("/o1/evidence")
def o1_evidence() -> dict[str, object]:
    """Return the complete O1 evidence bundle used by the React evidence view."""
    oracle = load_oracle()
    return {
        "reproduction": _read_json_file(O1_REPRODUCTION_PATH),
        "contract": _read_json_file(O1_CONTRACT_PATH),
        "dependencies": check_dependencies(),
        "oracle": {
            "version": oracle.version,
            "name": oracle.name,
            "entry_count": len(oracle.entries),
            "entries": [
                {
                    "id": entry.id,
                    "secret_type": entry.secret_type,
                    "is_secret": entry.is_secret,
                    "expected_lifecycle": entry.expected_lifecycle,
                }
                for entry in oracle.entries
            ],
        },
    }


@app.get("/cp1/extras")
def cp1_extras() -> dict[str, object]:
    """Run and return the five privacy-safe CP1 Extra evidence bundles."""
    kappa = evaluate_kappa()
    ablation = run_rigour()
    rotation = rotate("cp1-synthetic-credential")
    public_summary = build_summary()
    fixture_path = PROJECT_ROOT / "artifacts" / "synthetic_repo_v1"
    shap_report = {"status": "fixture unavailable"}
    if fixture_path.exists():
        shap_report = score_findings(detect_lines(walk_history(fixture_path)))
    return {
        "dataset_kappa": kappa,
        "xgboost_ablation": ablation,
        "rotation": rotation,
        "public_repo_summary": public_summary,
        "shap_risk": shap_report,
    }


@app.get("/o2/benchmark")
def o2_benchmark() -> dict[str, object]:
    """Run and return the O2.4/O2.5 head-to-head benchmark."""
    return run_benchmark()


@app.get("/api/cp1/overview")
def cp1_overview() -> dict[str, object]:
    """Return one structured overview payload for the CP1 workbench."""
    contract = _read_json_file(O1_CONTRACT_PATH)
    dependencies = check_dependencies()
    benchmark_path = PROJECT_ROOT / "artifacts" / "o2_benchmark_kpis.json"
    benchmark = _read_json_file(benchmark_path) if benchmark_path.exists() else run_benchmark()
    extras = cp1_extras()
    return {
        "status": "ready",
        "contract": contract,
        "reproduction": _read_json_file(O1_REPRODUCTION_PATH),
        "dependencies": dependencies,
        "kpis": benchmark,
        "extras": {
            "dataset_kappa": extras["dataset_kappa"],
            "xgboost_ablation": extras["xgboost_ablation"],
            "shap_risk": extras["shap_risk"],
            "rotation": extras["rotation"],
            "public_repo_summary": extras["public_repo_summary"],
        },
    }


@app.post("/api/cp1/scan")
def cp1_scan(request: CP1ScanRequest) -> dict[str, object]:
    """Scan a local/remote repository or the deterministic CP1 fixture."""
    repository, temporary = _cp1_repo_path(request)
    try:
        if not repository.exists():
            raise HTTPException(status_code=400, detail=f"repository does not exist: {repository}")
        history = list(walk_history(repository))
        findings = detect_lines(history)
        shap_report = score_findings(findings) if findings else {"findings": [], "ndcg_at_5": 0.0, "ndcg_at_10": 0.0}
        shap_by_key = {
            (str(item["file_path"]), int(item.get("line_number", 0))): item
            for item in shap_report.get("findings", [])
        }
        payload = [_cp1_finding_payload(item, shap_by_key) for item in findings]
        if not request.use_ai_filter:
            for item in payload:
                item["is_false_positive"] = False
        deduplicated: dict[tuple[str, str], dict[str, object]] = {}
        for item in payload:
            key = (
                str(item.get("fingerprint", "")),
                str(item.get("secret_type", "")),
            )
            previous = deduplicated.get(key)
            if previous is None or float(item.get("risk_score", 0)) > float(previous.get("risk_score", 0)):
                deduplicated[key] = item
        resolved = sorted(
            (item for item in deduplicated.values() if item.get("status") == "ROTATED_SAFE"),
            key=lambda item: str(item.get("file_path", "")),
        )
        filtered = sorted(
            (item for item in deduplicated.values() if item.get("is_false_positive")),
            key=lambda item: float(item.get("risk_score", 0)),
            reverse=True,
        )
        prioritized = sorted(
            (
                item for item in deduplicated.values()
                if not item.get("is_false_positive") and item.get("status") != "ROTATED_SAFE"
            ),
            key=lambda item: float(item.get("risk_score", 0)),
            reverse=True,
        )
        response = {
            "repository": str(repository),
            "fixture": repository == _cp1_fixture_path().resolve(),
            "findings": prioritized,
            "suppressed_findings": filtered,
            "resolved_findings": resolved,
            "summary": {
                "active_head": sum(
                    item["git_lifecycle_state"] == "ACTIVE_HEAD"
                    and item.get("status") != "ROTATED_SAFE"
                    for item in prioritized
                ),
                "historical": sum(item["git_lifecycle_state"] == "DELETED_HISTORY" for item in prioritized),
                "filtered": len(filtered),
                "total": len(prioritized),
            },
            "ndcg": {
                "at_5": shap_report.get("ndcg_at_5", 0.0),
                "at_10": shap_report.get("ndcg_at_10", 0.0),
            },
        }
        save_cp1_artifact("cp1_latest_scan", response, PROJECT_ROOT / "artifacts" / "cp1_latest_scan.json")
        return response
    except (ValueError, git.exc.GitCommandError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temporary is not None:
            temporary.cleanup()


@app.post("/api/scan")
def api_scan(request: CP1ScanRequest) -> dict[str, object]:
    """Compatibility alias for the primary frontend scan workflow."""
    return cp1_scan(request)


@app.post("/api/cp1/reproduce-o1")
def cp1_reproduce_o1() -> dict[str, object]:
    """Run O1.1 and return the redacted commit timeline and verification."""
    from backend.services.o1_reproducer import run_reproduction, save_artifacts

    result = run_reproduction()
    save_artifacts(result)
    return result


@app.post("/api/cp1/benchmark/run")
def cp1_benchmark_run() -> dict[str, object]:
    """Run the four-way benchmark on the shared synthetic fixture."""
    return run_benchmark()


@app.post("/api/cp1/rotate/{finding_id}")
def cp1_rotate(finding_id: str, request: CP1RotateRequest | None = None) -> dict[str, object]:
    """Execute the offline-safe four-step rotation state machine."""
    result = rotate(finding_id, force_failure=bool(request and request.force_failure))
    if result.get("state") == "VERIFIED_SAFE":
        _rotated_findings.add(finding_id)
        ROTATED_FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        ROTATED_FINDINGS_PATH.write_text(
            json.dumps(sorted(_rotated_findings), indent=2) + "\n",
            encoding="utf-8",
        )
        save_cp1_artifact(
            "cp1_rotated_findings",
            {"finding_ids": sorted(_rotated_findings)},
            ROTATED_FINDINGS_PATH,
        )
        result["finding_id"] = finding_id
        result["status"] = "ROTATED_SAFE"
    return result


@app.post("/api/rotate")
def api_rotate(request: APIRotateRequest) -> dict[str, object]:
    """Compatibility endpoint for clients that send the finding ID in JSON."""
    return cp1_rotate(request.finding_id, CP1RotateRequest(force_failure=request.force_failure))


@app.post("/scan", response_model=ScanResponse)
def scan(request: ScanRequest, session: Session = Depends(get_session)) -> ScanResponse:
    try:
        if not request.repo_path.startswith(("http://", "https://", "git://", "git@", "ssh://")):
            request.repo_path = validate_repository(request.repo_path)
        count = 0
        findings_count = 0
        scan_id = 0
        if request.analysis_mode in {"history", "full"}:
            count = ingest_repo(request.repo_path, request.repo_id, session)
            findings_count = session.scalar(
                select(func.count()).select_from(HistoricalFindingRow).where(
                    HistoricalFindingRow.repository_id == request.repo_id
                )
            ) or 0
        if request.analysis_mode in {"current", "full"}:
            scan_id, current_findings_count = persist_source_scan(request.repo_path, request.repo_id, session)
            findings_count += current_findings_count
    except ValueError as exc:
        session.rollback()
        logger.warning("Repository scan rejected: repository=%s error=%s", request.repo_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        session.rollback()
        logger.exception("Repository scan failed: repository=%s operation=scan", request.repo_id)
        raise HTTPException(status_code=400, detail="repository scan failed") from exc
    return ScanResponse(
        scan_id=scan_id,
        analysis_mode=request.analysis_mode,
        blobs_written=count,
        findings_count=findings_count,
    )


@app.get("/scans", response_model=list[ScanSummaryResponse])
def scans(session: Session = Depends(get_session)) -> list[ScanSummaryResponse]:
    rows = list(session.scalars(select(ScanRow).order_by(ScanRow.completed_at.desc())))
    return [
        ScanSummaryResponse(
            id=row.id,
            repository_id=row.repository_id,
            files_discovered=row.files_discovered,
            files_scanned=row.files_scanned,
            files_skipped=row.files_skipped,
            findings_count=row.findings_count,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            duration_ms=max(0, int((row.completed_at - row.started_at).total_seconds() * 1000)),
        )
        for row in rows
    ]


@app.get("/findings", response_model=list[FindingResponse])
def findings(repo_id: str | None = None, session: Session = Depends(get_session)) -> list[FindingResponse]:
    statement = select(FindingRow)
    if repo_id is not None:
        repository_key = repo_id
        if repo_id.isdigit():
            repository_key = session.scalar(
                select(RepositoryRow.repository_id).where(RepositoryRow.id == int(repo_id))
            )
            if repository_key is None:
                return []
        statement = statement.where(FindingRow.repository_id == repository_key)
    statement = statement.order_by(FindingRow.created_at.desc())
    rows = list(session.scalars(statement))
    return [_finding_response(row) for row in rows]


@app.post("/repositories")
def add_repository(request: RepositoryRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    url = _validate_repository_url(request.url)
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == url))
    if repository is None:
        repository = RepositoryRow(
            repository_id=url,
            path=url,
            created_at=datetime.utcnow(),
        )
        session.add(repository)
        session.commit()
        session.refresh(repository)
    return {"id": str(repository.id), "url": repository.path, "last_scan": None, "finding_count": 0}


@app.put("/repositories/{repository_id}")
def update_repository(repository_id: str, request: RepositoryRequest, session: Session = Depends(get_session)) -> dict[str, object]:
    try:
        repo_id = int(repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid repository id") from exc

    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.id == repo_id))
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")

    updated_url = _validate_repository_url(request.url)
    previous_repository_id = repository.repository_id
    repository.repository_id = updated_url
    repository.path = updated_url

    if previous_repository_id != updated_url:
        session.execute(update(FindingRow).where(FindingRow.repository_id == previous_repository_id).values(repository_id=updated_url))
        session.execute(update(ScanRow).where(ScanRow.repository_id == previous_repository_id).values(repository_id=updated_url))
        session.execute(update(HistoricalFindingRow).where(HistoricalFindingRow.repository_id == previous_repository_id).values(repository_id=updated_url))
        session.execute(update(BlobRecordRow).where(BlobRecordRow.repo_id == previous_repository_id).values(repo_id=updated_url))

    session.commit()
    session.refresh(repository)
    return {
        "id": str(repository.id),
        "url": repository.path,
        "last_scan": session.scalar(
            select(ScanRow.completed_at)
            .where(ScanRow.repository_id == repository.repository_id)
            .order_by(ScanRow.completed_at.desc())
            .limit(1)
        ),
        "finding_count": session.scalar(
            select(func.count()).select_from(FindingRow).where(FindingRow.repository_id == repository.repository_id)
        ) or 0,
    }


@app.delete("/repositories/{repository_id}", status_code=204)
def delete_repository(repository_id: str, session: Session = Depends(get_session)) -> Response:
    try:
        repo_id = int(repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid repository id") from exc

    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.id == repo_id))
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")

    repository_key = repository.repository_id
    session.execute(delete(FindingRow).where(FindingRow.repository_id == repository_key))
    session.execute(delete(HistoricalFindingRow).where(HistoricalFindingRow.repository_id == repository_key))
    session.execute(delete(BlobRecordRow).where(BlobRecordRow.repo_id == repository_key))
    session.execute(delete(ScanRow).where(ScanRow.repository_id == repository_key))
    session.execute(delete(RepositoryRow).where(RepositoryRow.id == repo_id))
    session.commit()
    return Response(status_code=204)


@app.get("/repositories")
def repositories(session: Session = Depends(get_session)) -> list[dict[str, object]]:
    rows = list(session.scalars(select(RepositoryRow).order_by(RepositoryRow.created_at.desc())))
    result = []
    for row in rows:
        last_scan = session.scalar(
            select(ScanRow.completed_at)
            .where(ScanRow.repository_id == row.repository_id)
            .order_by(ScanRow.completed_at.desc())
            .limit(1)
        )
        finding_count = session.scalar(
            select(func.count()).select_from(FindingRow).where(FindingRow.repository_id == row.repository_id)
        ) or 0
        result.append({
            "id": str(row.id),
            "repository_id": row.repository_id,
            "url": row.path,
            "last_scan": last_scan,
            "finding_count": finding_count,
        })
    return result


@app.post("/repositories/{repository_id}/scan")
def scan_repository(repository_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    try:
        repository = session.scalar(select(RepositoryRow).where(RepositoryRow.id == int(repository_id)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid repository id") from exc
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        pipeline_findings = run_pipeline(repository.path)
        session.execute(delete(FindingRow).where(FindingRow.repository_id == repository.repository_id))
        completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        scan = ScanRow(
            repository_id=repository.repository_id,
            started_at=started_at,
            completed_at=completed_at,
            files_discovered=0,
            files_scanned=0,
            files_skipped=0,
            findings_count=len(pipeline_findings),
            status="completed",
        )
        session.add(scan)
        session.flush()
        session.add_all([
            FindingRow(
                finding_id=hashlib.sha256(
                    f"{repository.repository_id}:{finding.get('commit_sha')}:{finding.get('file')}:{finding.get('line')}".encode()
                ).hexdigest(),
                scan_id=scan.id,
                repository_id=repository.repository_id,
                file_path=str(finding.get("file", "")),
                line_number=int(finding.get("line", 1)),
                secret_type=str(finding.get("secret_type", "generic_high_entropy")),
                detector=str(finding.get("rule_id", "gitleaks")),
                confidence=float(finding.get("ml_confidence") or 0.0),
                secret_hash=str(finding.get("secret_hash", "")),
                masked_preview=str(finding.get("masked_preview", "")),
                status="open",
                created_at=completed_at,
                classification=str(finding.get("classification", "UNKNOWN")),
                validation_status=str(finding.get("validation_status", "NOT_CHECKED")),
                criticality=str(finding.get("criticality_level", "UNKNOWN")),
                features=dict(finding.get("features", {})),
                ml_verdict=str(finding.get("ml_verdict", "NOT_AVAILABLE")),
                is_current=bool(finding.get("is_current", True)),
                is_historical=bool(finding.get("is_historical", False)),
                commit_sha=str(finding.get("commit_sha", "working-tree")),
            )
            for finding in pipeline_findings
        ])
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("Repository scan failed: repository=%s", repository.repository_id)
        raise HTTPException(status_code=400, detail="repository scan failed") from exc

    return {
        "repository_id": repository.repository_id,
        "scan_id": scan.id,
        "last_scan": completed_at,
        "finding_count": len(pipeline_findings),
    }


@app.get("/metrics", response_model=MetricsResponse)
def metrics(session: Session = Depends(get_session)) -> MetricsResponse:
    commit_rows = session.execute(select(BlobRecordRow.repo_id, BlobRecordRow.commit_hash)).all()
    current_hashes = set(session.scalars(select(FindingRow.secret_hash)))
    historical_hashes = set(session.scalars(select(HistoricalFindingRow.secret_hash)))
    historical_findings = session.scalar(select(func.count()).select_from(HistoricalFindingRow)) or 0
    classification_rows = list(session.scalars(select(FindingRow))) + list(session.scalars(select(HistoricalFindingRow)))
    classification_counts = {
        value: sum(row.classification == value for row in classification_rows)
        for value in Classification
    }
    return MetricsResponse(
        repositories=session.scalar(select(func.count()).select_from(RepositoryRow)) or 0,
        scans=session.scalar(select(func.count()).select_from(ScanRow)) or 0,
        commits_analyzed=len({(repo_id, commit_hash) for repo_id, commit_hash in commit_rows}),
        files_scanned=session.scalar(select(func.coalesce(func.sum(ScanRow.files_scanned), 0))) or 0,
        historical_files_recovered=session.scalar(
            select(func.count(func.distinct(BlobRecordRow.file_path)))
            .select_from(BlobRecordRow)
            .where(BlobRecordRow.is_head.is_(False))
        ) or 0,
        secrets_detected=len(current_hashes | historical_hashes),
        current_secrets=len(current_hashes),
        historical_secrets=len(historical_hashes),
        high_confidence_findings=(session.scalar(
            select(func.count()).select_from(FindingRow).where(FindingRow.confidence >= 0.8)
        ) or 0) + (session.scalar(
            select(func.count()).select_from(HistoricalFindingRow).where(HistoricalFindingRow.confidence >= 0.8)
        ) or 0),
        historical_findings=historical_findings,
        total_findings=(session.scalar(select(func.count()).select_from(FindingRow)) or 0) + historical_findings,
        true_secrets=classification_counts[Classification.TRUE_SECRET],
        false_positives=classification_counts[Classification.FALSE_POSITIVE],
        test_fixtures=classification_counts[Classification.TEST_FIXTURE],
        unknown_findings=classification_counts[Classification.UNKNOWN] + classification_counts[Classification.EXAMPLE_DOCUMENTATION],
        current_findings=session.scalar(select(func.count()).select_from(FindingRow)) or 0,
        high_findings=sum(row.criticality == "HIGH" for row in classification_rows),
        medium_findings=sum(row.criticality == "MEDIUM" for row in classification_rows),
        low_findings=sum(row.criticality == "LOW" for row in classification_rows),
    )


@app.get("/metrics/summary")
def metrics_summary(repo_id: str | None = None, session: Session = Depends(get_session)) -> dict[str, object]:
    if repo_id is None:
        return metrics(session).model_dump()
    current_rows = list(session.scalars(select(FindingRow).where(FindingRow.repository_id == repo_id)))
    historical_rows = list(session.scalars(select(HistoricalFindingRow).where(HistoricalFindingRow.repository_id == repo_id)))
    rows = current_rows + historical_rows
    counts = {value: sum(row.classification == value for row in rows) for value in Classification}
    return {
        "repositories": 1 if rows else 0,
        "scans": len({row.scan_id for row in current_rows}),
        "commits_analyzed": len({row.commit_hash for row in historical_rows}),
        "files_scanned": 0,
        "historical_files_recovered": len({row.file_path for row in historical_rows}),
        "secrets_detected": len({row.secret_hash for row in rows}),
        "current_secrets": len({row.secret_hash for row in current_rows}),
        "historical_secrets": len({row.secret_hash for row in historical_rows}),
        "high_confidence_findings": sum((row.confidence or 0) >= 0.8 for row in rows),
        "historical_findings": len(historical_rows),
        "total_findings": len(rows),
        "true_secrets": counts[Classification.TRUE_SECRET],
        "false_positives": counts[Classification.FALSE_POSITIVE],
        "test_fixtures": counts[Classification.TEST_FIXTURE],
        "unknown_findings": counts[Classification.UNKNOWN] + counts[Classification.EXAMPLE_DOCUMENTATION],
        "current_findings": len(current_rows),
        "high_findings": sum(row.criticality == "HIGH" for row in rows),
        "medium_findings": sum(row.criticality == "MEDIUM" for row in rows),
        "low_findings": sum(row.criticality == "LOW" for row in rows),
    }


@app.get("/metrics/baseline")
def baseline_metrics(response: Response) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    try:
        report = evaluate()
    except (OSError, ValueError, RuntimeError) as exc:
        return {
            "evaluation_valid": False,
            "evaluation_error": f"Evaluation unavailable: {exc}",
            "dataset_size": 0,
            "test_set_size": 0,
        }
    BASELINE_METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


@app.get("/repos/{repo_id}/commits", response_model=list[CommitResponse])
def commits(repo_id: str, session: Session = Depends(get_session)) -> list[CommitResponse]:
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == repo_id))
    rows = get_commits(repo_id, session)
    if repository is None:
        return []
    result = []
    for row in rows:
        try:
            details = get_commit_details(repository.path, row.commit_hash)
        except Exception:
            details = {}
        result.append(
            CommitResponse(
                commit_hash=row.commit_hash,
                commit_timestamp=row.commit_timestamp,
                message=details.get("message"),
                author=details.get("author"),
                parent_hash=details.get("parent_hash"),
                short_hash=details.get("short_hash"),
                parents=details.get("parents", []),
            )
        )
    return result


@app.get("/repos/{repo_id}/commits/{commit_hash}", response_model=CommitDetailsResponse)
def commit_details(repo_id: str, commit_hash: str, session: Session = Depends(get_session)) -> CommitDetailsResponse:
    repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == repo_id))
    if repository is None:
        raise HTTPException(status_code=404, detail="repository not found")
    try:
        return CommitDetailsResponse(**get_commit_details(repository.path, commit_hash))
    except (git.BadName, ValueError, OSError) as exc:
        raise HTTPException(status_code=404, detail="commit not found") from exc


@app.get("/findings/{finding_id}", response_model=FindingResponse)
def finding_detail(finding_id: str, session: Session = Depends(get_session)) -> FindingResponse:
    row = session.scalar(select(FindingRow).where(FindingRow.finding_id == finding_id))
    if row is None:
        raise HTTPException(status_code=404, detail="finding not found")
    return FindingResponse.model_validate(row, from_attributes=True)


@app.get("/historical-findings", response_model=list[HistoricalFindingResponse])
def historical_findings(
    repo_id: str | None = None,
    session: Session = Depends(get_session),
) -> list[HistoricalFindingResponse]:
    result = []
    for row in get_historical_findings(repo_id, session):
        repository = session.scalar(select(RepositoryRow).where(RepositoryRow.repository_id == row.repository_id))
        details = {}
        if repository is not None:
            try:
                details = get_commit_details(repository.path, row.commit_hash)
            except Exception:
                details = {}
        result.append(HistoricalFindingResponse(
            id=row.id,
            finding_id=row.finding_id,
            repository_id=row.repository_id,
            commit_hash=row.commit_hash,
            commit_timestamp=row.commit_timestamp,
            file_path=row.file_path,
            line_number=row.line_number,
            secret_type=row.secret_type,
            detector=row.detector,
            confidence=row.confidence,
            secret_hash=row.secret_hash,
            masked_preview=row.masked_preview,
            status=row.status,
            classification=row.classification,
            validation_status=row.validation_status,
            criticality=row.criticality,
            features=row.features or {},
            ml_verdict=row.ml_verdict,
            is_current=False,
            is_historical=True,
            commit_message=details.get("message"),
            author=details.get("author"),
            first_seen_commit=row.commit_hash,
            last_seen_commit=row.commit_hash,
            removed_from_current_source=True,
        ))
    return result


@app.get("/repos/{repo_id}/commits/{commit_hash}/blobs", response_model=list[BlobResponse])
def commit_blobs(repo_id: str, commit_hash: str, session: Session = Depends(get_session)) -> list[BlobRecordRow]:
    return get_blobs_for_commit(repo_id, commit_hash, session)


@app.get("/repos/{repo_id}/deleted-blobs", response_model=list[BlobResponse])
def deleted_blobs(repo_id: str, session: Session = Depends(get_session)) -> list[BlobRecordRow]:
    return get_deleted_blobs(repo_id, session)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        check_database()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "db": "ok"}
