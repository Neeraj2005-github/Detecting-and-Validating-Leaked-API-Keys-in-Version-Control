#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then
  PYTHON="$ROOT/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  printf 'Python was not found. Create .venv and install requirements.txt first.\n' >&2
  exit 1
fi
command -v npm >/dev/null 2>&1 || { printf 'npm was not found.\n' >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { printf 'curl was not found; it is required for readiness checks.\n' >&2; exit 1; }

mkdir -p "$ROOT/logs"
BACKEND_LOG="$ROOT/logs/secretguard-demo-backend.log"
FRONTEND_LOG="$ROOT/logs/secretguard-demo-frontend.log"
BACKEND_PID=''
FRONTEND_PID=''

cleanup() {
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID"
  fi
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID"
  fi
}
trap cleanup EXIT

nohup "$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
nohup npm --prefix "$ROOT/frontend" run dev -- --host 127.0.0.1 --port 5173 >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

wait_for_url() {
  local url="$1"
  local pid="$2"
  local label="$3"
  for _ in $(seq 1 45); do
    if ! kill -0 "$pid" 2>/dev/null; then
      printf '%s process exited before becoming ready. See %s\n' "$label" "$BACKEND_LOG" >&2
      return 1
    fi
    if curl --fail --silent --output /dev/null "$url"; then
      return 0
    fi
    sleep 1
  done
  printf '%s did not become ready at %s\n' "$label" "$url" >&2
  return 1
}

wait_for_url 'http://127.0.0.1:8000/health' "$BACKEND_PID" backend
wait_for_url 'http://127.0.0.1:5173/vaultguard/scanner' "$FRONTEND_PID" frontend
trap - EXIT

URL='http://127.0.0.1:5173/vaultguard/scanner'
printf 'Demo ready: %s\nBackend PID: %s; frontend PID: %s\n' "$URL" "$BACKEND_PID" "$FRONTEND_PID"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "$URL" >/dev/null 2>&1 &
elif command -v cmd.exe >/dev/null 2>&1; then
  cmd.exe /c start "" "$URL" >/dev/null 2>&1 || printf 'Open %s in a browser.\n' "$URL"
else
  printf 'Open %s in a browser.\n' "$URL"
fi
