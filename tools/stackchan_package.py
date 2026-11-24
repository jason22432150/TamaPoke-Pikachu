#!/usr/bin/env python3
"""Create/verify an unapproved K151 bench candidate. Never accesses serial."""
import argparse
import hashlib
import re
import struct
import tempfile
import json
import os
from pathlib import Path
import shutil
import sys
from stackchan_review import firmware_evidence, initial_ota_data, validate_esp_image

IDF_PIN="051e4c4eb20346e043cdd47bc388fde75ff8af63"
SOURCE_FILES=("bootloader.bin","bootloader.elf","sdkconfig","bootloader-sdkconfig.h")

NOTICE = """EXPERIMENTAL K151 BENCH CANDIDATE -- NOT APPROVED FOR FLASH
This package has three compiled images, not a complete flash image.
An erased initial OTA selection image is included for offline review only.
No factory image, installer or restore command is included.
The partition layout is experimental. Verify current security, actual layout,
Bootloader safety and exact build approval before any write.
Passing package verification does not authorize flashing.
"""

def package(bins, out, commit):
    evidence=firmware_evidence(bins,commit)
    # Fail if output exists, including partial packages from earlier attempts.
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    try:
        for item in evidence["files"]:
            src=bins/item["name"]
            with src.open("rb") as f, (out/item["name"]).open("xb") as dest:
                shutil.copyfileobj(f,dest)
        if firmware_evidence(out,commit)!=evidence:
            raise ValueError("copied image changed")
        with (out/"ota_data_initial.bin").open("xb") as f:
            f.write(initial_ota_data())
        (out/"READ-ME-NOT-FOR-FLASH.txt").write_text(NOTICE,encoding="utf-8")
        with (out/"manifest.json").open("x",encoding="utf-8") as f:
            json.dump(evidence,f,indent=2);f.write("\n")
        return verify_package(out)
    except BaseException:
        # Incomplete output is deliberately retained for investigation.
        (out/"manifest.json").unlink(missing_ok=True)
        raise

def verify_package(out):
    mpath=out/"manifest.json"
    notice=out/"READ-ME-NOT-FOR-FLASH.txt"
    if out.is_symlink() or any(p.is_symlink() or not p.is_file() for p in (mpath,notice)):
        raise ValueError("symbolic links not accepted")
    m=json.loads(mpath.read_text(encoding="utf-8"))
    expected=firmware_evidence(out,m["source_commit"])
    if expected!=m:
        raise ValueError("manifest or firmware hash mismatch")
    if notice.read_text(encoding="utf-8")!=NOTICE:
        raise ValueError("missing or changed safety notice")
    ota=out/expected["initial_ota"]["name"]
    if ota.is_symlink() or not ota.is_file() or ota.stat().st_size!=8192 or ota.read_bytes()!=initial_ota_data():
        raise ValueError("invalid initial OTA selection image")
    names={x["name"] for x in expected["files"]}|{"manifest.json",notice.name,ota.name}
    if {p.name for p in out.iterdir()}!=names:
        raise ValueError("unexpected package contents")
    return expected

def app_idf_version(data):
    """Read the official esp_app_desc_t from the first image segment."""
    validate_esp_image(data)
    if struct.unpack_from("<I",data,28)[0]<256 or len(data)<288:
        raise ValueError("missing application descriptor")
    magic,secure=struct.unpack_from("<II",data,32)
    if magic!=0xABCD5432 or secure!=0:
        raise ValueError("invalid application descriptor or nonzero secure version")
    version=data[144:176].split(b"\0",1)[0].decode("ascii")
    if not re.fullmatch(r"v?6\.1\.1(?:-[A-Za-z0-9._-]+)?",version):
        raise ValueError("application is not based on ESP-IDF v6.1.1")
    return version

