#!/usr/bin/env python3
"""Read-only K151 flash archive; never grants permission to flash/restore."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

FLASH_BYTES = 16 * 1024 * 1024
TABLE_OFFSET = 0x8000
TABLE_BYTES = 0xC00
ARCHIVE = "factory-flash.bin"
COPY = "factory-flash-second.bin"
REPORTS = ("security.txt", "flash-id.txt", "mac-before.txt", "mac-after.txt",
           "read-first.txt", "read-second.txt", "tool-version.txt", "partitions.json")
MAC = re.compile(r"\bMAC\s*:\s*((?:[0-9a-f]{2}:){5}[0-9a-f]{2})\b", re.I)


def sha256(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def parse_table(raw):
    """Recognize only the usual plaintext ESP-IDF table, with valid MD5."""
    entries = []
    for pos in range(0, len(raw), 32):
        block = raw[pos:pos + 32]
        if len(block) != 32:
            break
        magic, = struct.unpack_from("<H", block)
        if magic == 0xEBEB:
            if block[2:16] != b"\xff" * 14 or block[16:] != hashlib.md5(raw[:pos]).digest():
                raise ValueError("partition table MD5 mismatch")
            if not entries or any(x != 0xff for x in raw[pos+32:]):
                raise ValueError("invalid table terminator")
            return entries
        if magic != 0x50AA:
            break
        _, kind, subtype, offset, size, label, flags = struct.unpack("<HBBII16sI", block)
        if not size or offset % 4096 or size % 4096 or offset < 0x9000 or offset + size > FLASH_BYTES:
            raise ValueError("invalid partition bounds")
        if kind == 0 and offset % 65536:
            raise ValueError("unaligned app partition")
        if any(offset < p["offset"] + p["size"] and p["offset"] < offset + size for p in entries):
            raise ValueError("overlapping partitions")
        name = label.split(b"\x00", 1)[0].decode("ascii")
        if not name or any(ord(c) < 32 or ord(c) > 126 for c in name):
            raise ValueError("invalid partition label")
        entries.append(dict(label=name, type=kind, subtype=subtype, offset=offset, size=size, flags=flags))
    raise ValueError("no verified plaintext partition table at standard offset")


def partition_report(image):
    with image.open("rb") as f:
        f.seek(TABLE_OFFSET)
        raw = f.read(TABLE_BYTES)
    try:
        return dict(offset=TABLE_OFFSET, status="candidate-md5-valid", entries=parse_table(raw))
    except (ValueError, UnicodeError) as exc:
        return dict(offset=TABLE_OFFSET, status="unverified", reason=str(exc), entries=[])


def run_logged(args, path):
    with path.open("x", encoding="utf-8") as f:
        result = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT, timeout=1800,
                                env={**os.environ, "NO_COLOR": "1"})
    if result.returncode:
        raise RuntimeError(f"command failed; inspect {path.name}")
    return path.read_text(encoding="utf-8", errors="replace")


def mac_of(report):
    values = {m.lower() for m in MAC.findall(report)}
    if len(values) != 1:
        raise ValueError("could not uniquely identify device MAC")
    return values.pop()


def capture(port, out, baud=115200, runner=run_logged):
    # Unique directory, private permissions, no overwrite; incomplete captures
    # retain their logs but never receive a success manifest.
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    prefix = [sys.executable, "-m", "esptool"]
    ver = runner(prefix + ["version"], out / "tool-version.txt")
    if not re.search(r"\bv?5\.\d+\.\d+\b", ver):
        raise ValueError("esptool 5.x required")
    cmd = prefix + ["--chip", "esp32s3", "--port", port, "--baud", str(baud),
                    "--before", "default-reset", "--after", "no-reset"]
    def read_command(args, report):
        return runner(cmd + args, out / report)
    before = mac_of(read_command(["read-mac"], "mac-before.txt"))
    read_command(["get-security-info"], "security.txt")
    flash = read_command(["flash-id"], "flash-id.txt")
    if not re.search(r"Detected flash size:\s*16\s*MB\b", flash, re.I):
        raise ValueError("expected detected flash size of 16 MB")
    for name, log in [(ARCHIVE, "read-first.txt"), (COPY, "read-second.txt")]:
        read_command(["read-flash", "0x0", hex(FLASH_BYTES), str(out / name)], log)
        if (out / name).stat().st_size != FLASH_BYTES:
            raise ValueError("incomplete flash read")
    after = mac_of(read_command(["read-mac"], "mac-after.txt"))
    if before != after:
        raise ValueError("device identity changed")
    digest = sha256(out / ARCHIVE)
    if digest != sha256(out / COPY):
        raise ValueError("flash reads differ; keep both for inspection")
    # A matching pair alone is not a valid boot image or a restorable backup.
    report = partition_report(out / ARCHIVE)
    (out / "partitions.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest = dict(schema=1, created=dt.datetime.now(dt.timezone.utc).isoformat(),
                    chip="esp32s3", bytes=FLASH_BYTES, mac=before,
                    status="matching-reads-review-required", restore_authorized=False,
                    files={name: sha256(out / name) for name in (ARCHIVE,COPY,*REPORTS)})
    tmp=out / "manifest.pending"
    tmp.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    tmp.rename(out / "manifest.json")
    return manifest


def verify(out):
    m=json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if (m.get("schema") != 1 or m.get("chip") != "esp32s3" or m.get("bytes") != FLASH_BYTES
            or m.get("status") != "matching-reads-review-required" or m.get("restore_authorized") is not False):
        raise ValueError("unrecognized archive manifest")
    names={ARCHIVE,COPY,*REPORTS}
    if set(m["files"]) != names:
        raise ValueError("archive file list mismatch")
    for name in names:
        p=out/name
        if p.is_symlink() or sha256(p)!=m["files"][name]:
            raise ValueError(f"archive hash mismatch: {name}")
    if any((out / n).stat().st_size != FLASH_BYTES for n in (ARCHIVE,COPY)):
        raise ValueError("archive image size mismatch")
    if m["files"][ARCHIVE]!=m["files"][COPY]:
        raise ValueError("archive copies differ")
    if any(mac_of((out / n).read_text(encoding="utf-8")) != m["mac"]
           for n in ("mac-before.txt","mac-after.txt")):
        raise ValueError("archive device identity mismatch")
    if json.loads((out/"partitions.json").read_text(encoding="utf-8")) != partition_report(out/ARCHIVE):
        raise ValueError("partition report mismatch")
    return m


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    c=sub.add_parser("capture")
    c.add_argument("--port",required=True)
    c.add_argument("--out",required=True,type=Path)
    c.add_argument("--baud",type=int,choices=(115200,230400,460800),default=115200)
    v=sub.add_parser("verify")
    v.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    os.umask(0o077)
    try:
        m=capture(a.port,a.out,a.baud) if a.action=="capture" else verify(a.out)
        print("Archive integrity OK; security/layout review required. No restore authorized.")
        print("SHA256:",m["files"][ARCHIVE])
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
