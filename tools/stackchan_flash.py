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
import time
from stackchan_backup import run_logged, mac_of, parse_table, TABLE_BYTES
from stackchan_efuse import capture, compare, verify, fields, read_json, checked_crypt_count
from stackchan_review import security_state
from stackchan_deploy_review import plan, readback, checkpoints

# Only maintainers can add independently audited (commit, bootloader, app,
# partition table, initial OTA data) tuples. No CLI override.
# The bb5234e candidate is withdrawn after the owner's GDMA boot-loop.
# Exact DMA-fix candidate reviewed from build run 45581224571 and ELF audit
# 45584713403. Bounded static review and supervised ROM-only install;
# DMA-fix startup was subsequently confirmed by the owner.
# Landscape B6: exact archived build 45675596329, audit 45726785560.
# Bounded static review of known MMIO and ROM references; hardware untested.
# B8: archived build 45824080265 and exact ELF audit 45826383469.
# Bounded comparison of known eFuse read paths against B6; hardware untested.
# B10: archived build 45838322365 and exact ELF audit 45839829181.
# Bounded comparison against B8, supervised ROM-only install; hardware pending.
# B11: archived build 45861451180, fixed ELF audit 45864574356.
# Bounded reference-function comparison to B10; supervised ROM-only install.
# B11l: archived build 45931554248, fixed ELF audit 45933053881.
# Bounded reference-function comparison to B11; supervised ROM-only install.
# B11m: archived build 45945886585, exact ELF audit 45956353073.
# Owner reports 0/5 battery cold starts; withdraw from new writes pending diagnosis.
# Retain only for read-only verification of an existing installation.
# Retain the previously approved tuples for supervised recovery.
APPROVED_BUILDS=frozenset({(
    "871e6d8851c6b7348bbf5a0d71a80affa10e1e32",
    "2b96dbdd514a69af17c2d6425de8cc10939051e3a03462ae4a2c6ffc1249f512",
    "504181669538c9de2b8a866fb62ff5e44ec8cb6c744dfd9127fedf5a9270e05b",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
),(
    "01266e011f68e7e4c78c093efb0d4f882b70ee45",
    "f544e71912a4ef440c8f428ac6fd1b5cc1cb1c5bd3b6a007cf267f0dea5fb648",
    "379d3e349cb0d8cfc5cec0b9014d7ed387558530ade8e4a034a1f0d82d9c554a",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
),(
    "a3e4428e7f82ed450450a45c8550dc701de4e48b",
    "35c75da84b1221eaa0e345b0229ff2f4bbcc11e31d17150747f13c223c47e9cb",
    "ae2c6b9bfd38a5ef2c74b5ca62fefd94876297e2d9e4080c3ae4e26eed7d9312",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
),(
    "54d9a27d2e735ba8b051aaa44aed9de79096a97b",
    "0a33b61168e1e18b4bd846aa833a85326a321e67ec6dc0a92342d3ec8b61976f",
    "273f5a4bc7098b2c11b231f31c54a717cd68d1f8d866ea3c62ae0eae220ba707",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
),(
    "0bb39e5292d712007612b248ac005dac1bfc558b",
    "eb607f98fd500ebaeb5c6da9649d98458e8f8601a5e6a2525c25e694c8cdfc91",
    "8ac9ac7aea76f77f0bfb21e6563b70abef424ee535b43f3ab169eb52c154e707",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
),(
    "e21c476b278544793f9ecd56ff770c0f30cae1f8",
    "6de5b257f7d66b1662fd5db3eb836508675e89f575883c420842ceebf82696f1",
    "b9d4470ee0c4ac7053a8b6ff388e1760db76bc51bbf8efbbd2b2f4f853e9a54a",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",

)})
# Previously approved images may still be verified, read-only.
CHECKPOINT_BUILDS=frozenset({(
    "bb5234ef25ca5903309028b76afcbc29dc414011",
    "8a7d2bb8a3ea22e1b8d9d44c2ec0e965727231066feda335234a16ac8ea0de0a",
    "d0d54b1feab01787a8b36f606b00f29ede2f4375d5b8b1c48577a83b8644ed2b",
    "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
    "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
),(
    "d830ac15cc1761aa421b33035ccfa0bb5f93fd1c",
    "89a958cdeb364677fb217072750fe3b6c2c7ca00e6bf8d5fb6398ff2696316d8",
    "4a8a63d4166d8d058389cc469519c6f0ccae315a6939cadaae64e6c7f0532ea5",
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

# Display only transfer telemetry, never private MAC/eFuse/flash logs.
# esptool 5.1.0 emits CR/LF progress lines with a decimal percentage.
TRANSFER_PROGRESS = re.compile(
    rb"(Writing at|Reading from) (0x[0-9a-fA-F]+)\s+\[[=> ]+\]\s+(\d{1,3}(?:\.\d+)?)%")
class TransferProgress:
    def __init__(self, emit):
        self.emit=emit
        self.pending=b""
        self.last=None

    def feed(self, data):
        records=re.split(rb"[\r\n]",self.pending+data)
        self.pending=records.pop()
        # With CR-only compact output the newest line is displayed on the next
        # update; final flush handles any trailing non-newline output.
        if len(self.pending)>16384:
            self.pending=self.pending[-16384:]
        for line in records:
            self.line(line)

    def line(self,line):
        m=TRANSFER_PROGRESS.search(line)
        if not m:return
        pct=float(m[3])
        if not 0<=pct<=100:return
        kind=m[1].decode()
        # esptool restarts percentages for each image. Do not combine them
        # into an invented overall byte/elapsed-time percentage.
        bucket=int(pct)//5
        if self.last and self.last[0]==kind and self.last[1]==bucket and pct>=self.last[2]:
            return
        self.last=(kind,bucket,pct)
        self.emit(f"{kind} {m[2].decode()}  {pct:5.1f}%")

    def finish(self):
        self.line(self.pending)
        self.pending=b""

def progress_message(message):
    print(message,file=sys.stderr,flush=True)

def run_transfer_logged(args,path,emit=progress_message,timeout=1800):
    # Non-transfer logs use the unchanged private runner.
    if not any(a in ("write-flash","read-flash") for a in args):
        return run_logged(args,path)
    progress=TransferProgress(emit)
    deadline=time.monotonic()+timeout
    # Keep exact raw logs and exclusive creation; file output avoids pipe
    # deadlocks. Poll only complete output bytes, no command/serial changes.
    with path.open("xb") as dst, path.open("rb") as src:
        with subprocess.Popen(args,stdout=dst,stderr=subprocess.STDOUT,
                              env={**os.environ,"NO_COLOR":"1","PYTHONUNBUFFERED":"1"}) as proc:
            try:
                while True:
                    progress.feed(src.read())
                    remaining=deadline-time.monotonic()
                    if remaining<=0:
                        raise subprocess.TimeoutExpired(args,timeout)
                    try:
                        rc=proc.wait(timeout=min(0.2,remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
                progress.feed(src.read())
                progress.finish()
            except BaseException:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
                raise
    if rc:
        raise RuntimeError(f"command failed; inspect {path.name}")
    return path.read_text(encoding="utf-8",errors="replace")

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

def install(candidate,port,out,confirm,runner=run_logged,snapshot=capture,progress=lambda _:None):
    candidate=candidate.resolve();out=out.absolute()
    p=plan(candidate)
    require_approved(p) # MUST precede serial connection, even in CLI.
    if not confirm:
        raise ValueError("explicit installation acknowledgement required")
    progress('[1/5] Preflight: device identity, security and partition checks')
    p2,baseline=probe(candidate,port,out,runner,snapshot)
    if p!=p2:raise ValueError("candidate changed")
    # Stage exact verified bytes privately, then revalidate the staged package.
    progress("[2/5] Stage verified files and recheck partition table")
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
    progress("[3/5] Write Flash: per-image transfer percentages")
    runner(rom_write_command(port)+args,out/"write.log")
    # No hard reset. Operator must hold the device in download mode until
    # readback and the second eFuse capture complete.
    progress("[4/5] Read back and verify all four regions")
    rb=out/"readback";rb.mkdir(mode=0o700)
    for i,r in enumerate(p["regions"]):
        run(["read-flash",hex(r["offset"]),hex(r["size"]),str(rb/r["name"])],f"readback-{i}.log")
    readback(staged,rb)
    progress("[5/5] Compare eFuse snapshots (read-only)")
    snapshot(port,out/"after-write",runner=runner,before="no-reset")
    result=compare(out/"before",out/"after-write")
    if result["changed_fields"]:raise ValueError("eFuse changed; stop")
    (out/"write-verified.json").write_text(json.dumps(result,indent=2))
    progress("100% - installation and named eFuse comparison completed; first boot pending")
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
            probe(a.candidate,a.port,a.out,runner=run_transfer_logged)
            print("Read-only checks passed; no write authorized.")
        elif a.action=="install":
            print(json.dumps(install(a.candidate,a.port,a.out,a.acknowledge_download_mode,
                                     runner=run_transfer_logged,progress=progress_message),indent=2))
        else:print(json.dumps(after_boot(a.port,a.out),indent=2))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0

if __name__=="__main__":sys.exit(main())
