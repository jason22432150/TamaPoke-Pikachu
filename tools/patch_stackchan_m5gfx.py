#!/usr/bin/env python3
"""Pinned M5GFX 0.2.26 compatibility fix for K151 / ESP-IDF 6.1.1."""
import argparse
import hashlib
from pathlib import Path

SOURCE_BLOB="376d412cb98013a609d2672043245ade066f19cf"
RELATIVE=Path("src/lgfx/v1/platforms/esp32/common.cpp")

def git_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

REPLACEMENTS=(
    (b"#include <freertos/semphr.h>\n",b"#include <freertos/semphr.h>\n#include <freertos/task.h>\n",1),
    (b"        buscfg.intr_flags = 0;\n",b"        buscfg.intr_flags = 0;\n"
     b"        // K151: IDF 6.1 adds dma_burst_size; the legacy memset(~0u) leaves it UINT32_MAX.\n"
     b"        // Zero requests the SDK's supported default (32 bytes).\n"
     b"#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(6, 1, 0)\n"
     b"        buscfg.dma_burst_size = 0;\n"
     b"#endif\n",1),
    (b'          ESP_LOGW("LGFX", "Failed to spi_bus_initialize. ");',
     b'          ESP_LOGE("LGFX", "K151 SPI bus initialization failed; stopping before invalid handle access");\n'
     b'          for (;;) vTaskDelay(pdMS_TO_TICKS(1000));',2),
    (b'          ESP_LOGW("LGFX", "Failed to spi_bus_add_device. ");',
     b'          ESP_LOGE("LGFX", "K151 SPI device initialization failed; stopping before invalid handle access");\n'
     b'          for (;;) vTaskDelay(pdMS_TO_TICKS(1000));',2),
)

def patched(source):
    if git_blob_sha(source)!=SOURCE_BLOB:
        raise ValueError("M5GFX common.cpp is not the pinned upstream 0.2.26 source")
    for old,new,count in REPLACEMENTS:
        if source.count(old)!=count:raise ValueError("unexpected M5GFX patch context")
        source=source.replace(old,new)
    return source

def ensure(library,check_only=False):
    p=library/RELATIVE
    current=p.read_bytes()
    # Accept an already patched file only when reversing every exact change
    # recreates the pinned upstream blob and reapplying gives identical bytes.
    original=current
    for old,new,count in reversed(REPLACEMENTS):
        if original.count(new)==count:original=original.replace(new,old)
    fixed=patched(original)
    if current==fixed:return hashlib.sha256(fixed).hexdigest()
    if current!=original:raise ValueError("partial or unexpected M5GFX modifications")
    if check_only:raise ValueError("M5GFX K151 DMA patch missing; run without --check")
    p.write_bytes(fixed)
    return hashlib.sha256(fixed).hexdigest()

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library",type=Path)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    print("Pinned K151 M5GFX DMA patch SHA-256:",ensure(args.library,args.check))
