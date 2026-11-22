# Local Adult Video Studio — Design Spec

**Date:** 2026-11-22  
**Status:** Draft for review  
**Product working name:** WoombaDoesWilma (local Mac studio)  
**Host:** MacBook Pro (Apple Silicon preferred; CPU-safe path required)

## 1. Goal

Build a **private, on-device** home studio that helps edit and later create amateur adult videos from **footage owned by consenting adults only**.

**v1 success:** import clips → auto rough-cut → polish → optional privacy tools → export. No prompt-to-video generation in v1.

**Later:** light create/enhance module when hardware allows (stronger GPU / external box).

## 2. Non-negotiable boundaries

- Consenting adults only; first-run consent gate required.
- No non-consensual deepfakes / face-swap of third parties.
- No cloud upload or telemetry by default.
- Masters are never overwritten; work happens on copies/proxies.
- Generation is out of scope for v1 (stub interface only).

## 3. Approach

**Local web UI + worker queue + CLI parity** (approved).

- FastAPI API + SQLite job store
- FFmpeg-centered media workers
- Local React web UI on `127.0.0.1`
- Optional LAN bind behind a simple shared token
- Same jobs runnable via CLI for batch work

Rejected alternatives:

- Script-only wrappers around Final Cut / Resolve (weaker “home AI” product; poor LAN review)
- Docker/NVIDIA GPU pipelines (poor MacBook Pro fit for v1)

## 4. Architecture

```
[Media library on disk]
        │
        ▼
┌───────────────────┐     jobs      ┌─────────────────────┐
│  Web UI (local)   │◄─────────────►│  API + job queue    │
│  review / trim    │               │  FastAPI + SQLite   │
│  export / privacy │               └─────────┬───────────┘
└───────────────────┘                         │
                                              ▼
                                    ┌─────────────────────┐
                                    │  Workers (CLI too)  │
                                    │  FFmpeg + analyzers │
                                    │  (MLX later)        │
                                    └─────────────────────┘
```

### Components

| Unit | Responsibility | Depends on |
|---|---|---|
| `studio-api` | Projects, clips, jobs, auth token, websocket/SSE progress | SQLite, filesystem |
| `studio-worker` | Runs media jobs; writes artifacts + timeline JSON | FFmpeg, analyzers |
| `studio-cli` | Same job entrypoints as API (`import`, `roughcut`, …) | worker library |
| `studio-web` | Library / Project / Export screens | API |
| `media-layout` | Convention for `inbox/`, `projects/`, `exports/` | none |

### Default library layout

```
~/Movies/WoombaDoesWilma/
  inbox/
  projects/<project-id>/
    sources/
    proxies/
    timeline.json
    jobs/
    logs/
  exports/
```

Paths are configurable.

## 5. Jobs (v1)

Each project keeps a JSON timeline. Jobs are queued, cancelable, and resumable from the last successful step.

| Job | Behavior |
|---|---|
| `import` | Link or copy clips; probe duration/codec; strip GPS on copies |
| `analyze` | Silence/scene detect, loudness, shake score, optional face regions |
| `roughcut` | Drop dead air + near-duplicate junk; draft keep/cut ranges |
| `polish` | Optional stabilize, color normalize, denoise, LUFS normalize |
| `privacy` | On-demand face blur, mute ranges, metadata strip |
| `export` | Render MP4 + sidecar timeline; masters untouched |

CLI examples:

```bash
studio import ./clips --project weekend-01
studio roughcut weekend-01 --silence -35dB
studio export weekend-01 --codec h264
```

### v1 non-goals

- Prompt-to-video / image-to-video generation
- Face-swap / identity transfer
- Multi-user accounts / cloud sync
- Full NLE feature parity with Premiere / Resolve

## 6. Timeline model (conceptual)

```json
{
  "project_id": "weekend-01",
  "version": 1,
  "clips": [
    {"id": "c1", "path": "sources/cam-a.mov", "duration_ms": 120000}
  ],
  "segments": [
    {
      "id": "s1",
      "clip_id": "c1",
      "in_ms": 1000,
      "out_ms": 15000,
      "state": "keep",
      "mute": false,
      "blur_faces": false
    }
  ],
  "export": {
    "codec": "h264",
    "strip_metadata": true
  }
}
```

Segment states: `keep` | `cut`. Privacy flags are per-segment overrides.

## 7. UI

Editor-first, three screens:

1. **Library** — inbox clips and projects
2. **Project** — player, waveform, keep/cut list, job runner, undo
3. **Export** — codec, privacy toggles, destination

Project view is the primary workspace: scrub timeline, toggle segments, run `analyze → roughcut → polish → privacy → export`.

LAN phones may review; heavy renders stay on the MacBook via queue/CLI.

Visual direction: calm dark chrome, minimal clutter, clear job progress and cancel.

## 8. Privacy & security

Defaults:

- Bind `127.0.0.1` only
- LAN requires explicit enable + shared token
- No telemetry
- Import copies strip GPS / identifying metadata
- Consent acknowledgment on first launch
- Optional face blur + mute before export
- Exports land in `exports/`; sources remain read-only from the app’s perspective

## 9. Export

- Default: MP4 H.264
- Optional: H.265 on Apple Silicon when available
- Sidecar JSON of final timeline for re-edit
- Optional proxy media for faster scrubbing on MacBook Pro

## 10. Errors & recovery

- Persist job logs under `projects/<id>/logs/`
- On failure, keep partial artifacts; retry from last ok step
- Preflight disk-space check before export
- Per-clip analyze failures mark the clip and continue the rest

## 11. Testing strategy (v1)

- Unit tests for silence/scene cut helpers with fixture audio/video
- Smoke: import → roughcut → export on a short checked-in fixture (non-adult synthetic media)
- Manual: Library → Project → Export on localhost

## 12. Implementation phases

1. **Scaffold** — repo layout, API, SQLite jobs, CLI stubs, empty web shell
2. **Import + analyze** — probe, silence/scene, timeline draft
3. **Roughcut + Project UI** — review/edit segments
4. **Polish + privacy + export** — FFmpeg render path
5. **Hardening** — cancel/retry, LAN token, disk checks
6. **Later (not v1)** — generation/enhance module behind a feature flag

## 13. Open decisions locked by this spec

- Host: MacBook Pro local
- UX: mix of LAN web UI + CLI/batch
- v1 scope: full rough cut (auto-cut + polish + light privacy); no generation
- Architecture: Approach 1 (local web + worker)
