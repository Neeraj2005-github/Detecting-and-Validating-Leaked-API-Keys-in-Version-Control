from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append_audit(path: str | Path, actor: str, action: str, finding_id: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    audit_path = Path(path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if audit_path.exists():
        entries = json.loads(audit_path.read_text(encoding="utf-8"))
    previous = entries[-1]["entry_hash"] if entries else "0" * 64
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "finding_id": finding_id,
        "details": details or {},
        "previous_hash": previous,
    }
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
    entry["entry_hash"] = hashlib.sha256(canonical).hexdigest()
    entries.append(entry)
    audit_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    return entry


def verify_chain(path: str | Path) -> bool:
    audit_path = Path(path)
    if not audit_path.exists():
        return True
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    previous = "0" * 64
    for entry in entries:
        saved_hash = entry.pop("entry_hash", None)
        entry["previous_hash"] = previous
        canonical = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if saved_hash != hashlib.sha256(canonical).hexdigest():
            return False
        previous = saved_hash
    return True
