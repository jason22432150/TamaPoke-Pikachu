#!/usr/bin/env python3
"""Pinned K151 game-only battery startup experiment."""
import argparse
import hashlib
from pathlib import Path

HEADER = Path(__file__).resolve().parents[1] / "boards/stackchan/hal/boost_start_policy.h"
GUARD = b'#if defined(BOARD_STACKCHAN) && BOARD_STACKCHAN\n#include "tpk_k151_boost_start.h"\n#endif\n'
GFX_OLD = b"            m5gfx::i2c::bitOn(i2c_port, aw9523_i2c_addr, 0x03, reg0x03); //port1 output ctrl\n"
GFX_NEW = b"""#if defined(BOARD_STACKCHAN) && BOARD_STACKCHAN
            auto boostRead = [](uint8_t reg, uint8_t& value) {
              auto v=lgfx::i2c::readRegister8(i2c_port,aw9523_i2c_addr,reg,i2c_freq);
              if(!v.has_value())return false;
              value=v.value();return true;
            };
            auto boostWrite = [](uint8_t reg,uint8_t value) {
              return lgfx::i2c::writeRegister8(i2c_port,aw9523_i2c_addr,reg,value,0,i2c_freq).has_value();
            };
            auto boostFail = []() {
              ESP_LOGE(LIBRARY_NAME,"K151 boost init I2C failed; startup stopped");
              for(;;)lgfx::delay(1000);
            };
            if(!tpkboost::prepare(boostRead,boostWrite))boostFail();
            if(!lgfx::i2c::bitOn(i2c_port,aw9523_i2c_addr,0x03,reg0x03&0x7f,i2c_freq).has_value())boostFail();
#else
""" + GFX_OLD + b"#endif\n"
GFX_DIR = b"            m5gfx::i2c::writeRegister8(i2c_port, aw9523_i2c_addr, 0x13, 0b11111111);  // LEDMODE_P1\n"
GFX_START = GFX_DIR + b"""#if defined(BOARD_STACKCHAN) && BOARD_STACKCHAN
            if((reg0x03&0x80)&&!tpkboost::start(boostRead,boostWrite,
                    [](uint32_t us){lgfx::delayMicroseconds(us);}))boostFail();
#endif
"""
UNIFIED_OLD = b"      M5.In_I2C.bitOn(aw9523_i2c_addr, 0x03, 0b10000000, i2c_freq);  // SY7088 BOOST_EN\n"
UNIFIED_NEW = b"""#if defined(BOARD_STACKCHAN) && BOARD_STACKCHAN
      if(M5.getBoard()==board_t::board_M5StackChan) {
        auto read=[](uint8_t reg,uint8_t& value){
          return M5.In_I2C.readRegister(aw9523_i2c_addr,reg,&value,1,i2c_freq);
        };
        auto write=[](uint8_t reg,uint8_t value){
          return M5.In_I2C.writeRegister8(aw9523_i2c_addr,reg,value,i2c_freq);
        };
        if(!tpkboost::start(read,write,[](uint32_t us){lgfx::delayMicroseconds(us);})) {
          ESP_LOGE("Power","K151 boost init I2C failed; startup stopped");
          // _begin ignores Power.begin's return, so prevent fallthrough
          // to its unconditional setExtOutput call.
          for(;;)m5gfx::delay(1000);
        }
      } else
#endif
""" + UNIFIED_OLD

SPECS = (
    ("M5GFX","src/M5GFX.cpp","5e8b4fba81f589fadb7d87bf46983387593a6360",
     ((b'#include "M5GFX.h"\n',b'#include "M5GFX.h"\n'+GUARD),
      (GFX_OLD,GFX_NEW),(GFX_DIR,GFX_START))),
    ("M5Unified","src/utility/Power_Class.cpp","8531e1113e6a41eaf80fa4e8c831ab80fe6866f9",
     ((b'#include "Power_Class.hpp"\n',b'#include "Power_Class.hpp"\n'+GUARD),
      (UNIFIED_OLD,UNIFIED_NEW))),
)
def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def patched(original,expected,replacements):
    if blob(original)!=expected:raise ValueError("unexpected pinned library source")
    for old,new in replacements:
        if original.count(old)!=1:raise ValueError("unexpected patch context")
        original=original.replace(old,new)
    return original

def ensure(libraries,check=False):
    header=HEADER.read_bytes()
    pending=[]
    for name,relative,expected,replacements in SPECS:
        path=libraries/name/relative
        dst=path.with_name("tpk_k151_boost_start.h")
        current=path.read_bytes()
        original=current
        for old,new in reversed(replacements):
            if original.count(new)==1:original=original.replace(new,old)
        fixed=patched(original,expected,replacements)
        if current not in (original,fixed):raise ValueError("partial patch")
        if dst.exists() and dst.read_bytes()!=header:raise ValueError("unexpected boost header")
        if check and (current!=fixed or not dst.is_file()):
            raise ValueError("K151 boost patch missing")
        pending.append((path,current,fixed,dst))
    for path,current,fixed,dst in pending:
        if not check:
            if current!=fixed:path.write_bytes(fixed)
            if not dst.exists():dst.write_bytes(header)
        print(path.name,"K151 boost patch SHA-256:",hashlib.sha256(fixed).hexdigest())
    print("K151 boost policy SHA-256:",hashlib.sha256(header).hexdigest())

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("libraries",type=Path)
    p.add_argument("--check",action="store_true")
    a=p.parse_args()
    ensure(a.libraries,a.check)
