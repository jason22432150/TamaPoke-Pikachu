#!/usr/bin/env python3
"""Offline deployment evidence only; no serial commands or flash authorization."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import re
import subprocess
import struct
import tempfile
from stackchan_merge import assemble,SECTOR
from stackchan_efuse import compare,verify
from stackchan_package import verify_package
from stackchan_backup import sha256

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

FORBIDDEN=("CONFIG_SECURE_BOOT","CONFIG_SECURE_BOOT_V2_ENABLED",
           "CONFIG_SECURE_FLASH_ENC_ENABLED","CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK",
           "CONFIG_SECURE_DISABLE_ROM_DL_MODE","CONFIG_SECURE_ENABLE_SECURE_ROM_DL_MODE")

def check_sdkconfig(path):
    settings={}
    for line in path.read_text(encoding="utf-8").splitlines():
        m=re.fullmatch(r"(CONFIG_[A-Z0-9_]+)=(.*)",line)
        disabled=re.fullmatch(r"# (CONFIG_[A-Z0-9_]+) is not set",line)
        if m or disabled:
            key=m[1] if m else disabled[1]
            value=m[2] if m else "n"
            # Generated Arduino SDK configuration may repeat identical values.
            # Never accept conflicting assignments, including explicit unset.
            if key in settings and settings[key]!=value:
                raise ValueError("conflicting SDK setting: "+key)
            settings[key]=value
    if not settings or settings.get("CONFIG_IDF_TARGET")!='"esp32s3"':
        raise ValueError("expected ESP32-S3 SDK configuration")
    for key in FORBIDDEN:
        if settings.get(key,"n") not in ("n","0"):
            raise ValueError("forbidden SDK configuration: "+key)
    return {k:settings.get(k,"not-defined") for k in FORBIDDEN}

# Names of SDK provisioning and low-level eFuse programming functions.
# This is a symbol inventory, not a call-graph or MMIO safety proof.
EFUSE_WRITER=re.compile(
    r"^(?:(?:esp_efuse|efuse_hal|efuse_ll|esp_rom_efuse|ets_efuse)_"
    r"(?:write|burn|program|set_|update_|disable_|enable_|batch_write|"
    r"utility_(?:burn|write|set_|update_|program|apply))"
    r"|esp_secure_boot(?:_v[12])?_permanently_enable"
    r"|esp_flash_encrypt_(?:init|enable|contents))")

def efuse_symbol_inventory(output,entry):
    code=set();absolute=set();entries=set()
    for line in output.splitlines():
        parts=line.split()
        if len(parts)<3 or len(parts[1])!=1:
            continue
        name,kind=parts[:2]
        if kind in "TtWw":
            entries.add(name)
            if EFUSE_WRITER.match(name):code.add(name)
        elif kind in "Aa" and EFUSE_WRITER.match(name):
            absolute.add(name)
    if entry not in entries:
        raise ValueError("ELF symbol inventory missing entry: "+entry)
    return dict(linked_code_symbols=sorted(code),absolute_symbols=sorted(absolute),
                code_symbol_count=len(entries),entry=entry,
                safety_attested=False,
                warning="Names alone do not establish reachability or rule out inlined/MMIO/ROM writes.")

def rom_write_references(symbols,disassembly,image):
    """Screen explicit disassembly targets and little-endian ROM address literals."""
    addresses={}
    for line in symbols.splitlines():
        parts=line.split()
        if len(parts)>=3 and parts[1] in ("A","a") and EFUSE_WRITER.match(parts[0]):
            addr=int(parts[2],16)
            if not 0<addr<=0xffffffff:
                raise ValueError("unexpected ROM symbol address")
            addresses[parts[0]]=addr
    hits=[]
    instructions=0
    for line in disassembly.splitlines():
        m=re.match(r"^\s*([0-9a-fA-F]+):\s+(\S.*)$",line)
        if not m:
            continue
        instructions+=1
        operand=m[2]
        for name,addr in addresses.items():
            if (re.search(r"(?<![\w.])"+re.escape(name)+r"(?![\w.])",operand)
                or re.search(r"(?<![\w])(?:0x)?"+format(addr,"x")+r"(?![\w])",operand,re.I)):
                hits.append(dict(symbol=name,instruction_address=m[1]))
    if not instructions:
        raise ValueError("empty ELF disassembly")
    literals=[]
    for name,addr in addresses.items():
        needle=struct.pack("<I",addr)
        pos=image.find(needle)
        while pos!=-1:
            literals.append(dict(symbol=name,image_offset=pos))
            pos=image.find(needle,pos+1)
    return dict(disassembly_instruction_count=instructions,
                rom_addresses={k:hex(v) for k,v in sorted(addresses.items())},
                direct_references=hits,address_literals=literals,
                warning="Potential references only; cannot exclude indirect or computed calls, inlining or direct MMIO.")

def inspect_efuse_symbols(nm,elf,entry,image):
    output=subprocess.run([str(nm),"--defined-only","--format=posix",str(elf)],
                          check=True,capture_output=True,text=True).stdout
    report=efuse_symbol_inventory(output,entry)
    objdump=Path(nm).with_name(Path(nm).name.removesuffix("nm")+"objdump")
    disassembly=subprocess.run([str(objdump),"-d","--no-show-raw-insn",str(elf)],
                                check=True,capture_output=True,text=True).stdout
    report["rom_references"]=rom_write_references(output,disassembly,image.read_bytes())
    report["elf_sha256"]=sha256(elf)
    report["image_sha256"]=sha256(image)
    return report

def boot_evidence(properties,build_dir,bins,source_commit):
    """Reproduce the Arduino platform ELF conversion, not a bootloader safety attestation."""
    props={}
    for line in properties.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k,v=line.split("=",1)
            props[k]=v
    if props["build.mcu"]!="esp32s3" or props["build.bootloader_addr"]!="0x0":
        # Arduino may use a longer representation of zero.
        if props["build.mcu"]!="esp32s3" or int(props["build.bootloader_addr"],0)!=0:
            raise ValueError("wrong bootloader target")
    if props["build.flash_size"]!="16MB":raise ValueError("wrong flash size")
    if Path(props["runtime.platform.path"]).name!="4.0.0":
        raise ValueError("expected Arduino ESP32 4.0.0")
    sdk=Path(props["compiler.sdk.path"])
    variant=Path(props["build.variant.path"])
    sketch=Path(props["build.source.path"])
    if (sketch/"bootloader.bin").exists() or (variant/(props["build.custom_bootloader"]+".bin")).exists():
        raise ValueError("unexpected custom bootloader")
    elf=sdk/"bin"/("bootloader_"+props["build.boot"]+"_"+props["build.boot_freq"]+".elf")
    config=sdk/"sdkconfig"
    if sha256(config)!=sha256(build_dir/"sdkconfig"):
        raise ValueError("copied SDK configuration differs")
    settings=check_sdkconfig(config)
    boot=bins/"TamaPoke.ino.bootloader.bin"
    nm=Path(props["compiler.path"])/(props["compiler.prefix"]+"nm")
    app_elf=build_dir/"TamaPoke.ino.elf"
    app_symbols=inspect_efuse_symbols(nm,app_elf,"app_main",bins/"TamaPoke.ino.bin")
    with tempfile.TemporaryDirectory() as tmp:
        image=Path(tmp)/"boot.bin"
        subprocess.run([str(Path(props["tools.esptool_py.path"])/props["tools.esptool_py.cmd"]),
                        "--chip","esp32s3","elf2image","--flash-mode",props["build.flash_mode"],
                        "--flash-freq",props["build.img_freq"],"--flash-size",props["build.flash_size"],
                        "-o",str(image),str(elf)],check=True)
        if image.read_bytes()!=boot.read_bytes():
            raise ValueError("bootloader differs from reproduced ELF conversion")
    return dict(schema=1,source_commit=source_commit,arduino_core="4.0.0",
                sdk_config_sha256=sha256(config),bootloader_elf_name=elf.name,
                bootloader_elf_sha256=sha256(elf),bootloader_bin_sha256=sha256(boot),
                app_sha256=sha256(bins/"TamaPoke.ino.bin"),sdk_security_settings=settings,
                application_efuse_symbols=app_symbols,
                elf_conversion_matches=True,bootloader_security_attested=False,
                flash_authorized=False,warning="SDK config and ELF provenance are not proof of bootloader build configuration or eFuse behavior.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="action",required=True)
    a=s.add_parser("plan");a.add_argument("--candidate",type=Path,required=True)
    b=s.add_parser("readback");b.add_argument("--candidate",type=Path,required=True);b.add_argument("--readback",type=Path,required=True)
    c=s.add_parser("checkpoints")
    for name in ("before","after-write","after-boot"):c.add_argument("--"+name,type=Path,required=True)
    d=s.add_parser("boot-evidence")
    for key in ("properties","build-dir","bins","report"):d.add_argument("--"+key,type=Path,required=True)
    d.add_argument("--commit",required=True)
    a=p.parse_args()
    try:
        if a.action=="plan":r=plan(a.candidate)
        elif a.action=="readback":r=readback(a.candidate,a.readback)
        elif a.action=="checkpoints":r=checkpoints(a.before,a.after_write,a.after_boot)
        else:
            r=boot_evidence(a.properties,a.build_dir,a.bins,a.commit)
            with a.report.open("x",encoding="utf-8") as f:json.dump(r,f,indent=2)
        print(json.dumps(r,indent=2))
        return 2 if r.get("status")=="changed" else 0
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1

if __name__=="__main__":sys.exit(main())
