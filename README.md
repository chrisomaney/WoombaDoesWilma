# WoombaDoesWilma

Private, on-device Mac studio for editing (and later creating) your own amateur adult videos.

**v1:** import → analyze → rough-cut → polish → privacy → export  
Local React UI + FastAPI/SQLite + FFmpeg workers + CLI. No cloud upload by default.

## Quick start (Mac)

Needs Python 3.11+, Node, and FFmpeg on PATH.

```bash
chmod +x scripts/mac-start.sh
./scripts/mac-start.sh
```

Then open http://127.0.0.1:5173

Manual setup: see `docs/USAGE.md`.

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
