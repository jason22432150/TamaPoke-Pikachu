#!/usr/bin/env python3
"""Offline experimental image assembly; never opens serial or writes flash."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from stackchan_package import verify_package
from stackchan_assets import NAME as ASSETS_NAME, SIZE as ASSETS_SIZE

FLASH_BYTES = 16*1024*1024
SECTOR = 4096

def assemble(candidate):
    manifest=verify_package(candidate)
    partitions=manifest["partitions"]
    by_label={p["label"]:p for p in partitions}
    if len(by_label)!=len(partitions):
        raise ValueError("duplicate partition label")
    previous=0x9000
    for p in sorted(partitions,key=lambda p:p["offset"]):
        start,size=p["offset"],p["size"]
        if start<previous or start%SECTOR or size<=0 or size%SECTOR or start+size>FLASH_BYTES:
            raise ValueError("invalid partition bounds")
        previous=start+size
    apps=[p for p in partitions if p["type"]==0 and p["subtype"]==16]
    if len(apps)!=1:
        raise ValueError("expected exactly one initial OTA slot")
    app=apps[0]
    ota=by_label["otadata"]
    if app["type"]!=0 or app["subtype"]!=16 or app["offset"]%65536:
        raise ValueError("invalid initial app slot")
    if ota["type"]!=1 or ota["subtype"]!=0 or ota["size"]!=8192:
        raise ValueError("invalid OTA region")
    assets=by_label["assets"]
    if (assets["type"],assets["subtype"],assets["offset"],assets["size"])!=(1,130,0xa00000,ASSETS_SIZE):
        raise ValueError("unexpected assets partition")
    specs=[
        ("TamaPoke.ino.bootloader.bin",0,0x8000),
        ("TamaPoke.ino.partitions.bin",0x8000,0x1000),
        ("ota_data_initial.bin",ota["offset"],ota["size"]),
        ("TamaPoke.ino.bin",app["offset"],app["size"]),
        (ASSETS_NAME,assets["offset"],assets["size"]),
    ]
    evidence={p["name"]:p for p in manifest["files"]}
    evidence[manifest["initial_ota"]["name"]]=manifest["initial_ota"]
    regions=[]
    chunks=[]
    last=0
    for name,offset,capacity in sorted(specs,key=lambda x:x[1]):
        path=candidate/name
        if path.is_symlink() or not path.is_file():
            raise ValueError("invalid source file")
        data=path.read_bytes()
        digest=hashlib.sha256(data).hexdigest()
        if digest!=evidence[name]["sha256"] or len(data)!=evidence[name]["size"]:
            raise ValueError("source changed after verification")
        if not data or offset%SECTOR or offset<last or len(data)>capacity or offset+capacity>FLASH_BYTES:
            raise ValueError("invalid image region")
        last=offset+capacity
        chunks.append((offset,data))
        regions.append(dict(name=name,offset=offset,size=len(data),capacity=capacity,sha256=digest))
    # Sector-aligned prefix, NOT a full device backup. Gaps are erased bytes.
    length=max(offset+len(data) for offset,data in chunks)
    length=(length+SECTOR-1)//SECTOR*SECTOR
    merged=bytearray(b"\xff"*length)
    for offset,data in chunks:
        merged[offset:offset+len(data)]=data
    report=dict(schema=1,kind="offline-merged-review-only",source_commit=manifest["source_commit"],
                flash_authorized=False,restore_authorized=False,factory_compatible=False,
                flash_bytes=FLASH_BYTES,regions=regions,merged_size=length,
                merged_sha256=hashlib.sha256(merged).hexdigest(),
                warning="Writing this prefix would also overwrite gaps including NVS; not a migration or restore image.")
    return bytes(merged),report

def create(candidate,out):
    data,report=assemble(candidate)
    out.mkdir(mode=0o700,exist_ok=False)
    with (out/"merged-review-only.bin").open("xb") as f:
        f.write(data)
    with (out/"manifest.json").open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2);f.write("\n")
    return verify(candidate,out)

def verify(candidate,out):
    data,report=assemble(candidate)
    names={"merged-review-only.bin","manifest.json"}
    if out.is_symlink() or {p.name for p in out.iterdir()}!=names:
        raise ValueError("unexpected merged package contents")
    for name in names:
        p=out/name
        if p.is_symlink() or not p.is_file():
            raise ValueError("invalid merged package file")
    if (out/"merged-review-only.bin").stat().st_size!=len(data) or (out/"merged-review-only.bin").read_bytes()!=data:
        raise ValueError("merged image differs from validated inputs")
    if json.loads((out/"manifest.json").read_text(encoding="utf-8"))!=report:
        raise ValueError("merged manifest mismatch")
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("create","verify"))
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    os.umask(0o077)
    try:
        report=(create if args.action=="create" else verify)(args.candidate,args.out)
        print(json.dumps(report,indent=2))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    sys.exit(main())
