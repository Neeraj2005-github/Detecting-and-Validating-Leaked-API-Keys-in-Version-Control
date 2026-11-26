from __future__ import annotations

import http.client
import ipaddress
import os
import shutil
import socket
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterator


FORBIDDEN_SCHEMES = {"file", "ssh", "git", "ftp", "ext"}


def _is_public_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def validate_https_url(
    value: str,
    *,
    allow_loopback_test: bool = False,
    allow_http_test: bool = False,
) -> str:
    return _validate_https_url(
        value,
        allow_loopback_test=allow_loopback_test,
        allow_http_test=allow_http_test,
    )[0]


def _validate_https_url(
    value: str,
    *,
    allow_loopback_test: bool,
    allow_http_test: bool,
) -> tuple[str, list[str]]:
    raw = value.strip()
    parsed = urllib.parse.urlparse(raw)
    scheme = parsed.scheme.lower()
    if scheme in FORBIDDEN_SCHEMES or (scheme != "https" and not (allow_http_test and scheme == "http")):
        raise ValueError("Only an https:// URL is accepted")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Repository URL is malformed")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Localhost repositories are not accepted")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None and not _is_public_ip(str(literal)):
        if not (allow_loopback_test and literal.is_loopback):
            raise ValueError("Private, link-local, or local repository addresses are not accepted")

    port = parsed.port or (80 if scheme == "http" else 443)
    try:
        addresses = sorted({
            item[4][0]
            for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        })
    except socket.gaierror as exc:
        raise ValueError("Repository hostname could not be resolved") from exc
    if not addresses or any(
        not _is_public_ip(address) and not (allow_loopback_test and ipaddress.ip_address(address).is_loopback)
        for address in addresses
    ):
        raise ValueError("Repository hostname resolves to a forbidden address")
    return parsed.geturl(), addresses


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, *, address: str, **kwargs: object) -> None:
        self._resolved_address = address
        super().__init__(host, **kwargs)

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._resolved_address, self.port),
            self.timeout,
            self.source_address,
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, *, address: str, **kwargs: object) -> None:
        self._resolved_address = address
        super().__init__(host, **kwargs)

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._resolved_address, self.port),
            self.timeout,
            self.source_address,
        )
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, address: str) -> None:
        super().__init__()
        self._address = address

    def http_open(self, request):
        return self.do_open(
            _PinnedHTTPConnection,
            request,
            address=self._address,
        )


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, address: str) -> None:
        super().__init__()
        self._address = address

    def https_open(self, request):
        return self.do_open(
            _PinnedHTTPSConnection,
            request,
            address=self._address,
            context=self._context,
        )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_redirect_chain(
    value: str,
    timeout_seconds: int = 10,
    *,
    allow_loopback_test: bool = False,
    allow_http_test: bool = False,
) -> str:
    return _validate_redirect_chain(
        value,
        timeout_seconds,
        allow_loopback_test=allow_loopback_test,
        allow_http_test=allow_http_test,
    )[0]


