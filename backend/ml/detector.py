"""O2 multi-stage detector: patterns, entropy/context features, and ML filter."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

import joblib

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "backend" / "ml" / "detector_model.pkl"
MODEL_META_PATH = ROOT / "backend" / "ml" / "detector_model.json"
FINGERPRINT_SALT = os.getenv("O2_FINGERPRINT_SALT", "secretguard-o2-local-synthetic-salt")
FEATURE_NAMES = [
    "entropy", "normalized_entropy", "token_length", "digit_ratio",
    "uppercase_ratio", "lowercase_ratio", "symbol_ratio",
    "transition_frequency", "positive_keyword_proximity",
    "negative_keyword_proximity", "file_path_risk_score", "is_base64_encoded",
    "assignment_operator_present", "line_length",
]

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("mysql_uri", re.compile(r"\b(?:mysql|postgres(?:ql)?|jdbc:mysql|jdbc:postgresql)://[^\s'\"<>]+", re.I)),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("stripe_token", re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{12,}\b")),
    ("generic_assignment", re.compile(r"(?i)(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|db_pass)\s*(?:=|:=|:)\s*['\"]?([A-Za-z0-9_+/=.$:@!#%\-]{12,})")),
)
BASE64_RE = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{20,}={0,2}(?![A-Za-z0-9+/])")
POSITIVE_KEYWORDS = ("password", "secret", "key", "token", "auth", "prod", "db_pass")
NEGATIVE_KEYWORDS = ("example", "test", "mock", "sample", "uuid", "hash", "todo", "placeholder")
_PLACEHOLDER_VALUES = {
    "your_key_here",
    "your_password",
    "your_secret_here",
    "replace_me",
    "changeme",
    "example",
}
_FRONTEND_BOILERPLATE = (
    "localstorage.getitem",
    "localstorage.setitem",
    "e.target.value",
    "event.target.value",
    "process.env.",
)


def _heuristic_false_positive(token: str, file_path: str, line: str) -> bool:
    """Classify known boilerplate before the learned probability is applied."""
    normalized_path = file_path.lower().replace("\\", "/")
    normalized_line = line.lower()
    normalized_token = token.strip("'\" `").lower()
    entropy = shannon_entropy(token)
    example_path = (
        normalized_path.endswith((".env.example", ".env.sample", ".sample"))
        or "/docs/" in f"/{normalized_path}"
        or normalized_path.startswith(("docs/", "documentation/"))
    )
    boilerplate = any(value in normalized_line for value in _FRONTEND_BOILERPLATE)
    placeholder = normalized_token in _PLACEHOLDER_VALUES
    context_line = normalized_line.replace(normalized_token, "")
    decoy_context = any(
        marker in normalized_path
        for marker in ("/test", "/tests/", "/mock", "/example", "/sample", "/docs/")
    ) or any(keyword in context_line for keyword in NEGATIVE_KEYWORDS)
    return (example_path and entropy <= 4.5) or boilerplate or placeholder or decoy_context


@dataclass(frozen=True)
class DetectionCandidate:
    commit_sha: str
    file_path: str
    line_number: int
    secret_type: str
    masked_match: str
    fingerprint: str
    features: dict[str, float]
    feature_vector: tuple[float, ...]
    ml_probability: float
    is_false_positive: bool
    still_in_head: bool
    git_lifecycle_state: str
    is_base64_encoded: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    total = len(value)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


def _path_risk(path: str) -> float:
    value = path.lower().replace("\\", "/")
    if any(part in value.split("/") for part in ("test", "tests", "mock", "docs", "examples")):
        return 0.15
    if any(token in value for token in (".env", "config", ".yaml", ".yml", ".json", "credentials")):
        return 1.0
    return 0.5


def extract_14_features(token: str, file_path: str, surrounding_line: str, *, is_base64_encoded: bool = False) -> dict[str, float]:
    """Return the specified 14-dimensional, mathematically defined vector."""
    token = str(token or "")
    line = str(surrounding_line or "")
    length = len(token)
    alphabet_size = len(set(token))
    entropy = shannon_entropy(token)
    normalized = entropy / math.log2(alphabet_size) if alphabet_size > 1 else 0.0
    transitions = sum(token[index] != token[index - 1] for index in range(1, length)) / max(1, length - 1)
    window = line[max(0, line.lower().find(token.lower()) - 80): line.lower().find(token.lower()) + length + 80] if token else line[:160]
    lower_window = window.lower()
    positives = float(sum(keyword in lower_window for keyword in POSITIVE_KEYWORDS))
    negatives = float(sum(keyword in lower_window for keyword in NEGATIVE_KEYWORDS))
    return {
        "entropy": entropy,
        "normalized_entropy": normalized,
        "token_length": float(length),
        "digit_ratio": sum(char.isdigit() for char in token) / max(1, length),
        "uppercase_ratio": sum(char.isupper() for char in token) / max(1, length),
        "lowercase_ratio": sum(char.islower() for char in token) / max(1, length),
        "symbol_ratio": sum(not char.isalnum() for char in token) / max(1, length),
        "transition_frequency": transitions,
        "positive_keyword_proximity": positives,
        "negative_keyword_proximity": negatives,
        "file_path_risk_score": _path_risk(file_path),
        "is_base64_encoded": float(is_base64_encoded),
        "assignment_operator_present": float(any(operator in line for operator in ("=", ":", ":="))),
        "line_length": float(len(line)),
    }


def _train_model() -> tuple[object, str]:
    from sklearn.ensemble import HistGradientBoostingClassifier

    examples = [
        ("AKIAIOSFODNN7EXAMPLE", "config/prod.env", "AWS_ACCESS_KEY_ID=", 1),
        ("ghp_" + "A" * 30, "src/auth.py", "token=", 1),
        ("q7V!m2Z#p9L@x4R$k8N%t3Q", "config/app.env", "SECRET=", 1),
        ("AKIAEXAMPLENOTREAL00", "tests/test_keys.py", "MOCK_KEY=", 0),
        ("550e8400-e29b-41d4-a716-446655440000", "tests/fixture.py", "UUID=", 0),
        ("placeholder-value-123456", "docs/example.md", "TOKEN=", 0),
    ]
    x = [[extract_14_features(token, path, line)[name] for name in FEATURE_NAMES] for token, path, line, _ in examples]
    y = [label for _, _, _, label in examples]
    model = HistGradientBoostingClassifier(max_iter=50, random_state=42, l2_regularization=0.1)
    model.fit(x, y)
    return model, "HistGradientBoostingClassifier(fallback)"


def ensure_model() -> object:
    """Load or deterministically generate the XGBoost model artifact."""
    if MODEL_PATH.exists():
        try:
            metadata = json.loads(MODEL_META_PATH.read_text(encoding="utf-8"))
            model_name = str(metadata.get("model", ""))
        except (OSError, json.JSONDecodeError):
            model_name = ""
        xgboost_available = False
        try:
            import xgboost  # noqa: F401

            xgboost_available = True
        except ImportError:
            pass
        if not (xgboost_available and model_name != "XGBClassifier"):
            return joblib.load(MODEL_PATH)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        from xgboost import XGBClassifier

        model_name = "XGBClassifier"
        examples = [
            ("AKIAIOSFODNN7EXAMPLE", "config/prod.env", "AWS_ACCESS_KEY_ID=", 1),
            ("ghp_" + "A" * 30, "src/auth.py", "token=", 1),
            ("q7V!m2Z#p9L@x4R$k8N%t3Q", "config/app.env", "SECRET=", 1),
            ("AKIAEXAMPLENOTREAL00", "tests/test_keys.py", "MOCK_KEY=", 0),
            ("550e8400-e29b-41d4-a716-446655440000", "tests/fixture.py", "UUID=", 0),
            ("placeholder-value-123456", "docs/example.md", "TOKEN=", 0),
        ]
        x = [[extract_14_features(token, path, line)[name] for name in FEATURE_NAMES] for token, path, line, _ in examples]
        y = [label for _, _, _, label in examples]
        model = XGBClassifier(n_estimators=40, max_depth=3, learning_rate=0.1, random_state=42, eval_metric="logloss", n_jobs=1)
        model.fit(x, y)
    except ImportError:
        model, model_name = _train_model()
    joblib.dump(model, MODEL_PATH)
    MODEL_META_PATH.write_text(json.dumps({"model": model_name, "features": FEATURE_NAMES, "random_state": 42}, indent=2) + "\n", encoding="utf-8")
    return model


def _candidates(line: str) -> list[tuple[str, str, bool]]:
    found: list[tuple[str, str, bool]] = []
    for secret_type, pattern in PATTERNS:
        for match in pattern.finditer(line):
            value = match.group(1) if secret_type == "generic_assignment" and match.lastindex else match.group(0)
            if secret_type == "generic_assignment":
                prefix = line[:match.start()].rstrip()
                if prefix.endswith((".", "(", "[", "{")) or "." in prefix[-24:]:
                    continue
            found.append((secret_type, value, False))
    for encoded in BASE64_RE.findall(line):
        try:
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (ValueError, binascii.Error, UnicodeDecodeError):
            continue
        if any(pattern.search(decoded) for _, pattern in PATTERNS) or (
            len(decoded) >= 8 and any(keyword in decoded.lower() for keyword in POSITIVE_KEYWORDS)
        ):
            found.append(("base64_encoded", decoded, True))
    unique: dict[tuple[str, str, bool], None] = {}
    for item in found:
        unique[item] = None
    return list(unique)


def detect_lines(lines: Iterable[object]) -> list[DetectionCandidate]:
    """Detect candidates from ``HistoryLine`` objects or compatible mappings."""
    model = ensure_model()
    findings: list[DetectionCandidate] = []
    for item in lines:
        value = item if isinstance(item, Mapping) else asdict(item)
        line = str(value.get("added_line", ""))
        for secret_type, token, encoded in _candidates(line):
            features = extract_14_features(token, str(value.get("file_path", "")), line, is_base64_encoded=encoded)
            vector = tuple(features[name] for name in FEATURE_NAMES)
            probability = float(model.predict_proba([list(vector)])[0][1])
            heuristic_fp = _heuristic_false_positive(token, str(value.get("file_path", "")), line)
            model_fp = probability < 0.5
            findings.append(
                DetectionCandidate(
                    commit_sha=str(value.get("commit_sha", "")),
                    file_path=str(value.get("file_path", "")),
                    line_number=int(value.get("line_number", 1)),
                    secret_type=secret_type,
                    masked_match=_mask(token),
                    fingerprint=hashlib.sha256((FINGERPRINT_SALT + token).encode("utf-8")).hexdigest(),
                    features=features,
                    feature_vector=vector,
                    ml_probability=max(0.0, min(1.0, probability)),
                    is_false_positive=heuristic_fp or (
                        secret_type == "generic_assignment" and model_fp
                    ),
                    still_in_head=bool(value.get("still_in_head", False)),
                    git_lifecycle_state=str(value.get("git_lifecycle_state", "UNKNOWN")),
                    is_base64_encoded=encoded,
                )
            )
    return findings


detect = detect_lines


class Detector:
    """Small stateful facade for applications that prefer an object API."""

    def __init__(self) -> None:
        self.model = ensure_model()

    def detect(self, lines: Iterable[object]) -> list[DetectionCandidate]:
        return detect_lines(lines)

    @staticmethod
    def extract_features(token: str, file_path: str, surrounding_line: str, *, is_base64_encoded: bool = False) -> dict[str, float]:
        return extract_14_features(token, file_path, surrounding_line, is_base64_encoded=is_base64_encoded)


__all__ = [
    "DetectionCandidate",
    "Detector",
    "FEATURE_NAMES",
    "PATTERNS",
    "detect",
    "detect_lines",
    "ensure_model",
    "extract_14_features",
    "shannon_entropy",
]

# Materialize the versioned model during service startup/import if absent.
STARTUP_MODEL = ensure_model()
