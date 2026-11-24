#!/usr/bin/env python3
"""Create/verify a local, unapproved K151 bench candidate. Never accesses serial."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from stackchan_review import firmware_evidence

NOTICE = """EXPERIMENTAL K151 BENCH CANDIDATE -- NOT APPROVED FOR FLASH
This package has three compiled images, not a complete flash image.
No OTA selection data, factory image, installer or restore command is included.
The partition layout is experimental. Verify the original device backup,
current security state, actual layout and recovery procedure before any write.
Passing package verification does not authorize flashing.
"""

def package(bins, out, commit):
    evidence=firmware_evidence(bins,commit)
    # Fail if output exists, including partial packages from earlier attempts.
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    try:
        for item in evidence["files"]:
            src=bins/item["name"]
            with src.open("rb") as f, (out/item["name"]).open("xb") as dest:
                shutil.copyfileobj(f,dest)
        if firmware_evidence(out,commit)!=evidence:
            raise ValueError("copied image changed")
        (out/"READ-ME-NOT-FOR-FLASH.txt").write_text(NOTICE,encoding="utf-8")
        with (out/"manifest.json").open("x",encoding="utf-8") as f:
            json.dump(evidence,f,indent=2);f.write("\n")
        return verify_package(out)
    except BaseException:
        # Incomplete output is deliberately retained for investigation.
        (out/"manifest.json").unlink(missing_ok=True)
        raise

def verify_package(out):
    mpath=out/"manifest.json"
    notice=out/"READ-ME-NOT-FOR-FLASH.txt"
    if mpath.is_symlink() or notice.is_symlink():
        raise ValueError("symbolic links not accepted")
    m=json.loads(mpath.read_text(encoding="utf-8"))
    expected=firmware_evidence(out,m["source_commit"])
    if expected!=m:
        raise ValueError("manifest or firmware hash mismatch")
    if notice.read_text(encoding="utf-8")!=NOTICE:
        raise ValueError("missing or changed safety notice")
    names={x["name"] for x in expected["files"]}|{"manifest.json",notice.name}
    if {p.name for p in out.iterdir()}!=names:
        raise ValueError("unexpected package contents")
    return expected

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    c=sub.add_parser("create")
    c.add_argument("--bins",type=Path,required=True)
    c.add_argument("--out",type=Path,required=True)
    c.add_argument("--commit",required=True)
    v=sub.add_parser("verify")
    v.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    os.umask(0o077)
    try:
        m=package(a.bins,a.out,a.commit) if a.action=="create" else verify_package(a.out)
        print(json.dumps(m,indent=2))
        print("Integrity verified; NOT APPROVED FOR FLASH.")
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0
if __name__=="__main__":
    sys.exit(main())