def _validate_redirect_chain(
    value: str,
    timeout_seconds: int,
    *,
    allow_loopback_test: bool,
    allow_http_test: bool,
) -> tuple[str, list[str]]:
    url, addresses = _validate_https_url(
        value,
        allow_loopback_test=allow_loopback_test,
        allow_http_test=allow_http_test,
    )
    current = url
    seen: set[str] = set()
    for _ in range(10):
        if current in seen:
            raise ValueError("Repository URL contains a redirect loop")
        seen.add(current)
        parsed = urllib.parse.urlparse(current)
        request = urllib.request.Request(current, method="HEAD")
        connection_handler = (
            _PinnedHTTPHandler(addresses[0])
            if parsed.scheme == "http"
            else _PinnedHTTPSHandler(addresses[0])
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirectHandler,
            connection_handler,
        )
        try:
            response = opener.open(request, timeout=timeout_seconds)
            response.close()
            return current, addresses
        except urllib.error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise ValueError("Repository URL could not be reached safely") from exc
            location = exc.headers.get("Location")
            if not location:
                raise ValueError("Repository redirect has no destination")
            current, addresses = _validate_https_url(
                urllib.parse.urljoin(current, location),
                allow_loopback_test=allow_loopback_test,
                allow_http_test=allow_http_test,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ValueError("Repository URL could not be reached safely") from exc
    raise ValueError("Repository URL redirected too many times")


def _directory_size_bytes(path: Path) -> int:
    total = 0
    for root, directories, filenames in os.walk(path):
        for filename in filenames:
            try:
                total += (Path(root) / filename).stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return total


def build_clone_command(
    url: str,
    destination: Path,
    hooks_dir: Path,
    *,
    resolved_addresses: list[str] | None = None,
) -> list[str]:
    command = [
        "git",
        "-c", f"core.hooksPath={hooks_dir.as_posix()}",
        "-c", "protocol.file.allow=never",
        "-c", "http.followRedirects=initial",
        "clone",
        "--no-recurse-submodules",
        "--",
        url,
        str(destination),
    ]
    parsed = urllib.parse.urlparse(url)
    if resolved_addresses:
        hostname = parsed.hostname or ""
        port = parsed.port or (80 if parsed.scheme == "http" else 443)
        if ":" in hostname:
            hostname = f"[{hostname}]"
        for address in resolved_addresses:
            resolved = f"[{address}]" if ":" in address else address
            command[1:1] = ["-c", f"http.curloptResolve={hostname}:{port}:{resolved}"]
    return command


def configure_askpass(parent: Path, env: dict[str, str], token: str) -> Path:
    askpass = parent / "askpass.cmd"
    askpass.write_text(
        "@echo off\r\n"
        "echo %SHD_GIT_TOKEN%\r\n",
        encoding="ascii",
    )
    env["GIT_ASKPASS"] = str(askpass)
    env["SHD_GIT_TOKEN"] = token
    return askpass


def clone_https_repository(
    value: str,
    *,
    timeout_seconds: int | None = None,
    max_size_mb: int | None = None,
    allow_loopback_test: bool = False,
    allow_http_test: bool = False,
) -> tuple[git.Repo, tempfile.TemporaryDirectory[str], Path]:
    # Import lazily so URL validation remains usable if GitPython is unavailable.
    import git

    url, resolved_addresses = _validate_redirect_chain(
        value,
        10,
        allow_loopback_test=allow_loopback_test,
        allow_http_test=allow_http_test,
    )
    timeout = timeout_seconds if timeout_seconds is not None else int(os.getenv("SHD_CLONE_TIMEOUT", "300"))
    max_size = max_size_mb if max_size_mb is not None else int(os.getenv("SHD_MAX_REPO_MB", "1024"))

    temporary = tempfile.TemporaryDirectory(prefix="secretguard-private-")
    parent = Path(temporary.name)
    os.chmod(parent, 0o700)
    hooks_dir = parent / "empty-hooks"
    hooks_dir.mkdir()
    os.chmod(hooks_dir, 0o700)
    destination = parent / "repository"
    env = os.environ.copy()
    env.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
    })
    token = os.environ.get("SHD_GIT_TOKEN")
    if token:
        configure_askpass(parent, env, token)

    command = build_clone_command(
        url,
        destination,
        hooks_dir,
        resolved_addresses=resolved_addresses,
    )
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(parent, ignore_errors=True)
        temporary.cleanup()
        raise RuntimeError("Repository clone timed out") from exc
    except OSError as exc:
        shutil.rmtree(parent, ignore_errors=True)
        temporary.cleanup()
        raise RuntimeError("Repository clone could not be started") from exc

    if completed.returncode != 0:
        shutil.rmtree(parent, ignore_errors=True)
        temporary.cleanup()
        raise RuntimeError("Repository clone failed")

    size = _directory_size_bytes(destination)
    if size > max_size * 1024 * 1024:
        shutil.rmtree(parent, ignore_errors=True)
        temporary.cleanup()
        raise RuntimeError("Repository exceeds the configured size limit")

    repo = git.Repo(str(destination), search_parent_directories=False)
    return repo, temporary, destination
