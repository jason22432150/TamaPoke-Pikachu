#!/usr/bin/env python3
"""Generate a compact Unifont subset for all marked Traditional Chinese strings."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def required_chars():
    chars=set(range(32,127))
    for name in ("i18n.cpp","dex.h"):
        source=(ROOT/"TamaPoke"/name).read_text(encoding="utf-8")
        blocks=re.findall(r"// ZH_TW_FONT_BEGIN(.*?)// ZH_TW_FONT_END",source,re.S)
        if not blocks:
            raise ValueError("Missing translation blocks: "+name)
        chars.update(ord(c) for block in blocks for c in block if ord(c)>127)
    return chars

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--u8g2",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    src=a.u8g2.resolve()
    expected="46b7f48bcb7bde787d214352873fba9baeccfb71"
    actual=subprocess.check_output(["git","-C",str(src),"rev-parse","HEAD"],text=True).strip()
    if actual!=expected:
        raise SystemExit("Unexpected U8g2 font source revision")
    bdf=src/"tools/font/bdf/unifont.bdf"
    codepoints=required_chars()
    encodings={int(m) for m in re.findall(r"^ENCODING (\d+)$",bdf.read_text(encoding="ascii",errors="replace"),re.M)}
    missing=codepoints-encodings
    if missing:
        raise SystemExit("Missing glyphs: "+" ".join(f"U+{c:04X}" for c in sorted(missing)))
    conv=src/"tools/font/bdfconv"
    subprocess.run(["make","-C",str(conv),"bdfconv"],check=True)
    mapping=",".join(map(str,sorted(codepoints)))
    with tempfile.TemporaryDirectory() as tmp:
        output=Path(tmp)/"font.c"
        subprocess.run([str(conv/"bdfconv"),"-f","1","-m",mapping,
                        "-n","tpk_zh_tw_font","-o",str(output),str(bdf)],check=True,cwd=tmp)
        data=output.read_text(encoding="utf-8")
        match=re.search(r"Glyphs:\s*(\d+)/",data)
        if not match or int(match.group(1))!=len(codepoints):
            raise SystemExit("Generated font glyph count mismatch")
        if "const uint8_t tpk_zh_tw_font[" not in data:
            raise SystemExit("Unexpected generated font format")
        a.out.write_text("#pragma once\n"+data,encoding="utf-8")
    print(f"Generated Traditional Chinese font: {len(codepoints)} glyphs")
if __name__=="__main__":
    main()
