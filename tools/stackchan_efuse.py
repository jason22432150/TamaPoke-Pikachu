#!/usr/bin/env python3
"""Read-only ESP32-S3 eFuse evidence. Never authorizes programming."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from stackchan_backup import run_logged,mac_of,sha256

VERSION="5.1.0"
FILES=("version.txt","mac-before.txt","summary.json","summary.log","mac-after.txt")
REQUIRED={"MAC","WR_DIS","RD_DIS","SECURE_BOOT_EN","SPI_BOOT_CRYPT_CNT"}

def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError("duplicate JSON field")
        result[k]=v
    return result

def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2*1024*1024:
        raise ValueError("invalid snapshot file")
    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=unique)

def fields(path):
    data=read_json(path)
    if not isinstance(data,dict) or not REQUIRED<=data.keys():
        raise ValueError("incomplete ESP32-S3 summary")
    keys={"name","value","readable","writeable","block","word","pos","bit_len","efuse_type"}
    for name,row in data.items():
        if not isinstance(row,dict) or not keys<=row.keys() or row["name"]!=name:
            raise ValueError("invalid eFuse field")
        if type(row["readable"]) is not bool or type(row["writeable"]) is not bool:
            raise ValueError("invalid eFuse permissions")
        if type(row["bit_len"]) is not int or row["bit_len"]<=0:
            raise ValueError("invalid eFuse length")
    return data

def evidence(out):
    for name in FILES:
        p=out/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size>2*1024*1024:
            raise ValueError("invalid snapshot input")
    version=(out/"version.txt").read_text()
    if not re.search(r"\bv?5\.1\.0\b",version):
        raise ValueError("esptool 5.1.0 required")
    a=mac_of((out/"mac-before.txt").read_text())
    b=mac_of((out/"mac-after.txt").read_text())
    if a!=b:raise ValueError("device identity changed")
    data=fields(out/"summary.json")
    mac=data["MAC"]
    if not mac["readable"] or str(mac["value"]).lower()!=a:
        raise ValueError("summary MAC differs from device")
    return dict(schema=1,chip="esp32s3",version=VERSION,mac=a,
                fields=len(data),unreadable=sum(not x["readable"] for x in data.values()),
                files={n:sha256(out/n) for n in FILES},flash_authorized=False)

def capture(port,out,runner=run_logged):
    out.mkdir(mode=0o700,exist_ok=False)
    base=[sys.executable,"-m","esptool"]
    runner(base+["version"],out/"version.txt")
    if not re.search(r"\bv?5\.1\.0\b",(out/"version.txt").read_text()):
        raise ValueError("esptool 5.1.0 required")
    mac=base+["--chip","esp32s3","--port",port,"--before","default-reset","--after","no-reset","read-mac"]
    runner(mac,out/"mac-before.txt")
    runner([sys.executable,"-m","espefuse","--chip","esp32s3","--port",port,
            "summary","--format","json","--file",str(out/"summary.json")],out/"summary.log")
    runner(mac,out/"mac-after.txt")
    m=evidence(out)
    with (out/"manifest.json").open("x",encoding="utf-8") as f:
        json.dump(m,f,indent=2)
    return m

def verify(out):
    if out.is_symlink():raise ValueError("symbolic link directory")
    m=read_json(out/"manifest.json")
    if m!=evidence(out):raise ValueError("snapshot integrity mismatch")
    return m

def compare(before,after):
    if before.resolve()==after.resolve():raise ValueError("independent snapshots required")
    a,b=verify(before),verify(after)
    if a["mac"]!=b["mac"]:raise ValueError("different device")
    x,y=fields(before/"summary.json"),fields(after/"summary.json")
    changed=sorted(k for k in x.keys()|y.keys() if x.get(k)!=y.get(k))
    if verify(before)!=a or verify(after)!=b:raise ValueError("snapshot changed during comparison")
    return dict(status="changed" if changed else "observable-summary-unchanged",
                changed_fields=changed,unreadable_before=a["unreadable"],
                unreadable_after=b["unreadable"],flash_authorized=False,
                warning="Only named observable fields compared; protected or reserved bits are not proven unchanged.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    c=sub.add_parser("capture");c.add_argument("--port",required=True);c.add_argument("--out",type=Path,required=True)
    v=sub.add_parser("verify");v.add_argument("--out",type=Path,required=True)
    q=sub.add_parser("compare");q.add_argument("--before",type=Path,required=True);q.add_argument("--after",type=Path,required=True)
    a=p.parse_args();os.umask(0o077)
    try:
        if a.action=="capture":
            capture(a.port,a.out);print("Private snapshot captured")
        elif a.action=="verify":
            verify(a.out);print("Snapshot integrity verified")
        else:
            report=compare(a.before,a.after);print(json.dumps(report,indent=2))
            return 2 if report["changed_fields"] else 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0

if __name__=="__main__":sys.exit(main())
