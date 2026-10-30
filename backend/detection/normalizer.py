import hashlib

from pydantic import BaseModel, Field

from backend.ml_filter.features import extract_features


class RawFinding(BaseModel):
    commit_sha: str
    file: str
    line: int
    rule_id: str
    matched_string_hash: str
    features: dict[str, int | float] = Field(default_factory=dict)
    masked_preview: str = ""


def _mask(secret: str) -> str:
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * max(4, len(secret) - 8)}{secret[-4:]}"


def normalize(gitleaks_raw_output: list[dict]) -> list[RawFinding]:
    """Map Gitleaks' native JSON field names (Commit, File, StartLine, RuleID,
    Secret) into RawFinding objects. Hash the Secret field immediately with
    sha256 and discard the plaintext — do not keep it in the RawFinding object
    or in any log line, per NFR-03."""
    normalized: list[RawFinding] = []
    for item in gitleaks_raw_output:
        if not isinstance(item, dict):
            continue
        secret = str(item.get("Secret") or item.get("Match") or "").strip().rstrip("\r\n")
        if not secret:
            continue
        file_path = str(item.get("File") or item.get("file") or "").strip()
        line_number = int(item.get("StartLine") or item.get("line") or 1)
        surrounding_line = str(item.get("Match") or item.get("match") or "")
        finding = RawFinding(
            commit_sha=str(item.get("Commit") or item.get("commit") or "").strip(),
            file=file_path,
            line=line_number,
            rule_id=str(item.get("RuleID") or item.get("rule_id") or "unknown").strip(),
            matched_string_hash=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            features=extract_features(secret, file_path, surrounding_line),
            masked_preview=_mask(secret),
        )
        normalized.append(finding)
    return normalized
