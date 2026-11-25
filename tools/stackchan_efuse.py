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
FILES=("version.txt","mac-before.txt","summary.json","summary.log","security.txt","mac-after.txt")
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

def raw_crypt_count(report):
    # esptool 5.1.0 get-security-info prints the raw three-bit field.
    # Reject duplicate, malformed and out-of-range records.
    lines=[line for line in report.splitlines()
           if line.lstrip().startswith("SPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT):")]
    if len(lines)!=1:
        raise ValueError("missing or duplicate raw SPI_BOOT_CRYPT_CNT")
    m=re.fullmatch(r"\s*SPI Boot Crypt Count \(SPI_BOOT_CRYPT_CNT\):\s*0x([0-7])\s*",lines[0])
    if not m:
        raise ValueError("invalid raw SPI_BOOT_CRYPT_CNT")
    return int(m[1],16)

def checked_crypt_count(row,report):
    count=raw_crypt_count(report)
    if row.get("readable") is not True:
        raise ValueError("SPI_BOOT_CRYPT_CNT not readable")
    # The pinned ESP32-S3 definition maps raw 0 and 3 to "Disable",
    # and 1 and 7 to "Enable". Other values remain numeric.
    value=row.get("value")
    if not ((type(value) is int and value==count)
            or (type(value) is str and value=={0:"Disable",1:"Enable",3:"Disable",7:"Enable"}.get(count))):
        raise ValueError("SPI_BOOT_CRYPT_CNT summary and raw count disagree")
    return count

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
    # ESP32-S3 EfuseMacField.get() appends block status, e.g. "aa:... (OK)".
    # Accept a plain MAC for older captures, but never accept a block error.
    m=re.fullmatch(r"((?:[0-9a-f]{2}:){5}[0-9a-f]{2})(?: \(OK\))?",
                   str(mac["value"]),re.I)
    if not mac["readable"] or not m or m[1].lower()!=a:
        raise ValueError("summary MAC differs from device or has a block error")
    count=checked_crypt_count(data["SPI_BOOT_CRYPT_CNT"],(out/"security.txt").read_text())
    return dict(schema=2,chip="esp32s3",version=VERSION,mac=a,spi_boot_crypt_cnt=count,
                fields=len(data),unreadable=sum(not x["readable"] for x in data.values()),
                files={n:sha256(out/n) for n in FILES},flash_authorized=False)

def capture(port,out,runner=run_logged,before="default-reset"):
    if before not in ("default-reset","no-reset"):
        raise ValueError("unsupported reset mode")
    out.mkdir(mode=0o700,exist_ok=False)
    base=[sys.executable,"-m","esptool"]
    runner(base+["version"],out/"version.txt")
    if not re.search(r"\bv?5\.1\.0\b",(out/"version.txt").read_text()):
        raise ValueError("esptool 5.1.0 required")
    mac=base+["--chip","esp32s3","--port",port,"--before",before,"--after","no-reset","read-mac"]
    runner(mac,out/"mac-before.txt")
    runner([sys.executable,"-m","espefuse","--chip","esp32s3","--port",port,"--before",before,
            "summary","--format","json","--file",str(out/"summary.json")],out/"summary.log")
    runner(mac[:-1]+["get-security-info"],out/"security.txt")
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
    changed={k for k in x.keys()|y.keys() if x.get(k)!=y.get(k)}
    if a["spi_boot_crypt_cnt"]!=b["spi_boot_crypt_cnt"]:
        changed.add("SPI_BOOT_CRYPT_CNT")
    changed=sorted(changed)
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
