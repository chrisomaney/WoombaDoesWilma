# WoombaDoesWilma

Private, on-device Mac studio for editing (and later creating) your own amateur adult videos.

**v1:** import → analyze → rough-cut → polish → privacy → export  
Local React UI + FastAPI/SQLite + FFmpeg workers + CLI. No cloud upload by default.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export WOOMBA_LIBRARY=/tmp/woomba-lib   # or ~/Movies/WoombaDoesWilma
woomba init --i-consent
woomba serve
```

```bash
cd apps/web && npm install && npm run dev
```

See `docs/USAGE.md` for the full Mac workflow.

## Docs

- Design: `docs/superpowers/specs/2026-11-22-local-adult-studio-design.md`
- Plan: `docs/superpowers/plans/2026-11-22-local-adult-studio.md`

## Boundaries

- Consenting-adult / owned footage only
- No non-consensual deepfakes or third-party face-swap
- Masters never overwritten
- Generation deferred

## Dev checks

```bash
./scripts/make_fixture.sh
pytest -q
npm --prefix apps/web run build
```
