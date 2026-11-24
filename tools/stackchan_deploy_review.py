#!/usr/bin/env python3
"""Offline deployment evidence only; no serial commands or flash authorization."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from stackchan_merge import assemble,SECTOR
from stackchan_efuse import compare,verify
from stackchan_package import verify_package

def plan(candidate):
    _,report=assemble(candidate)
    regions=[]
    for r in report["regions"]:
        regions.append(dict(**r,erase_end=r["offset"]+((r["size"]+SECTOR-1)//SECTOR)*SECTOR))
    return dict(schema=1,source_commit=report["source_commit"],chip="esp32s3",
                flash_bytes=report["flash_bytes"],regions=regions,
                flash_authorized=False,efuse_write_allowed=False,
                blockers=["bootloader security configuration not independently attested",
                          "device security and actual partition map not verified for installation"])

def readback(candidate,readback_dir):
    p=plan(candidate)
    names={r["name"] for r in p["regions"]}
    if readback_dir.is_symlink() or {f.name for f in readback_dir.iterdir()}!=names:
        raise ValueError("unexpected readback files")
    for r in p["regions"]:
        f=readback_dir/r["name"]
        if f.is_symlink() or not f.is_file() or f.stat().st_size!=r["size"]:
            raise ValueError("invalid readback length or file")
        if hashlib.sha256(f.read_bytes()).hexdigest()!=r["sha256"]:
            raise ValueError("readback differs: "+r["name"])
    return dict(status="supplied-readback-matches",source_commit=p["source_commit"],
                flash_authorized=False,warning="Offline file comparison does not establish device provenance.")

def checkpoints(before,after_write,after_boot):
    paths=[before,after_write,after_boot]
    if len({p.resolve() for p in paths})!=3:
        raise ValueError("three independent snapshots required")
    manifests=[verify(p) for p in paths]
    if len({m["mac"] for m in manifests})!=1:
        raise ValueError("different devices")
    write=compare(before,after_write)
    boot=compare(after_write,after_boot)
    return dict(status="changed" if write["changed_fields"] or boot["changed_fields"] else "observable-summary-unchanged",
                after_write=write,after_boot=boot,flash_authorized=False,
                warning="Snapshot ordering and device boot history require operator evidence.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="action",required=True)
    a=s.add_parser("plan");a.add_argument("--candidate",type=Path,required=True)
    b=s.add_parser("readback");b.add_argument("--candidate",type=Path,required=True);b.add_argument("--readback",type=Path,required=True)
    c=s.add_parser("checkpoints")
    for name in ("before","after-write","after-boot"):c.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    try:
        if a.action=="plan":r=plan(a.candidate)
        elif a.action=="readback":r=readback(a.candidate,a.readback)
        else:r=checkpoints(a.before,a.after_write,a.after_boot)
        print(json.dumps(r,indent=2))
        return 2 if r.get("status")=="changed" else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1

if __name__=="__main__":sys.exit(main())
