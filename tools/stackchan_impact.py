#!/usr/bin/env python3
"""Offline deployment impact report; never accesses a device or authorizes writes."""
import argparse
import json
import os
from pathlib import Path
import sys
from stackchan_backup import ARCHIVE, verify, FLASH_BYTES
from stackchan_merge import assemble, SECTOR
from stackchan_preflight import compare_archives
from stackchan_package import verify_package

def overlaps(start,end,regions):
    return sum(max(0,min(end,b)-max(start,a)) for a,b in regions)

def impact(factory,current,candidate):
    preflight=compare_archives(factory,current)
    original=verify(factory)
    latest=verify(current)
    manifest=verify_package(candidate)
    merged,assembly=assemble(candidate)
    if manifest["source_commit"]!=assembly["source_commit"]:
        raise ValueError("candidate changed during analysis")
    table=json.loads((current/"partitions.json").read_text(encoding="utf-8"))
    separate=[(r["offset"],r["offset"]+((r["size"]+SECTOR-1)//SECTOR)*SECTOR)
              for r in assembly["regions"]]
    prefix=[(0,len(merged))]
    rows=[]
    for p in table["entries"]:
        start,end=p["offset"],p["offset"]+p["size"]
        same=p in manifest["partitions"]
        rows.append(dict(label=p["label"],type=p["type"],subtype=p["subtype"],
                         offset=start,size=p["size"],exact_layout_match=same,
                         separate_erase_bytes=overlaps(start,end,separate),
                         merged_erase_bytes=overlaps(start,end,prefix),
                         data_partition=p["type"]!=0))
    # All non-app partitions are potentially valuable, including unknown types.
    # Even a physically untouched partition is not logically preserved if moved.
    blockers=list(preflight["blockers"])
    if table["status"]!="candidate-md5-valid":
        blockers.append("current partition table unknown; impact incomplete")
    if any(p["data_partition"] and (p["separate_erase_bytes"] or not p["exact_layout_match"]) for p in rows):
        blockers.append("separate images affect data partitions or their layout")
    if any(p["data_partition"] and p["merged_erase_bytes"] for p in rows):
        blockers.append("merged prefix erases data partition sectors")
    if verify(factory)!=original or verify(current)!=latest or verify_package(candidate)!=manifest:
        raise ValueError("inputs changed during analysis")
    return dict(schema=1,status="manual-review-required",flash_authorized=False,restore_authorized=False,
                factory_sha256=original["files"][ARCHIVE],current_sha256=latest["files"][ARCHIVE],
                source_commit=manifest["source_commit"],partition_table_verified=table["status"]=="candidate-md5-valid",
                separate_erase_bytes=sum(b-a for a,b in separate),merged_erase_bytes=len(merged),
                partitions=rows,blockers=blockers,
                warning="Sector ranges are estimates for raw writes, not a write plan. Calibration location and boot-time mutations are unverified.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("factory","current","candidate"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--report",type=Path)
    a=p.parse_args()
    os.umask(0o077)
    try:
        result=impact(a.factory,a.current,a.candidate)
        payload=json.dumps(result,indent=2)+"\n"
        if a.report:
            with a.report.open("x",encoding="utf-8") as f:f.write(payload)
        else:print(payload,end="")
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0

if __name__=="__main__":
    sys.exit(main())
