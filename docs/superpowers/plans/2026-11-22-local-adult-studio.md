# Local Adult Studio — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or equivalent) to implement this plan task-by-task.

**Goal:** Ship v1 of WoombaDoesWilma — a private MacBook Pro studio: import → analyze → roughcut → polish → privacy → export, with local React UI + FastAPI/SQLite + FFmpeg workers + CLI.

**Architecture:** Monorepo with `packages/core` (timeline/jobs/ffmpeg), `apps/api` (FastAPI), `apps/cli` (Typer), `apps/web` (React+Vite). Library root defaults to `~/Movies/WoombaDoesWilma`. Spec: `docs/superpowers/specs/2026-11-22-local-adult-studio-design.md`.

**Tech stack:** Python 3.12, FastAPI, SQLite, Typer, FFmpeg/ffprobe, React + Vite + TypeScript, pytest, Vitest.

---

### Task 1: Repo scaffold + consent gate stub

**Files:**
- Create: `pyproject.toml`, `package.json` (workspace root), `.env.example`
- Create: `packages/core/woomba/__init__.py`, `packages/core/woomba/paths.py`, `packages/core/woomba/consent.py`, `packages/core/woomba/settings.py`
- Create: `apps/api/woomba_api/main.py` (health + consent endpoints)
- Create: `apps/cli/woomba_cli/main.py`
- Create: `apps/web/package.json`, `apps/web/index.html`, `apps/web/src/main.tsx`, `apps/web/src/App.tsx`
- Create: `tests/test_paths.py`, `tests/test_consent.py`
- Modify: `README.md`, `.gitignore`

**Steps:**
1. Create Python package layout with hatchling/setuptools editable installs; settings load library root from env `WOOMBA_LIBRARY`.
2. Implement `ensure_library_layout()` creating `inbox/`, `projects/`, `exports/`.
3. Implement consent file `library/.consent.json` with `accepted_at` + version; API `GET/POST /api/consent`.
4. CLI `woomba init` creates layout + prompts consent acknowledgment flag `--i-consent`.
5. Web shell: dark calm first-run consent screen + “Library” placeholder.
6. Run: `pytest tests/test_paths.py tests/test_consent.py -q` and `npm --prefix apps/web run build`.
7. Commit: `Scaffold monorepo with consent gate and library layout.`

---

### Task 2: SQLite job queue + project model

**Files:**
- Create: `packages/core/woomba/db.py`, `packages/core/woomba/models.py`, `packages/core/woomba/jobs.py`
- Create: `packages/core/woomba/timeline.py`
- Create: `tests/test_jobs.py`, `tests/test_timeline.py`
- Modify: `apps/api/woomba_api/main.py` — projects + jobs routes
- Modify: `apps/cli/woomba_cli/main.py` — `project create/list`

**Steps:**
1. SQLite schema: `projects`, `jobs` (id, project_id, type, status, progress, error, created_at, updated_at).
2. Timeline read/write helpers matching spec JSON shape.
3. Job enqueue + status update helpers; statuses: `queued|running|succeeded|failed|cancelled`.
4. API: `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{id}`, `GET /api/jobs/{id}`.
5. Tests cover create project, enqueue job, timeline round-trip.
6. Commit: `Add SQLite projects/jobs store and timeline helpers.`

---

### Task 3: Import + ffprobe analyze basics

**Files:**
- Create: `packages/core/woomba/media/probe.py`, `packages/core/woomba/media/import_clips.py`, `packages/core/woomba/media/metadata.py`
- Create: `packages/core/woomba/workers/import_job.py`, `packages/core/woomba/workers/analyze_job.py`
- Create: `scripts/make_fixture.sh`, `tests/fixtures/.gitkeep`
- Create: `tests/test_probe.py`, `tests/test_import_job.py`
- Modify: CLI — `woomba import`, `woomba analyze`

