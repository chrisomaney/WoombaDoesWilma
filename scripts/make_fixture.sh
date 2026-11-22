#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/tests/fixtures"
mkdir -p "$OUT"

# 3s color bars + sine, with a quiet middle second for silence detection tests
ffmpeg -y -f lavfi -i "color=c=blue:s=320x240:d=3" -f lavfi -i "sine=frequency=880:duration=3" \
  -filter_complex "[1:a]volume=enable='between(t,1,2)':volume=0[a]" \
  -map 0:v -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest \
  "$OUT/silence_demo.mp4"

# Short clean clip without intentional silence
ffmpeg -y -f lavfi -i "color=c=green:s=320x240:d=1" -f lavfi -i "sine=frequency=440:duration=1" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest \
  "$OUT/short_clean.mp4"

echo "Fixtures written to $OUT"
