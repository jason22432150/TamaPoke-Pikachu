#!/usr/bin/env python3
"""Deterministic full K151 assets partition image; no device access."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
NAME="tamapoke_assets.bin"
SIZE=0x400000
COUNT=303
HEADER=struct.Struct("<4sIII")
ENTRY=struct.Struct("<III")
START=HEADER.size+COUNT*ENTRY.size
SPECIES=tuple(range(1,10))+(25,26)
IDS=(0,)+SPECIES+tuple(151+n for n in SPECIES)

def filename(i):
    if i==0:return "mons/thumbs.bin"
    return f"mons/p{'s' if i>151 else ''}{i-151 if i>151 else i:03d}.bin"

def check_payload(i,data):
    if i==0:
        if not 10<=len(data)<=2*1024*1024 or data[:4]!=b"TPTH":
            raise ValueError("invalid thumbnail asset")
    elif not 7<=len(data)<=3*1024*1024 or data[:4]!=b"TPK2":
        raise ValueError("invalid sprite asset")

def build_image(items):
    if set(items)!=set(IDS):raise ValueError("unexpected asset set")
    image=bytearray(b"\xff"*SIZE)
    HEADER.pack_into(image,0,b"TPAS",1,COUNT,START)
    image[HEADER.size:START]=bytes(START-HEADER.size)
    pos=START
    for i in sorted(items):
        data=items[i];check_payload(i,data)
        if len(data)>SIZE-pos:raise ValueError("assets partition overflow")
        ENTRY.pack_into(image,HEADER.size+i*ENTRY.size,pos,len(data),zlib.crc32(data))
        image[pos:pos+len(data)]=data
        pos+=len(data)
    return bytes(image)

def verify_image(data):
    if len(data)!=SIZE or HEADER.unpack_from(data)!=(b"TPAS",1,COUNT,START):
        raise ValueError("invalid assets image header or size")
    pos=START
    found=[]
    for i in range(COUNT):
        offset,size,crc=ENTRY.unpack_from(data,HEADER.size+i*ENTRY.size)
        if i not in IDS:
            if (offset,size,crc)!=(0,0,0):raise ValueError("unexpected asset entry")
            continue
        if offset!=pos or not 0<size<=SIZE-pos:raise ValueError("invalid asset bounds")
        payload=data[pos:pos+size];check_payload(i,payload)
        if zlib.crc32(payload)!=crc:raise ValueError("asset CRC mismatch")
        found.append(dict(name=filename(i),size=size,sha256=hashlib.sha256(payload).hexdigest()))
        pos+=size
    if data[pos:]!=b"\xff"*(SIZE-pos):raise ValueError("unexpected assets padding")
    return dict(format="TPAS-v1",files=found,used_bytes=pos,capacity=SIZE)

def source_assets(root=ROOT):
    meta=json.loads((root/"evidence/full-sprite-pack.json").read_text())
    pack=(root/"web/assets/sprites/all-gen1.pak").read_bytes()
    if len(pack)!=meta["bytes"] or hashlib.sha256(pack).hexdigest()!=meta["sha256"]:
        raise ValueError("source sprite pack checksum mismatch")
    if pack[:4]!=b"TPAK":raise ValueError("invalid source pack")
    count,=struct.unpack_from("<H",pack,4)
    if count!=len(meta["files"]):raise ValueError("source pack file count")
    pos=6;entries={}
    for _ in range(count):
        if pos>=len(pack):raise ValueError("truncated source index")
        n=pack[pos];pos+=1
        if not n or pos+n+4>len(pack):raise ValueError("invalid source index")
        name=pack[pos:pos+n].decode("ascii");pos+=n
        size,=struct.unpack_from("<I",pack,pos);pos+=4
        if name in entries or not size:raise ValueError("duplicate or empty source asset")
        entries[name]=size
    expected={f["name"]:f for f in meta["files"]}
    if set(entries)!=set(expected):raise ValueError("source index differs")
    selected={filename(i):i for i in IDS};items={}
    for name,size in entries.items():
        data=pack[pos:pos+size];pos+=size
        if len(data)!=size or size!=expected[name]["bytes"] or hashlib.sha256(data).hexdigest()!=expected[name]["sha256"]:
            raise ValueError("source asset checksum mismatch: "+name)
        if name in selected:items[selected[name]]=data
    if pos!=len(pack):raise ValueError("source pack trailing bytes")
    return items

if __name__=="__main__":
    out=Path(sys.argv[1])
    image=build_image(source_assets())
    report=verify_image(image)
    with out.open("xb") as f:f.write(image)
    print(json.dumps(report,indent=2))
