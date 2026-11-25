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
from stackchan_efuse import capture, compare, verify, fields, read_json, checked_crypt_count
from stackchan_review import security_state
from stackchan_deploy_review import plan, readback, checkpoints

# Only maintainers can add independently audited (commit, bootloader, app,
# partition table, initial OTA data) tuples. No CLI override.
# The bb5234e candidate is withdrawn after the owner's GDMA boot-loop.
# Keep writes locked until the exact DMA-fix candidate is reviewed.
APPROVED_BUILDS=frozenset()
# Previously approved images may still be verified, read-only.
CHECKPOINT_BUILDS=frozenset({(
    "bb5234ef25ca5903309028b76afcbc29dc414011",
    "8a7d2bb8a3ea22e1b8d9d44c2ec0e965727231066feda335234a16ac8ea0de0a",
    "d0d54b1feab01787a8b36f606b00f29ede2f4375d5b8b1c48577a83b8644ed2b",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
)})

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
            "--baud","115200","--before","no-reset","--after","no-reset","--no-stub"]

# esptool 5.1.0 write_flash() otherwise retries a lost serial connection
# via esp.connect() with the default reset mode. Stop on disconnection.
# This fixed launcher is used only after the existing build approval gate.
ROM_WRITE_LAUNCHER = """import esptool
from esptool.targets.esp32s3 import ESP32S3ROM
if esptool.__version__ != "5.1.0":
    raise SystemExit("esptool 5.1.0 required")
ESP32S3ROM.WRITE_FLASH_ATTEMPTS = 1
esptool.main()
"""

def rom_write_command(port):
    cmd=serial_prefix(port)
    return [sys.executable,"-c",ROM_WRITE_LAUNCHER,*cmd[3:]]

def probe(candidate,port,out,runner=run_logged,snapshot=capture):
    candidate=candidate.resolve();out=out.absolute()
    p=plan(candidate)
    cmd=serial_prefix(port)
    out.mkdir(mode=0o700,exist_ok=False)
    baseline=snapshot(port,out/"before",runner=runner,before="no-reset")
    def run(args,name):
        return runner(cmd+args,out/name)
    if mac_of(run(["read-mac"],"mac-probe.txt"))!=baseline["mac"]:
        raise ValueError("different device")
    info=run(["get-security-info"],"security.txt")
    if any(security_state(info,k)!="disabled" for k in ("Secure Boot","Flash Encryption")):
        raise ValueError("device security enabled or unknown")
    data=fields(out/"before"/"summary.json")
    row=data["SECURE_BOOT_EN"]
    if not row["readable"] or type(row["value"]) not in (bool,int) or row["value"]!=0:
        raise ValueError("security eFuse nonzero or unknown: SECURE_BOOT_EN")
    count=checked_crypt_count(data["SPI_BOOT_CRYPT_CNT"],info)
    if count!=0 or baseline["spi_boot_crypt_cnt"]!=0:
        raise ValueError("security eFuse nonzero: SPI_BOOT_CRYPT_CNT (raw count must be zero)")
    flash=run(["flash-id"],"flash-id.txt")
    if not re.search(r"Detected flash size:\s*16\s*MB\b",flash,re.I):
        raise ValueError("expected 16 MiB flash")
    table=out/"current-partitions.bin"
    compiled_table=(candidate/"TamaPoke.ino.partitions.bin").read_bytes()
    run(["read-flash","0x8000",hex(len(compiled_table)),str(table)],"partitions.log")
    if table.stat().st_size!=len(compiled_table):
        raise ValueError("incomplete device partition table")
    actual=parse_table(table.read_bytes()[:TABLE_BYTES])
    expected=parse_table(compiled_table[:TABLE_BYTES])
    if mac_of(run(["read-mac"],"mac-probe-end.txt"))!=baseline["mac"]:
        raise ValueError("different device")
    if plan(candidate)!=p:
        raise ValueError("candidate changed during preflight")
    # Shareable layout-only report: no MAC, key values or raw eFuse contents.
    report=dict(schema=1,source_commit=p["source_commit"],chip="esp32s3",
                flash_bytes=p["flash_bytes"],secure_boot="disabled",flash_encryption="disabled",
                spi_boot_crypt_cnt=count,
                layout_matches=actual==expected,table_bytes_match=table.read_bytes()==compiled_table,
                current_partitions=actual,
                candidate_partitions=expected,flash_authorized=False,efuse_write_allowed=False)
    with (out/"layout-report.json").open("x",encoding="utf-8") as dst:
        json.dump(report,dst,indent=2)
    if actual!=expected:
        raise ValueError("device layout differs; migration is not authorized; inspect layout-report.json")
    if not report["table_bytes_match"]:
        raise ValueError("device partition table bytes differ; inspect layout-report.json; no write")
    return p,baseline

def install(candidate,port,out,confirm,runner=run_logged,snapshot=capture):
    candidate=candidate.resolve();out=out.absolute()
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
    # Never rewrite the partition table. Verify its exact candidate-length
    # bytes again on the same device before any flash write.
    table_name="TamaPoke.ino.partitions.bin"
    expected_table=(staged/table_name).read_bytes()
    if (out/"current-partitions.bin").read_bytes()!=expected_table:
        raise ValueError("existing partition table differs byte-for-byte; no write")
    latest=out/"partitions-before-write.bin"
    run(["read-flash","0x8000",hex(len(expected_table)),str(latest)],"partitions-before-write.log")
    if latest.read_bytes()!=expected_table:
        raise ValueError("partition table changed before write")
    args=["write-flash","--flash-mode","keep","--flash-freq","keep","--flash-size","keep"]
    for r in p["regions"]:
        if r["name"]!=table_name:
            args.extend([hex(r["offset"]),str(staged/r["name"])])
    runner(rom_write_command(port)+args,out/"write.log")
    # No hard reset. Operator must hold the device in download mode until
    # readback and the second eFuse capture complete.
    rb=out/"readback";rb.mkdir(mode=0o700)
    for i,r in enumerate(p["regions"]):
        run(["read-flash",hex(r["offset"]),hex(r["size"]),str(rb/r["name"])],f"readback-{i}.log")
    readback(staged,rb)
    snapshot(port,out/"after-write",runner=runner,before="no-reset")
    result=compare(out/"before",out/"after-write")
    if result["changed_fields"]:raise ValueError("eFuse changed; stop")
    (out/"write-verified.json").write_text(json.dumps(result,indent=2))
    return result

def after_boot(port,out,runner=run_logged,snapshot=capture):
    serial_prefix(port)
    out=out.absolute()
    if out.is_symlink() or not (out/"write-verified.json").is_file():
        raise ValueError("missing completed write verification")
    if identity(plan(out/"candidate")) not in (APPROVED_BUILDS | CHECKPOINT_BUILDS):
        raise ValueError("unknown historical installation tuple")
    readback(out/"candidate",out/"readback")
    verify(out/"before");verify(out/"after-write")
    if compare(out/"before",out/"after-write")["changed_fields"]:
        raise ValueError("eFuse changed before boot")
    snapshot(port,out/"after-boot",runner=runner,before="no-reset")
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