def combine(candidate,source_bootloader,arduino_evidence,out):
    """Produce an experimental paired image, never an approved installation."""
    old=verify_package(candidate)
    if source_bootloader.is_symlink():
        raise ValueError("invalid source bootloader directory")
    for name in (*SOURCE_FILES,"manifest.json","READ-ME-NOT-FOR-FLASH.txt"):
        p=source_bootloader/name
        if p.is_symlink() or not p.is_file():
            raise ValueError("invalid source bootloader file: "+name)
    source=json.loads((source_bootloader/"manifest.json").read_text(encoding="utf-8"))
    if (source.get("schema")!=1 or source.get("kind")!="source-bootloader-reference"
        or source.get("idf_version")!="6.1.1" or source.get("idf_commit")!=IDF_PIN
        or source.get("source_commit")!=old["source_commit"]
        or source.get("flash_authorized") is not False
        or source.get("bootloader_security_attested") is not False):
        raise ValueError("source bootloader provenance mismatch")
    hashes=source["files"]
    if set(hashes)!=set(SOURCE_FILES):
        raise ValueError("unexpected source bootloader file manifest")
    for name in SOURCE_FILES:
        if hashlib.sha256((source_bootloader/name).read_bytes()).hexdigest()!=hashes[name]:
            raise ValueError("source bootloader file hash mismatch: "+name)
    if arduino_evidence.is_symlink() or not arduino_evidence.is_file():
        raise ValueError("missing Arduino compile evidence")
    arduino=json.loads(arduino_evidence.read_text(encoding="utf-8"))
    by_name={f["name"]:f["sha256"] for f in old["files"]}
    if (arduino.get("source_commit")!=old["source_commit"] or arduino.get("arduino_core")!="4.0.0"
        or arduino.get("elf_conversion_matches") is not True
        or arduino.get("flash_authorized") is not False
        or arduino.get("bootloader_security_attested") is not False
        or arduino.get("app_sha256")!=by_name["TamaPoke.ino.bin"]
        or arduino.get("bootloader_bin_sha256")!=by_name["TamaPoke.ino.bootloader.bin"]):
        raise ValueError("Arduino compile evidence mismatch")
    new_boot=(source_bootloader/"bootloader.bin").read_bytes()
    app=(candidate/"TamaPoke.ino.bin").read_bytes()
    old_boot=(candidate/"TamaPoke.ino.bootloader.bin").read_bytes()
    if hashlib.sha256(new_boot).hexdigest()!=hashes["bootloader.bin"] or hashlib.sha256(app).hexdigest()!=by_name["TamaPoke.ino.bin"] or hashlib.sha256(old_boot).hexdigest()!=by_name["TamaPoke.ino.bootloader.bin"]:
        raise ValueError("input changed after validation")
    validate_esp_image(new_boot)
    version=app_idf_version(app)
    # Header byte 2 is SPI mode; byte 3 is size (high nibble) and speed.
    if new_boot[2:4]!=old_boot[2:4] or new_boot[2:4]!=app[2:4] or new_boot[3]>>4!=4:
        raise ValueError("SPI flash header mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        bins=Path(tmp)
        (bins/"TamaPoke.ino.bootloader.bin").write_bytes(new_boot)
        (bins/"TamaPoke.ino.bin").write_bytes(app)
        table=(candidate/"TamaPoke.ino.partitions.bin").read_bytes()
        if hashlib.sha256(table).hexdigest()!=by_name["TamaPoke.ino.partitions.bin"]:
            raise ValueError("partition image changed")
        (bins/"TamaPoke.ino.partitions.bin").write_bytes(table)
        paired=package(bins,out,old["source_commit"])
    return dict(schema=1,kind="source-bootloader-paired-candidate",
                source_commit=old["source_commit"],idf_commit=IDF_PIN,
                application_idf_version=version,source_bootloader_sha256=hashes["bootloader.bin"],
                arduino_bootloader_sha256=by_name["TamaPoke.ino.bootloader.bin"],
                app_sha256=by_name["TamaPoke.ino.bin"],paired_manifest=paired,
                flash_authorized=False,bootloader_security_attested=False,
                warning="Matching SDK and image headers do not establish runtime compatibility or eFuse safety.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    c=sub.add_parser("create")
    c.add_argument("--bins",type=Path,required=True)
    c.add_argument("--out",type=Path,required=True)
    c.add_argument("--commit",required=True)
    v=sub.add_parser("verify")
    v.add_argument("--out",type=Path,required=True)
    b=sub.add_parser("combine")
    for key in ("candidate","source-bootloader","arduino-evidence","out","report"):
        b.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    os.umask(0o077)
    try:
        if a.action=="combine":
            if a.report.exists() or a.report.is_symlink():raise ValueError("report already exists")
            m=combine(a.candidate,a.source_bootloader,a.arduino_evidence,a.out)
            with a.report.open("x",encoding="utf-8") as f:json.dump(m,f,indent=2)
        else:
            m=package(a.bins,a.out,a.commit) if a.action=="create" else verify_package(a.out)
        print(json.dumps(m,indent=2))
        print("Integrity verified; NOT APPROVED FOR FLASH.")
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0
if __name__=="__main__":
    sys.exit(main())
