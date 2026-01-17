#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
INPUT_FILE="${INPUT_FILE:-$ROOT_DIR/rally.mp4}"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/frames}"
FPS="${FPS:-30}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found. Install it first." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
ffmpeg -i "$INPUT_FILE" -vf "fps=$FPS" "$OUT_DIR/frame_%05d.jpg"
