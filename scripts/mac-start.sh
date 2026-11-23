#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> WoombaDoesWilma Mac starter"

pick_python() {
  for candidate in \
    "${WOOMBA_PYTHON:-}" \
    /usr/local/bin/python3.12 \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
    /opt/homebrew/bin/python3.12 \
    /usr/local/bin/python3.11 \
    python3.12 \
    python3.11 \
    python3
  do
    if [[ -z "$candidate" ]]; then
      continue
    fi
    if command -v "$candidate" >/dev/null 2>&1 || [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

need() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required tool: $name" >&2
    return 1
  fi
}

PY="$(pick_python || true)"
if [[ -z "${PY}" ]]; then
  echo "Python 3.11+ not found. Install from https://www.python.org/downloads/" >&2
  exit 1
fi

need ffmpeg
need ffprobe
need npm
need node

echo "Python: $($PY --version 2>&1)"
echo "Node:   $(node -v)"
echo "FFmpeg: $(ffmpeg -version | head -1)"

if [[ ! -d .venv ]]; then
  echo "==> Creating venv"
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip >/dev/null
pip install -e ".[dev]" >/dev/null

export WOOMBA_LIBRARY="${WOOMBA_LIBRARY:-$HOME/Movies/WoombaDoesWilma}"
echo "Library: $WOOMBA_LIBRARY"

if [[ ! -f "$WOOMBA_LIBRARY/.consent.json" ]]; then
  echo "==> First run: accepting consent for owned/consenting-adult footage"
  woomba init --i-consent
else
  woomba init >/dev/null || true
fi

if [[ ! -d apps/web/node_modules ]]; then
  echo "==> Installing web deps"
  npm --prefix apps/web install
fi

API_LOG="/tmp/woomba-api.log"
WEB_LOG="/tmp/woomba-web.log"

echo "==> Starting API on http://127.0.0.1:8787"
woomba serve --host 127.0.0.1 --port 8787 >"$API_LOG" 2>&1 &
API_PID=$!

echo "==> Starting UI on http://127.0.0.1:5173"
npm --prefix apps/web run dev -- --host 127.0.0.1 --port 5173 >"$WEB_LOG" 2>&1 &
WEB_PID=$!

cleanup() {
  echo
  echo "==> Stopping..."
  kill "$WEB_PID" "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 2
echo
echo "Open:  http://127.0.0.1:5173"
echo "API:   http://127.0.0.1:8787/api/health"
echo "Logs:  $API_LOG  |  $WEB_LOG"
echo "Drop clips in: $WOOMBA_LIBRARY/inbox"
echo "Press Ctrl+C to stop both."
wait
