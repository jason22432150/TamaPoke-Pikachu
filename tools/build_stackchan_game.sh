#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/tools/check_stackchan_partitions.py"
python3 "$ROOT/tools/generate_embedded.py" --check
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
SKETCH="$STAGE/TamaPoke"
mkdir -p "$SKETCH"
cp "$ROOT/TamaPoke/"*.{ino,h,cpp} "$SKETCH/"
cp "$ROOT/boards/stackchan/hal/"*.h "$SKETCH/"
cp "$ROOT/boards/stackchan/partitions.csv" "$SKETCH/"
source "$ROOT/boards/stackchan/versions.env"
BSP_DIR="${STACKCHAN_BSP_DIR:-$ROOT/.deps/stackchan-bsp}"
if [[ "$(git -C "$BSP_DIR" rev-parse HEAD)" != "$STACKCHAN_BSP_COMMIT" ]]; then
  echo "Official StackChan-BSP checkout at $STACKCHAN_BSP_COMMIT required" >&2
  exit 1
fi
if [[ -n "$(git -C "$BSP_DIR" status --porcelain)" ]]; then
  echo "StackChan-BSP checkout must be clean" >&2
  exit 1
fi
mkdir -p "$SKETCH/src/drivers"
cp -R "$BSP_DIR/src/drivers/PY32IOExpander" "$SKETCH/src/drivers/"
arduino-cli compile --warnings all --build-property 'compiler.cpp.extra_flags=-DBOARD_STACKCHAN=1' --fqbn 'esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=enabled,PartitionScheme=app3M_fat9M_16MB' "$SKETCH"
# Compile gate only. No upload or game artifact before hardware verification.
