#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
OUT_FILE="${OUT_FILE:-$ROOT_DIR/rally.mp4}"
VIDEO_URL="${VIDEO_URL:-https://youtu.be/UnwYdF8a5ws?si=3Sky_1LbEt_GhibJ}"
SECTION="${SECTION:-*8:28-8:36}"
FORMAT="${FORMAT:-best[ext=mp4]/best}"
EXTRACTOR_ARGS="${EXTRACTOR_ARGS:-youtube:player_client=android}"

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "yt-dlp not found. Install it first." >&2
  exit 1
fi

yt-dlp -f "$FORMAT" --extractor-args "$EXTRACTOR_ARGS" --download-sections "$SECTION" \
  --no-playlist "$VIDEO_URL" -o "$OUT_FILE"
