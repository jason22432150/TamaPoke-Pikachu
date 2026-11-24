#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
SKETCH="$STAGE/StackChanCoreProbe"
mkdir -p "$SKETCH"
cp "$ROOT/boards/stackchan/StackChanCoreProbe/"* "$SKETCH/"
cp "$ROOT/boards/stackchan/hal/"*.h "$SKETCH/"
cp "$ROOT/boards/stackchan/partitions.csv" "$SKETCH/"
for f in pet.cpp pet.h dex.h i18n.cpp i18n.h audio.h species.h board.h; do cp "$ROOT/TamaPoke/$f" "$SKETCH/"; done
arduino-cli compile --warnings all --fqbn 'esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=enabled,PartitionScheme=app3M_fat9M_16MB' "$SKETCH"
# Deliberately no artifact or upload command: experimental integration only.