**Steps:**
1. Script generates short synthetic silent/noisy WAV+MP4 fixtures (non-adult) under `tests/fixtures/`.
2. `probe_clip()` returns duration_ms, width, height, codec, has_audio.
3. Import copies into `projects/<id>/sources/`, strips GPS via ffmpeg `-map_metadata -1` on copies.
4. Analyze runs silence detect (`silencedetect`) stub + stores draft segments (full keep if no silence).
5. Worker runner executes queued jobs synchronously first (in-process), then background thread in API.
6. Commit: `Implement import/probe/analyze with synthetic fixtures.`

---

### Task 4: Roughcut engine

**Files:**
- Create: `packages/core/woomba/media/silence.py`, `packages/core/woomba/media/roughcut.py`
- Create: `packages/core/woomba/workers/roughcut_job.py`
- Create: `tests/test_silence.py`, `tests/test_roughcut.py`
- Modify: CLI — `woomba roughcut`

**Steps:**
1. Parse ffmpeg silencedetect output into silence ranges.
2. Invert to keep ranges with padding; mark cut segments; write timeline.
3. Unit tests with known silence fixtures.
4. Commit: `Add silence-based roughcut timeline builder.`

---

### Task 5: Polish + privacy + export render

**Files:**
- Create: `packages/core/woomba/media/polish.py`, `packages/core/woomba/media/privacy.py`, `packages/core/woomba/media/export.py`
- Create: `packages/core/woomba/workers/polish_job.py`, `privacy_job.py`, `export_job.py`
- Create: `tests/test_export.py`
- Modify: CLI — `woomba polish|privacy|export`

**Steps:**
1. Polish: optional `loudnorm`, light `hqdn3d`, optional `vidstab` when available (skip gracefully).
2. Privacy: mute via volume filter on ranges; face blur as optional boxblur on full frame flag for v1 (document real face detect as later); always strip metadata on export.
3. Export concatenates keep segments to `exports/<project>-<ts>.mp4` + sidecar JSON; disk-space preflight.
4. Smoke test: import → roughcut → export on fixture.
5. Commit: `Add polish, privacy, and export render path.`

---

### Task 6: API job runner + SSE progress

**Files:**
- Create: `apps/api/woomba_api/runner.py`, `apps/api/woomba_api/auth.py`
- Modify: `apps/api/woomba_api/main.py` — job enqueue, SSE `/api/jobs/{id}/events`, bind settings
- Create: `tests/test_api.py`

**Steps:**
1. Background worker thread pulls queued jobs.
2. SSE emits progress events; cancel sets status `cancelled`.
3. Default bind `127.0.0.1`; `WOOMBA_LAN=1` + `WOOMBA_TOKEN` required for `0.0.0.0`.
4. Commit: `Wire API job runner, SSE progress, and LAN token.`

---

### Task 7: Web Library / Project / Export UI

**Files:**
- Create: `apps/web/src/api.ts`, `apps/web/src/pages/Library.tsx`, `Project.tsx`, `Export.tsx`, `Consent.tsx`
- Create: `apps/web/src/components/Player.tsx`, `SegmentList.tsx`, `JobPanel.tsx`
- Create: `apps/web/src/styles.css`
- Modify: `apps/web/src/App.tsx` routing

**Steps:**
1. Consent gate blocks app until accepted.
2. Library lists projects + inbox hint; create project.
3. Project: HTML5 video for proxies/sources when available; segment keep/cut toggles; job buttons; progress.
4. Export page: codec, strip metadata, privacy toggles, start export job.
5. Calm dark UI; one job per section.
6. Commit: `Add local web UI for library, project, and export.`

---

### Task 8: Hardening + docs + smoke script

**Files:**
- Create: `scripts/smoke.sh`, `docs/USAGE.md`
- Modify: `README.md`
- Create: `tests/test_smoke_pipeline.py`

**Steps:**
1. End-to-end pytest smoke on fixtures.
2. Document Mac setup (ffmpeg via brew, `woomba init`, `woomba serve`, `npm run dev`).
3. Retry-from-last-step helper for failed jobs.
4. Commit: `Add smoke tests and Mac usage docs.`

---

## Execution order

Tasks 1 → 8 sequentially. After each task: tests green, commit, push. Generation module remains a stub only if touched.
