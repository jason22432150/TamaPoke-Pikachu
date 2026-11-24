#!/usr/bin/env python3
"""Read-only same-device backup comparison; no flash/restore authorization."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from stackchan_backup import ARCHIVE, FLASH_BYTES, capture, verify, run_logged
from stackchan_review import security_state

SECTOR = 4096

def security(out):
    report = (out / "security.txt").read_text(encoding="utf-8", errors="replace")
    flags = re.findall(r"^\s*Flags:\s*(0x[0-9a-fA-F]+)\s*\(", report, re.M)
    crypt = re.findall(r"^\s*SPI Boot Crypt Count \(SPI_BOOT_CRYPT_CNT\):\s*(0x[0-9a-fA-F]+)\s*$", report, re.M)
    return dict(secure_boot=security_state(report,"Secure Boot"),
                flash_encryption=security_state(report,"Flash Encryption"),
                flags=int(flags[0],16) if len(flags)==1 else None,
                crypt_count=int(crypt[0],16) if len(crypt)==1 else None)

def compare_archives(factory,current):
    if factory.resolve()==current.resolve():
        raise ValueError("two independently captured archives required")
    original, latest = verify(factory), verify(current)
    if original["mac"]!=latest["mac"]:
        raise ValueError("different device MAC; do not restore or flash")
    before, after = security(factory), security(current)
    p1=json.loads((factory/"partitions.json").read_text(encoding="utf-8"))
    p2=json.loads((current/"partitions.json").read_text(encoding="utf-8"))
    layout_same=p1["status"]==p2["status"]=="candidate-md5-valid" and p1["entries"]==p2["entries"]
    # Compare sectors without emitting any credential or partition contents.
    changed=[]
    with (factory/ARCHIVE).open("rb") as a, (current/ARCHIVE).open("rb") as b:
        for offset in range(0,FLASH_BYTES,SECTOR):
            x,y=a.read(SECTOR),b.read(SECTOR)
            if len(x)!=SECTOR or len(y)!=SECTOR:
                raise ValueError("archive changed during comparison")
            if x!=y: changed.append(offset)
    # Re-verify to detect normal concurrent modifications, not an authenticity guarantee.
    if verify(factory)!=original or verify(current)!=latest:
        raise ValueError("archive changed during comparison")
    partitions=[]
    if p1["status"]=="candidate-md5-valid":
        for entry in p1["entries"]:
            count=sum(entry["offset"]<=x<entry["offset"]+entry["size"] for x in changed)
            partitions.append(dict(label=entry["label"],offset=entry["offset"],
                                   size=entry["size"],changed_sectors=count))
    blockers=[]
    for name, info in (("factory",before),("current",after)):
        if info["secure_boot"]!="disabled" or info["flash_encryption"]!="disabled":
            blockers.append(name+" security enabled or unknown")
        if info["flags"] is None or info["crypt_count"] is None:
            blockers.append(name+" security flags or crypt count unverified")
    if before!=after: blockers.append("security state differs")
    if not layout_same: blockers.append("partition layout differs or is unverified")
    blockers.extend(["factory provenance and same-device recovery not validated",
                     "experimental layout and hardware require review",
                     "no write or restore plan authorized"])
    return dict(schema=1,status="manual-review-required",same_device_mac=True,
                factory_capture_at=original["created"],current_capture_at=latest["created"],
                factory_sha256=original["files"][ARCHIVE],current_sha256=latest["files"][ARCHIVE],
                security_before=before,security_after=after,layout_matches=layout_same,
                changed_sectors=len(changed),changed_sector_bytes=len(changed)*SECTOR,
                factory_partition_changes=partitions,
                flash_authorized=False,restore_authorized=False,blockers=blockers)

def preflight(factory,current,port,baud=115200,runner=run_logged):
    verify(factory) # Fail before connecting if original archive is invalid.
    if factory.resolve()==current.resolve():
        raise ValueError("current capture must use a new directory")
    capture(port,current,baud,runner)
    return compare_archives(factory,current)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    for name in ("capture","compare"):
        q=sub.add_parser(name)
        q.add_argument("--factory",required=True,type=Path)
        q.add_argument("--current",required=True,type=Path)
        if name=="capture":
            q.add_argument("--port",required=True)
            q.add_argument("--baud",type=int,choices=(115200,230400,460800),default=115200)
    args=p.parse_args()
    os.umask(0o077)
    try:
        report=preflight(args.factory,args.current,args.port,args.baud) if args.action=="capture" else compare_archives(args.factory,args.current)
        print(json.dumps(report,indent=2))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0
if __name__=="__main__":
    sys.exit(main())
