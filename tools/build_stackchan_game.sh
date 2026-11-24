#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE=""
if [[ $# -ne 0 ]]; then
  if [[ $# -ne 2 || "$1" != "--local-candidate" || -z "$2" ]]; then
    echo "Usage: $0 [--local-candidate NEW_DIRECTORY]" >&2; exit 2
  fi
  if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "Local binary package export disabled in CI" >&2; exit 2
  fi
  PACKAGE="$2"
  if [[ -e "$PACKAGE" || -L "$PACKAGE" ]]; then
    echo "Candidate output must not exist" >&2; exit 2
  fi
  if ! git -C "$ROOT" diff --quiet HEAD --; then
    echo "Commit tracked changes before creating source-bound candidate" >&2; exit 2
  fi
  if [[ -n "$(git -C "$ROOT" ls-files --others --exclude-standard -- TamaPoke boards/stackchan tools)" ]]; then
    echo "Untracked build source files must be reviewed before packaging" >&2; exit 2
  fi
fi
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
python3 "$ROOT/tools/generate_zh_tw_font.py" --u8g2 "${U8G2_SOURCE_DIR:-$ROOT/.deps/u8g2}" --out "$SKETCH/tpk_zh_tw_font.h"
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
BIN="$STAGE/compiled"
mkdir -p "$BIN"
arduino-cli compile --output-dir "$BIN" --warnings all --build-property 'compiler.cpp.extra_flags=-DBOARD_STACKCHAN=1' --fqbn 'esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=enabled,PartitionScheme=app3M_fat9M_16MB' "$SKETCH"
# Validate real compile outputs; publish only evidence, never the binaries.
REPORT="$ROOT/build/stackchan-game-review"
mkdir -p "$REPORT"
rm -f "$REPORT/manifest.json"
python3 "$ROOT/tools/stackchan_review.py" firmware --bins "$BIN" \
  --commit "$(git -C "$ROOT" rev-parse HEAD)" --report "$REPORT/manifest.json"
if [[ -n "$PACKAGE" ]]; then
  python3 "$ROOT/tools/stackchan_package.py" create --bins "$BIN" \
    --commit "$(git -C "$ROOT" rev-parse HEAD)" --out "$PACKAGE"
fi
# The temporary binaries are removed by the existing EXIT trap.
