from __future__ import annotations

import hashlib
import random
import shutil
from pathlib import Path

import yaml
from git import Repo

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "testdata" / "seeded_repo"
GROUND_TRUTH_PATH = ROOT / "testdata" / "ground_truth.yaml"
RAW_DEBUG_PATH = ROOT / "testdata" / "_raw_debug.yaml"

random.seed(42)


def _generate_secret_value(kind: str) -> str:
    if kind == "aws_access_key":
        return "AKIA" + "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(16))
    if kind == "github_pat":
        return "ghp_" + "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(36))
    if kind == "stripe_key":
        return "sk_test_" + "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(24))
    if kind == "slack_token":
        return "xoxb-" + "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(24))
    if kind == "jwt":
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." + "A" * 20 + "." + "B" * 15
    return "AKIA" + "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(16))


def _generate_false_positive() -> str:
    examples = [
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_0123456789abcdefghijklmnopqrstuv",
        "sk_test_1234567890abcdefghijklmnop",
        "xoxb-example-token-value",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.signature",
        "0123456789abcdef0123456789abcdef",
        "ZnJvbSB0ZXN0IGRhdGE=",
        "dummy-secret-value",
        "this is documentation only",
        "not-a-secret-hex-1234567890abcdef",
    ]
    return random.choice(examples)


def _write_file(repo: Repo, rel_path: str, content: str) -> None:
    full_path = Path(repo.working_tree_dir) / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")


def _make_repo() -> None:
    if SEED_DIR.exists():
        shutil.rmtree(SEED_DIR)
    if GROUND_TRUTH_PATH.exists():
        GROUND_TRUTH_PATH.unlink()
    if RAW_DEBUG_PATH.exists():
        RAW_DEBUG_PATH.unlink()

    repo = Repo.init(SEED_DIR)
    repo.config_writer().set_value("user", "name", "SecretGuard Test").release()
    repo.config_writer().set_value("user", "email", "secretguard@example.com").release()

    secret_kinds = ["aws_access_key", "github_pat", "stripe_key", "slack_token", "jwt"]
    ground_truth: list[dict] = []
    raw_debug: list[dict] = []

    for idx in range(15):
        kind = secret_kinds[idx % len(secret_kinds)]
        secret_value = _generate_secret_value(kind)
        rel_path = f"configs/secret_{idx:02d}.env"
        content = f"# generated\nSECRET={secret_value}\nSTATUS=active\n"
        _write_file(repo, rel_path, content)
        repo.index.add([rel_path])
        repo.index.commit(f"add true secret {idx}")
        ground_truth.append({
            "commit_sha": repo.head.commit.hexsha,
            "file": rel_path,
            "line": 2,
            "raw_value_hash": hashlib.sha256(secret_value.encode("utf-8")).hexdigest(),
            "label": "true_secret",
            "secret_type": kind,
        })
        raw_debug.append({
            "commit_sha": repo.head.commit.hexsha,
            "file": rel_path,
            "line": 2,
            "raw_value": secret_value,
            "surrounding_line": content,
        })

    for idx in range(15):
        false_value = _generate_false_positive()
        rel_path = f"docs/example_{idx:02d}.md"
        content = f"Example docs\n{false_value}\n"
        _write_file(repo, rel_path, content)
        repo.index.add([rel_path])
        repo.index.commit(f"add false positive {idx}")
        ground_truth.append({
            "commit_sha": repo.head.commit.hexsha,
            "file": rel_path,
            "line": 2,
            "raw_value_hash": hashlib.sha256(false_value.encode("utf-8")).hexdigest(),
            "label": "false_positive",
            "secret_type": "none",
        })
        raw_debug.append({
            "commit_sha": repo.head.commit.hexsha,
            "file": rel_path,
            "line": 2,
            "raw_value": false_value,
            "surrounding_line": content,
        })

    GROUND_TRUTH_PATH.write_text(yaml.safe_dump(ground_truth, sort_keys=False), encoding="utf-8")
    RAW_DEBUG_PATH.write_text(yaml.safe_dump(raw_debug, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    _make_repo()
