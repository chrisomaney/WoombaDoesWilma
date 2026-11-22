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

## Run locally

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

## Typical CLI workflow

```bash
# copy clips into inbox OR pass paths
cp ~/Desktop/clip.mov "$WOOMBA_LIBRARY/inbox/" 2>/dev/null || true

woomba project create weekend-01 --title "Weekend"
woomba import --project weekend-01 ~/Desktop/*.mp4
woomba analyze weekend-01
woomba roughcut weekend-01 --silence -35
woomba polish weekend-01
woomba privacy weekend-01
woomba export weekend-01 --codec h264
```

Exports land in `$WOOMBA_LIBRARY/exports/`.

## LAN review (optional)

```bash
export WOOMBA_LAN=1
export WOOMBA_TOKEN='pick-a-long-secret'
woomba serve
```

Phone/browser on your Wi‑Fi can hit `http://<mac-lan-ip>:8787` with header `X-Woomba-Token: …` (the Vite UI still proxies locally on the Mac).

## Boundaries

Consenting-adult / owned footage only. No cloud upload. No face-swap of third parties.
