#!/usr/bin/env python3
"""Offline factory backup review and compile-only firmware evidence. Never flashes."""
import argparse
import csv
import hashlib
import struct
import json
from pathlib import Path
import re
import sys
from stackchan_backup import ARCHIVE, TABLE_BYTES, parse_table, sha256, verify

ROOT=Path(__file__).resolve().parents[1]
LAYOUT=ROOT/"boards/stackchan/partitions.csv"

def partition_int(value):
    value=value.strip()
    if value[-1:].lower() in ("k","m"):
        return int(value[:-1],0)*({"k":1024,"m":1024*1024}[value[-1].lower()])
    return int(value,0)

def resolve_layout(lines):
    """Resolve the supported K151 CSV subset using ESP-IDF alignment rules."""
    types={"app":0,"data":1}
    subtypes={"nvs":2,"ota":0,"ota_0":16,"ota_1":17,"spiffs":130,"coredump":3,"phy":1}
    result=[];names=set();end=0x9000
    for row in csv.reader(line for line in lines if line.strip() and not line.lstrip().startswith("#")):
        if len(row)!=6:raise ValueError("expected six partition CSV fields")
        name,t,s,offset,size,flags=(field.strip() for field in row)
        if (not name or len(name.encode("ascii"))>16 or name in names or flags
            or t not in types or s not in subtypes
            or (t=="app")!=(s in ("ota_0","ota_1"))):
            raise ValueError("unsupported or duplicate K151 partition")
        alignment=0x10000 if t=="app" else 0x1000
        start=partition_int(offset) if offset else (end+alignment-1)//alignment*alignment
        n=partition_int(size)
        if start<end or start%alignment or n<=0 or n%0x1000 or start+n>0x1000000:
            raise ValueError("invalid partition bounds or alignment")
        result.append(dict(label=name,type=types[t],subtype=subtypes[s],offset=start,size=n,flags=0))
        names.add(name);end=start+n
    return result

def expected_layout():
    with LAYOUT.open() as f:
        return resolve_layout(f)

def security_state(report,key):
    matches=re.findall(r"^\s*"+re.escape(key)+r":\s*(Enabled|Disabled)\s*$",report,re.M)
    return matches[0].lower() if len(matches)==1 else "unknown"

def review_archive(out):
    m=verify(out)
    report=json.loads((out/"partitions.json").read_text())
    security=(out/"security.txt").read_text(encoding="utf-8",errors="replace")
    secure=security_state(security,"Secure Boot")
    encrypt=security_state(security,"Flash Encryption")
    blockers=[]
    if secure!="disabled": blockers.append("secure boot enabled or unknown")
    if encrypt!="disabled": blockers.append("flash encryption enabled or unknown")
    if report["status"]!="candidate-md5-valid":
        blockers.append("factory partition table unverified")
    elif report["entries"]!=expected_layout():
        blockers.append("device layout differs from candidate firmware")
    # Historical capture reports cannot establish the current device state.
    blockers.extend(["current device identity and security state not checked",
                     "factory firmware provenance and recovery procedure not validated",
                     "physical hardware and calibration not validated"])
    return dict(status="review-required",flash_authorized=False,restore_authorized=False,
                archive_sha256=m["files"][ARCHIVE],secure_boot=secure,flash_encryption=encrypt,
                layout_matches_experimental=report["status"]=="candidate-md5-valid" and report["entries"]==expected_layout(),
                blockers=blockers)

