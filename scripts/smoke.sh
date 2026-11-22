#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
./scripts/make_fixture.sh
source .venv/bin/activate
pytest -q
npm --prefix apps/web run build
echo "Smoke OK"
