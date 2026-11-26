from __future__ import annotations

import json
import http.server
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import git
import pytest

from src.shd import cli
from backend.services.repository_ingestion import (
    _directory_size_bytes,
    validate_https_url,
)
from backend.services.repository_ingestion import build_clone_command, configure_askpass
from backend.services.repository_ingestion import (
    clone_https_repository,
    validate_redirect_chain,
)


def _local_repo(tmp_path: Path) -> Path:
    repo = git.Repo.init(tmp_path, initial_branch="main")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Phase A Fixture")
        config.set_value("user", "email", "phase-a@example.test")
    (tmp_path / "config.env").write_text(
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n",
        encoding="utf-8",
    )
    repo.index.add(["config.env"])
    repo.index.commit("Add fake credential")
    repo.close()
    return tmp_path


def test_cli_local_repo_json_end_to_end(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    env = os.environ.copy()
    env["SHD_HMAC_KEY"] = "FAKE_TEST_HMAC_KEY_NOT_A_SECRET"
    out = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.shd.cli",
            "scan",
            str(repo),
            "--format",
            "json",
            "--out",
            str(out),
            "--fail-on-findings",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=env,
    )
    assert completed.returncode == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["coverage"]["refs"]["branch_count"] >= 1
    assert payload["coverage"]["refs"]["tag_count"] >= 0
    assert payload["findings"]
    assert payload["exit_code_meaning"]["0"].startswith("scan completed")
    assert payload["exit_code_meaning"]["1"].endswith("--fail-on-findings is set")
    assert "AKIAIOSFODNN7EXAMPLE" not in out.read_text(encoding="utf-8")
    assert "commits=" in completed.stdout
    assert "exit-codes=0 completed" in completed.stdout


def test_cli_reports_sanitized_runtime_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _local_repo(tmp_path)

    def fail_preflight(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("sensitive exception detail")

    monkeypatch.setattr(cli, "build_coverage", fail_preflight)
    assert cli.main(["scan", str(repo)]) == 3
    captured = capsys.readouterr()
    assert "scan runtime error during preflight (RuntimeError)" in captured.err
    assert "sensitive exception detail" not in captured.err


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/repository.git",
        "ssh://git@example.test/repository.git",
        "ext::sh -c /bin/false",
        "http://example.test/repository.git",
    ],
)
def test_cli_rejects_forbidden_schemes(url: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "src.shd.cli", "scan", url],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 4


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/repository.git",
        "https://127.0.0.1/repository.git",
        "https://10.0.0.10/repository.git",
        "https://169.254.169.254/repository.git",
        "https://[::1]/repository.git",
    ],
)
def test_https_url_rejects_forbidden_addresses(url: str) -> None:
    with pytest.raises(ValueError):
        validate_https_url(url)


def test_https_url_accepts_only_a_resolved_public_host() -> None:
    with pytest.raises(ValueError):
        validate_https_url("https://localhost/repository.git")


def test_oversize_limit_helper(tmp_path: Path) -> None:
    (tmp_path / "small.bin").write_bytes(b"FAKE" * 16)
    assert _directory_size_bytes(tmp_path) == 64


def test_clone_argv_never_contains_token(tmp_path: Path) -> None:
    token = "FAKE_TOKEN_NOT_A_REAL_SECRET"
    env: dict[str, str] = {}
    askpass = configure_askpass(tmp_path, env, token)
    command = build_clone_command(
        "https://example.invalid/repository.git",
        tmp_path / "repository",
        tmp_path / "empty-hooks",
    )
    assert token not in command
    assert all(token not in argument for argument in command)
    assert env["SHD_GIT_TOKEN"] == token
    assert env["GIT_ASKPASS"] == str(askpass)


def test_local_http_redirect_to_private_ip_is_rejected() -> None:
    class RedirectHandler(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            self.send_response(302)
            self.send_header("Location", "http://10.0.0.10/repository.git")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), RedirectHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/redirect"
        with pytest.raises(ValueError, match="Private|private|forbidden"):
            validate_redirect_chain(
                url,
                timeout_seconds=2,
                allow_loopback_test=True,
                allow_http_test=True,
            )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_redirect_probe_connects_to_the_address_it_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OkHandler(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), OkHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_getaddrinfo = socket.getaddrinfo
    original_create_connection = socket.create_connection
    resolutions = 0
    connected: list[str] = []

    def rebinding_getaddrinfo(host: str, port: int, *args: object, **kwargs: object):
        nonlocal resolutions
        if host == "rebind.example.test":
            resolutions += 1
            address = "127.0.0.1" if resolutions == 1 else "10.0.0.10"
            return original_getaddrinfo(address, port, *args, **kwargs)
        return original_getaddrinfo(host, port, *args, **kwargs)

    def recording_connect(address: tuple[str, int], *args: object, **kwargs: object):
        connected.append(address[0])
        return original_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", rebinding_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", recording_connect)
    try:
        url = f"http://rebind.example.test:{server.server_port}/repository.git"
        result = validate_redirect_chain(
            url,
            timeout_seconds=2,
            allow_loopback_test=True,
            allow_http_test=True,
        )
        assert result == url
        assert resolutions == 1
        assert connected == ["127.0.0.1"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_clone_command_pins_validated_addresses(tmp_path: Path) -> None:
    command = build_clone_command(
        "https://example.test/repository.git",
        tmp_path / "repository",
        tmp_path / "empty-hooks",
        resolved_addresses=["93.184.216.34"],
    )
    assert "http.curloptResolve=example.test:443:93.184.216.34" in command


def test_local_http_clone_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.services.repository_ingestion as ingestion

    monkeypatch.setattr(
        ingestion,
        "_validate_redirect_chain",
        lambda *args, **kwargs: ("http://127.0.0.1/repository.git", ["127.0.0.1"]),
    )

    def timeout_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="git-clone", timeout=1)

    monkeypatch.setattr(ingestion.subprocess, "run", timeout_run)
    with pytest.raises(RuntimeError, match="timed out"):
        clone_https_repository(
            "http://127.0.0.1/repository.git",
            timeout_seconds=1,
            allow_loopback_test=True,
            allow_http_test=True,
        )


def test_oversize_local_clone_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import backend.services.repository_ingestion as ingestion

    monkeypatch.setattr(
        ingestion,
        "_validate_redirect_chain",
        lambda *args, **kwargs: ("http://127.0.0.1/repository.git", ["127.0.0.1"]),
    )

    def fake_clone(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        destination = Path(command[-1])
        destination.mkdir(parents=True)
        (destination / "large.bin").write_bytes(b"F" * (1024 * 1024 + 1))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(ingestion.subprocess, "run", fake_clone)
    with pytest.raises(RuntimeError, match="exceeds"):
        clone_https_repository(
            "http://127.0.0.1/repository.git",
            max_size_mb=1,
            allow_loopback_test=True,
            allow_http_test=True,
        )
