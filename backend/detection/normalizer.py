import hashlib

from pydantic import BaseModel


class RawFinding(BaseModel):
    commit_sha: str
    file: str
    line: int
    rule_id: str
    matched_string_hash: str


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
        finding = RawFinding(
            commit_sha=str(item.get("Commit") or item.get("commit") or "").strip(),
            file=str(item.get("File") or item.get("file") or "").strip(),
            line=int(item.get("StartLine") or item.get("line") or 1),
            rule_id=str(item.get("RuleID") or item.get("rule_id") or "unknown").strip(),
            matched_string_hash=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
        )
        normalized.append(finding)
    return normalized
