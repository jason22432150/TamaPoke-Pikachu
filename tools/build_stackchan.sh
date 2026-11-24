#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/tools/check_stackchan_partitions.py"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/StackChanSmoke"
cp "$ROOT/boards/stackchan/StackChanSmoke/StackChanSmoke.ino" "$STAGE/StackChanSmoke/"
cp "$ROOT/boards/stackchan/hal/"*.h "$STAGE/StackChanSmoke/"
cp "$ROOT/boards/stackchan/partitions.csv" "$STAGE/StackChanSmoke/"
OUT="$ROOT/build/stackchan-smoke"
mkdir -p "$OUT"
arduino-cli compile --warnings all --fqbn 'esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=enabled,PartitionScheme=app3M_fat9M_16MB' --output-dir "$OUT" "$STAGE/StackChanSmoke"
python3 - "$OUT" "$(git -C "$ROOT" rev-parse HEAD)" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1])
bins=sorted(out.glob("*.bin"))
assert bins, "No firmware generated"
manifest={"board":"M5Stack StackChan K151","version":"0.1.0-dev","kind":"diagnostic-only","source_commit":sys.argv[2],"flash_bytes":16777216,"psram_bytes":8388608,"factory_compatible":False,"flash_authorized":False,"files":[{"name":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in bins]}
(out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
(out/"SHA256SUMS").write_text("".join(f"{x['sha256']}  {x['name']}\n" for x in manifest["files"]))
PY
(cd "$OUT" && sha256sum -c SHA256SUMS)
