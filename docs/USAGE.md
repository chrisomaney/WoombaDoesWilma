# Usage (MacBook Pro)

## Prerequisites

- Python 3.11+
- Node 20+
- FFmpeg (`brew install ffmpeg`)

## Setup

```bash
cd WoombaDoesWilma
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Optional: custom library root
export WOOMBA_LIBRARY="$HOME/Movies/WoombaDoesWilma"

woomba init --i-consent
```

## Run locally (easiest)

```bash
chmod +x scripts/mac-start.sh
./scripts/mac-start.sh
```

Builds the web UI and serves everything at **http://127.0.0.1:8787**. Ctrl+C stops it.

Hot-reload frontend during development:

```bash
WOOMBA_DEV=1 ./scripts/mac-start.sh
```

Then open http://127.0.0.1:5173

### Manual (two terminals)

Terminal A:

```bash
woomba serve
```

Terminal B:

```bash
cd apps/web
npm install
npm run dev
```

Open http://127.0.0.1:5173

## Typical workflow (UI)

1. Drop clips into `$WOOMBA_LIBRARY/inbox/` (`.mp4` / `.mov` ok)
2. Open http://127.0.0.1:5173 → create a project → open it
3. Click **Import files…** (or inbox / scan sources)
4. Click **Auto rough-cut** (analyze + roughcut), tweak cuts on the scrubber, then **Export keep only**
5. Find renders in `$WOOMBA_LIBRARY/exports/`

## Typical CLI workflow

```bash
# copy clips into inbox OR pass paths
cp ~/Desktop/clip.mov "$WOOMBA_LIBRARY/inbox/" 2>/dev/null || true

woomba project create weekend-01 --title "Weekend"
woomba import --project weekend-01
# or: woomba import --project weekend-01 ~/Desktop/*.mp4
woomba analyze weekend-01
woomba roughcut weekend-01 --silence -35
woomba polish weekend-01
woomba privacy weekend-01
woomba export weekend-01 --codec h264
```

Exports land in `$WOOMBA_LIBRARY/exports/`.

**Important:** copying files straight into `projects/.../sources` does nothing until you click **Scan sources folder** (or run import). The inbox + Import button is the normal path.

## LAN review (optional)

```bash
export WOOMBA_LAN=1
export WOOMBA_TOKEN='pick-a-long-secret'
woomba serve
```

Phone/browser on your Wi‑Fi can hit `http://<mac-lan-ip>:8787` with header `X-Woomba-Token: …` (the Vite UI still proxies locally on the Mac).

## Boundaries

Consenting-adult / owned footage only. No cloud upload. No face-swap of third parties.
