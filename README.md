# WoombaDoesWilma

Private, on-device Mac studio for editing (and later creating) your own amateur adult videos.

**v1 focus:** import → auto rough-cut → polish → optional privacy tools → export.  
Everything stays local. Consenting-adult footage only. No cloud upload by default.

## Status

Design in progress. See:

`docs/superpowers/specs/2026-11-22-local-adult-studio-design.md`

## Boundaries

- Your own / consenting-adult footage only
- No non-consensual deepfakes or third-party face-swap
- Masters never overwritten
- Generation deferred until stronger hardware

## Planned stack

- Local web UI + FastAPI job queue + FFmpeg workers
- CLI parity for batch jobs on MacBook Pro
