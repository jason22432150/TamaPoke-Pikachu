#!/usr/bin/env python3
"""Offline factory backup review and compile-only firmware evidence. Never flashes."""
import argparse
import csv
import json
from pathlib import Path
import re
import sys
from stackchan_backup import ARCHIVE, TABLE_BYTES, parse_table, sha256, verify

ROOT=Path(__file__).resolve().parents[1]
LAYOUT=ROOT/"boards/stackchan/partitions.csv"

def expected_layout():
    types={"app":0,"data":1}
    subtypes={"nvs":2,"ota":0,"ota_0":16,"ota_1":17,"spiffs":130,"coredump":3}
    with LAYOUT.open() as f:
        rows=csv.reader(line for line in f if line.strip() and not line.startswith("#"))
        return [dict(label=n,type=types[t],subtype=subtypes[s],offset=int(o,0),size=int(z,0),flags=0)
                for n,t,s,o,z,*_ in rows]

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
        blockers.append("factory layout differs from experimental firmware")
    # Historical capture reports cannot establish the current device state.
    blockers.extend(["current device identity and security state not checked",
                     "factory firmware provenance and recovery procedure not validated",
                     "physical hardware and calibration not validated"])
    return dict(status="review-required",flash_authorized=False,restore_authorized=False,
                archive_sha256=m["files"][ARCHIVE],secure_boot=secure,flash_encryption=encrypt,
                layout_matches_experimental=report["status"]=="candidate-md5-valid" and report["entries"]==expected_layout(),
                blockers=blockers)

def firmware_evidence(bins,source_commit):
    if not re.fullmatch(r"[0-9a-f]{40}",source_commit):
        raise ValueError("invalid source commit")
    names=("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin","TamaPoke.ino.partitions.bin")
    paths=[bins/n for n in names]
    for p in paths:
        if p.is_symlink() or not p.is_file():
            raise ValueError("missing or invalid compile output: "+p.name)
    app,boot,table=paths
    if not 0<app.stat().st_size<=0x300000 or not 0<boot.stat().st_size<=0x8000:
        raise ValueError("firmware exceeds partition limits")
    for p in (app,boot):
        with p.open("rb") as f:
            if f.read(1)!=b"\xe9":
                raise ValueError("invalid ESP image magic: "+p.name)
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
        raise ValueError("compiled partition table does not match experimental CSV")
    return dict(schema=1,kind="compile-evidence-only",board="M5Stack StackChan K151",
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
