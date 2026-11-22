# WoombaDoesWilma

Private, on-device Mac studio for editing (and later creating) your own amateur adult videos.

**v1 focus:** import → auto rough-cut → polish → optional privacy tools → export.  
Everything stays local. Consenting-adult footage only. No cloud upload by default.

## Status

Implementation in progress. Design + plan:

- `docs/superpowers/specs/2026-11-22-local-adult-studio-design.md`
- `docs/superpowers/plans/2026-11-22-local-adult-studio.md`

## Boundaries

- Your own / consenting-adult footage only
- No non-consensual deepfakes or third-party face-swap
- Masters never overwritten
- Generation deferred until stronger hardware

## Quick start (dev)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export WOOMBA_LIBRARY=/tmp/woomba-lib
woomba init --i-consent
woomba serve
```

In another terminal:

```bash
cd apps/web && npm install && npm run dev
```

Open http://127.0.0.1:5173

## Planned stack

- Local React web UI + FastAPI job queue + FFmpeg workers
- CLI parity for batch jobs on MacBook Pro
