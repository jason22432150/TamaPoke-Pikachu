#!/usr/bin/env bash
# Offline build only. Never accesses a device or invokes idf.py flash.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# != 1 || -z "$1" ]]; then
  echo "Usage: $0 NEW_OUTPUT_DIRECTORY" >&2; exit 2
fi
OUT="$1"
if [[ -e "$OUT" || -L "$OUT" ]]; then
  echo "Output must not already exist" >&2; exit 2
fi
: "${IDF_PATH:?Activate ESP-IDF v5.5 using export.sh first}"
PIN=8c750b088c7cd857d079c0eeb495da199b359461
if [[ "$(git -C "$IDF_PATH" rev-parse HEAD)" != "$PIN" ]]; then
  echo "Expected ESP-IDF v5.5 commit $PIN" >&2; exit 1
fi
if [[ -n "$(git -C "$IDF_PATH" status --porcelain --untracked-files=no)" ]]; then
  echo "ESP-IDF tracked sources must be clean" >&2; exit 1
fi
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$ROOT/boards/stackchan/bootloader/." "$STAGE/"
cp "$ROOT/boards/stackchan/partitions.csv" "$STAGE/partitions.csv"
idf.py -C "$STAGE" -B "$STAGE/build" -D IDF_TARGET=esp32s3 bootloader
PYTHONPATH="$ROOT/tools${PYTHONPATH:+:$PYTHONPATH}" python3 - "$STAGE" "$OUT" "$PIN" "$(git -C "$ROOT" rev-parse HEAD)" <<'PY'
import json, os, re, shutil, sys
from pathlib import Path
from stackchan_backup import sha256
from stackchan_deploy_review import check_sdkconfig, FORBIDDEN
from stackchan_review import validate_esp_image

stage,out=map(Path,sys.argv[1:3])
config=stage/"sdkconfig"
header=stage/"build/bootloader/config/sdkconfig.h"
boot=stage/"build/bootloader/bootloader.bin"
elf=stage/"build/bootloader/bootloader.elf"
settings=check_sdkconfig(config)
extra=("CONFIG_EFUSE_VIRTUAL","CONFIG_EFUSE_VIRTUAL_KEEP_IN_FLASH",
       "CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE","CONFIG_BOOTLOADER_FACTORY_RESET",
       "CONFIG_BOOTLOADER_APP_TEST","CONFIG_BOOTLOADER_SKIP_VALIDATE_IN_DEEP_SLEEP",
       "CONFIG_SECURE_BOOT_ENABLE_AGGRESSIVE_KEY_REVOKE")
resolved=dict(re.findall(r"^(CONFIG_[A-Z0-9_]+)=(.*)$",config.read_text(),re.M))
for key in extra:
    if resolved.get(key,"n") not in ("n","0"):
        raise SystemExit("Forbidden resolved configuration: "+key)
expected={"CONFIG_IDF_TARGET":'"esp32s3"', "CONFIG_ESPTOOLPY_FLASHMODE":'"dio"',
          "CONFIG_ESPTOOLPY_FLASHFREQ":'"80m"', "CONFIG_ESPTOOLPY_FLASHSIZE":'"16MB"',
          "CONFIG_PARTITION_TABLE_OFFSET":"0x8000"}
for key,value in expected.items():
    if resolved.get(key)!=value:
        raise SystemExit("Unexpected resolved configuration: "+key)
defines=dict(re.findall(r"^#define\s+(CONFIG_[A-Z0-9_]+)\s+([^\r\n]+)$",header.read_text(),re.M))
for key in FORBIDDEN+extra:
    if key in defines and defines[key].strip()!="0":
        raise SystemExit("Forbidden bootloader header: "+key)
for key,value in expected.items():
    if defines.get(key)!=value:
        raise SystemExit("Unexpected bootloader header: "+key)
data=boot.read_bytes()
if len(data)>0x8000:
    raise SystemExit("Bootloader exceeds 0x8000 boundary")
validate_esp_image(data)
os.umask(0o077)
out.mkdir(mode=0o700,exist_ok=False)
files={"bootloader.bin":boot,"bootloader.elf":elf,
       "sdkconfig":config,"bootloader-sdkconfig.h":header}
for name,src in files.items():
    shutil.copyfile(src,out/name)
report=dict(schema=1,kind="source-bootloader-reference",source_commit=sys.argv[4],
            idf_commit=sys.argv[3],flash_authorized=False,bootloader_security_attested=False,
            resolved_settings=expected,disabled_security_settings=list(FORBIDDEN+extra),
            files={name:sha256(out/name) for name in files},
            warning="Compiled reference only. Arduino application compatibility and full eFuse behavior require review.")
(out/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
(out/"READ-ME-NOT-FOR-FLASH.txt").write_text("Source bootloader reference only. NOT FOR FLASH.\n")
print(json.dumps(report,indent=2))
PY
