from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "scaling-repos"


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def generate(commit_count: int) -> Path:
    repo = OUTPUT / f"repo-{commit_count}"
    if repo.exists():
        subprocess.run(["git", "-C", str(repo), "gc", "--prune=now"], check=False)
        import shutil
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "CP1 Scaling Fixture")
    git(repo, "config", "user.email", "cp1-scaling@example.test")
    fixture = repo / "fixtures.env"
    fixture.write_text("TOKEN=FAKE_EXAMPLE_ONLY\n", encoding="utf-8")
    git(repo, "add", "fixtures.env")
    git(repo, "commit", "-m", "initial fake fixture")
    for index in range(1, commit_count):
        fixture.write_text(
            f"COMMIT_{index}=FAKE_EXAMPLE_ONLY\n",
            encoding="utf-8",
        )
        git(repo, "add", "fixtures.env")
        git(repo, "commit", "-m", f"synthetic commit {index}")
    return repo


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for count in (100, 1000, 10000):
        generate(count)
        print(repo := OUTPUT / f"repo-{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
