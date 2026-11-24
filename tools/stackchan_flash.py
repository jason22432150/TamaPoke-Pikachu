#!/usr/bin/env python3
"""K151 Alpha installer. Unapproved builds cannot reach the flash write path."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from stackchan_backup import run_logged, mac_of, parse_table, TABLE_BYTES
from stackchan_efuse import capture, compare, verify, fields, read_json
from stackchan_review import security_state
from stackchan_deploy_review import plan, readback, checkpoints

# Only maintainers can add independently audited (commit, bootloader, app,
# partition table, initial OTA data) tuples. No CLI override. Empty for Alpha.
APPROVED_BUILDS=frozenset()

def identity(p):
    by_name={r["name"]:r["sha256"] for r in p["regions"]}
    return (p["source_commit"],*(by_name[n] for n in (
        "TamaPoke.ino.bootloader.bin","TamaPoke.ino.bin",
        "TamaPoke.ino.partitions.bin","ota_data_initial.bin")))

def require_approved(p):
    if identity(p) not in APPROVED_BUILDS:
        raise ValueError("NOT FOR FLASH: no independently audited build approval")

def serial_prefix(port):
    if not re.fullmatch(r"/dev/(?:cu\.|tty)[A-Za-z0-9_.-]+",port):
        raise ValueError("explicit macOS/Linux serial device path required")
    return [sys.executable,"-m","esptool","--chip","esp32s3","--port",port,
            "--baud","115200","--before","default-reset","--after","no-reset"]

def probe(candidate,port,out,runner=run_logged,snapshot=capture):
    p=plan(candidate)
    cmd=serial_prefix(port)
    out.mkdir(mode=0o700,exist_ok=False)
    baseline=snapshot(port,out/"before",runner=runner)
    def run(args,name):
        return runner(cmd+args,out/name)
    if mac_of(run(["read-mac"],"mac-probe.txt"))!=baseline["mac"]:
        raise ValueError("different device")
    info=run(["get-security-info"],"security.txt")
    if any(security_state(info,k)!="disabled" for k in ("Secure Boot","Flash Encryption")):
        raise ValueError("device security enabled or unknown")
    data=fields(out/"before"/"summary.json")
    for key in ("SECURE_BOOT_EN","SPI_BOOT_CRYPT_CNT"):
        row=data[key]
        if not row["readable"] or type(row["value"]) not in (bool,int) or row["value"]!=0:
            raise ValueError("security eFuse nonzero or unknown: "+key)
    flash=run(["flash-id"],"flash-id.txt")
    if not re.search(r"Detected flash size:\s*16\s*MB\b",flash,re.I):
        raise ValueError("expected 16 MiB flash")
    table=out/"current-partitions.bin"
    run(["read-flash","0x8000",hex(TABLE_BYTES),str(table)],"partitions.log")
    if table.stat().st_size!=TABLE_BYTES:
        raise ValueError("incomplete device partition table")
    if parse_table(table.read_bytes())!=parse_table((candidate/"TamaPoke.ino.partitions.bin").read_bytes()[:TABLE_BYTES]):
        raise ValueError("device layout differs; migration is not authorized")
    if mac_of(run(["read-mac"],"mac-probe-end.txt"))!=baseline["mac"]:
        raise ValueError("different device")
    return p,baseline

def install(candidate,port,out,confirm,runner=run_logged,snapshot=capture):
    p=plan(candidate)
    require_approved(p) # MUST precede serial connection, even in CLI.
    if not confirm:
        raise ValueError("explicit installation acknowledgement required")
    p2,baseline=probe(candidate,port,out,runner,snapshot)
    if p!=p2:raise ValueError("candidate changed")
    # Stage exact verified bytes privately, then revalidate the staged package.
    staged=out/"candidate"
    shutil.copytree(candidate,staged,symlinks=True)
    if plan(staged)!=p:raise ValueError("candidate changed while staging")
    cmd=serial_prefix(port)
    def run(args,name):return runner(cmd+args,out/name)
    if mac_of(run(["read-mac"],"mac-write.txt"))!=baseline["mac"]:
        raise ValueError("different device")
    args=["write-flash","--flash-mode","keep","--flash-freq","keep","--flash-size","keep"]
    for r in p["regions"]:args.extend([hex(r["offset"]),str(staged/r["name"])])
    run(args,"write.log")
    # No hard reset. Operator must hold the device in download mode until
    # readback and the second eFuse capture complete.
    rb=out/"readback";rb.mkdir(mode=0o700)
    for i,r in enumerate(p["regions"]):
        run(["read-flash",hex(r["offset"]),hex(r["size"]),str(rb/r["name"])],f"readback-{i}.log")
    readback(staged,rb)
    snapshot(port,out/"after-write",runner=runner)
    result=compare(out/"before",out/"after-write")
    if result["changed_fields"]:raise ValueError("eFuse changed; stop")
    (out/"write-verified.json").write_text(json.dumps(result,indent=2))
    return result

def after_boot(port,out,runner=run_logged,snapshot=capture):
    if not (out/"write-verified.json").is_file():
        raise ValueError("missing completed write verification")
    verify(out/"before");verify(out/"after-write")
    if compare(out/"before",out/"after-write")["changed_fields"]:
        raise ValueError("eFuse changed before boot")
    snapshot(port,out/"after-boot",runner=runner)
    result=checkpoints(out/"before",out/"after-write",out/"after-boot")
    if result["status"]=="changed":raise ValueError("eFuse changed; stop")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="action",required=True)
    for name in ("probe","install","after-boot"):
        a=s.add_parser(name)
        a.add_argument("--port",required=True)
        a.add_argument("--out",type=Path,required=True)
        if name!="after-boot":a.add_argument("--candidate",type=Path,required=True)
        if name=="install":a.add_argument("--acknowledge-download-mode",action="store_true")
    a=p.parse_args();os.umask(0o077)
    try:
        if a.action=="probe":
            probe(a.candidate,a.port,a.out)
            print("Read-only checks passed; no write authorized.")
        elif a.action=="install":
            print(json.dumps(install(a.candidate,a.port,a.out,a.acknowledge_download_mode),indent=2))
        else:print(json.dumps(after_boot(a.port,a.out),indent=2))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0

if __name__=="__main__":sys.exit(main())