def validate_esp_image(data):
    """Validate unsigned standard ESP32-S3 image structure, not bootability."""
    if len(data)<24 or data[0]!=0xe9 or not 1<=data[1]<=16:
        raise ValueError("invalid ESP image header")
    if struct.unpack_from("<H",data,12)[0]!=9 or data[23] not in (0,1):
        raise ValueError("invalid ESP32-S3 chip ID or digest flag")
    pos=24
    checksum=0xef
    for _ in range(data[1]):
        if pos+8>len(data):
            raise ValueError("truncated ESP segment header")
        _,size=struct.unpack_from("<II",data,pos)
        pos+=8
        if size%4 or size>len(data)-pos:
            raise ValueError("invalid ESP segment size")
        for value in memoryview(data)[pos:pos+size]:
            checksum^=value
        pos+=size
    end=(pos+16)&~15
    if end>len(data) or any(data[pos:end-1]) or data[end-1]!=checksum:
        raise ValueError("invalid ESP image checksum or padding")
    if data[23]:
        if len(data)!=end+32 or hashlib.sha256(data[:end]).digest()!=data[end:]:
            raise ValueError("invalid ESP image digest")
    elif len(data)!=end:
        raise ValueError("unexpected ESP image trailing data")

def initial_ota_data():
    """Blank OTA selection for the experimental layout; never writes a device."""
    layout=expected_layout()
    ota=[p for p in layout if p["type"]==1 and p["subtype"]==0]
    slots=[p for p in layout if p["type"]==0]
    if len(ota)!=1 or ota[0]["size"]!=0x2000 or ota[0]["offset"]%0x1000:
        raise ValueError("invalid experimental OTA data layout")
    if sorted(p["subtype"] for p in slots)!=[16,17]:
        raise ValueError("expected exactly OTA slots 0 and 1 without factory app")
    return b"\xff"*ota[0]["size"]

def firmware_evidence(bins,source_commit):
    if not re.fullmatch(r"[0-9a-f]{40}",source_commit):
        raise ValueError("invalid source commit")
    names=("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin","TamaPoke.ino.partitions.bin")
    paths=[bins/n for n in names]
    for p in paths:
        if p.is_symlink() or not p.is_file():
            raise ValueError("missing or invalid compile output: "+p.name)
    app,boot,table=paths
    slots=[p for p in expected_layout() if p["type"]==0 and p["subtype"] in (16,17)]
    # Arduino's current FQBN reports a conservative 3 MiB application limit.
    if len(slots)!=2 or not 0<app.stat().st_size<=min(0x300000,*(p["size"] for p in slots)) or not 0<boot.stat().st_size<=0x8000:
        raise ValueError("firmware exceeds partition limits")
    for p in (app,boot):
        validate_esp_image(p.read_bytes())
    # ESP-IDF partition binaries may be padded to one 4 KiB sector.
    # Reject arbitrary trailing data and oversized images rather than silently
    # validating only the prefix that contains the partition records.
    if not TABLE_BYTES <= table.stat().st_size <= 0x1000:
        raise ValueError("invalid compiled partition image size")
    with table.open("rb") as f:
        data=f.read(TABLE_BYTES)
        padding=f.read()
    if any(b != 0xff for b in padding):
        raise ValueError("invalid compiled partition image padding")
    if len(data)!=TABLE_BYTES or parse_table(data)!=expected_layout():
        raise ValueError("compiled partition table does not match observed K151 CSV")
    return dict(schema=2,initial_ota=dict(name="ota_data_initial.bin",size=len(initial_ota_data()),sha256=hashlib.sha256(initial_ota_data()).hexdigest(),expected_slot="ota_0"),kind="compile-evidence-only",board="M5Stack StackChan K151",
                source_commit=source_commit,flash_authorized=False,restore_authorized=False,
                factory_compatible=False,files=[dict(name=p.name,size=p.stat().st_size,sha256=sha256(p)) for p in paths],
                partitions=expected_layout())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("archive")
    a.add_argument("--out",type=Path,required=True)
    b=sub.add_parser("firmware")
    b.add_argument("--bins",type=Path,required=True)
    b.add_argument("--commit",required=True)
    b.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.action=="archive":
            print(json.dumps(review_archive(args.out),indent=2))
        else:
            evidence=firmware_evidence(args.bins,args.commit)
            with args.report.open("x",encoding="utf-8") as f:
                json.dump(evidence,f,indent=2);f.write("\n")
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0
if __name__=="__main__":
    sys.exit(main())
