#!/usr/bin/env python3
"""B11n trace-only changes on exact B11m dependency sources."""
import argparse
import hashlib
from pathlib import Path
import patch_stackchan_boost as base

TRACE=Path(__file__).resolve().parents[1]/"boards/stackchan/hal/boot_trace.h"
def sub(s,old,new):
    if s.count(old)!=1: raise ValueError(f"Unexpected trace anchor: {old!r}")
    return s.replace(old,new)
def guard(old,new):
    return b'#if defined(TPK_BOOT_TRACE) && TPK_BOOT_TRACE\n'+new+b'#else\n'+old+b'#endif\n'

def trace_specs():
    gfx=base.GFX_NEW
    gfx=sub(gfx,b'if(!v.has_value())return false;',b'if(!v.has_value()){tpk_boot_mark(tpktrace::GfxI2cFail,0x100u|reg);return false;}')
    gfx=sub(gfx,b'auto boostWrite = [](uint8_t reg,uint8_t value) {\n              return lgfx::i2c::writeRegister8(i2c_port,aw9523_i2c_addr,reg,value,0,i2c_freq).has_value();\n            };',b'''bool traceFirstOn=false;
            auto boostWrite = [&traceFirstOn](uint8_t reg,uint8_t value) {
              const bool first=!traceFirstOn && reg==tpkboost::OUT && (value&tpkboost::MASK);
              if(first){traceFirstOn=true;tpk_boot_mark(tpktrace::GfxFirstOnBefore,value);}
              const bool ok=lgfx::i2c::writeRegister8(i2c_port,aw9523_i2c_addr,reg,value,0,i2c_freq).has_value();
              if(!ok)tpk_boot_mark(tpktrace::GfxI2cFail,0x200u|reg);
              else if(first)tpk_boot_mark(tpktrace::GfxFirstOnAfter,value);
              return ok;
            };''')
    gfx=sub(gfx,b'auto boostFail = []() {',b'auto boostFail = []() {\n              tpk_boot_mark(tpktrace::GfxI2cFail,0x300u);')
    gfx=sub(gfx,b'if(!tpkboost::prepare(boostRead,boostWrite))boostFail();',b'tpk_boot_mark(tpktrace::GfxPrepareBefore,0);\n            if(!tpkboost::prepare(boostRead,boostWrite))boostFail();\n            tpk_boot_mark(tpktrace::GfxPrepareAfter,0);')
    gfx=sub(gfx,b'if(!lgfx::i2c::bitOn(i2c_port,aw9523_i2c_addr,0x03,reg0x03&0x7f,i2c_freq).has_value())boostFail();',b'if(!lgfx::i2c::bitOn(i2c_port,aw9523_i2c_addr,0x03,reg0x03&0x7f,i2c_freq).has_value()){tpk_boot_mark(tpktrace::GfxI2cFail,0x203u);boostFail();}')
    start=sub(base.GFX_START,b'if((reg0x03&0x80)&&!tpkboost::start(boostRead,boostWrite,\n                    [](uint32_t us){lgfx::delayMicroseconds(us);}))boostFail();',b'''tpk_boot_mark(tpktrace::GfxStartBefore,reg0x03);
            if((reg0x03&0x80)&&!tpkboost::start(boostRead,boostWrite,
                    [](uint32_t us){lgfx::delayMicroseconds(us);}))boostFail();
            tpk_boot_mark(tpktrace::GfxStartAfter,(reg0x03&0x80)?uint32_t(traceFirstOn):2u);''')
    uni=base.UNIFIED_NEW
    uni=sub(uni,b'return M5.In_I2C.readRegister(aw9523_i2c_addr,reg,&value,1,i2c_freq);',b'const bool ok=M5.In_I2C.readRegister(aw9523_i2c_addr,reg,&value,1,i2c_freq);\n          if(!ok)tpk_boot_mark(tpktrace::UnifiedI2cFail,0x100u|reg);\n          return ok;')
    uni=sub(uni,b'auto write=[](uint8_t reg,uint8_t value){\n          return M5.In_I2C.writeRegister8(aw9523_i2c_addr,reg,value,i2c_freq);\n        };',b'''bool traceFirstOn=false;
        auto write=[&traceFirstOn](uint8_t reg,uint8_t value){
          const bool first=!traceFirstOn && reg==tpkboost::OUT && (value&tpkboost::MASK);
          if(first){traceFirstOn=true;tpk_boot_mark(tpktrace::UnifiedFirstOnBefore,value);}
          const bool ok=M5.In_I2C.writeRegister8(aw9523_i2c_addr,reg,value,i2c_freq);
          if(!ok)tpk_boot_mark(tpktrace::UnifiedI2cFail,0x200u|reg);
          else if(first)tpk_boot_mark(tpktrace::UnifiedFirstOnAfter,value);
          return ok;
        };''')
    uni=sub(uni,b'if(!tpkboost::start(read,write,',b'tpk_boot_mark(tpktrace::UnifiedStartBefore,0);\n        if(!tpkboost::start(read,write,')
    uni=sub(uni,b'ESP_LOGE("Power","K151 boost init I2C failed; startup stopped");',b'tpk_boot_mark(tpktrace::UnifiedI2cFail,0x300u);\n          ESP_LOGE("Power","K151 boost init I2C failed; startup stopped");')
    uni=sub(uni,b'      } else\n#endif',b'        tpk_boot_mark(tpktrace::UnifiedStartAfter,uint32_t(traceFirstOn));\n      } else\n#endif')
    direction=b'            m5gfx::i2c::writeRegister8(i2c_port, aw9523_i2c_addr, 0x05, 0b00001100);  // CONFIG_P1\n'
    direction_new=b'''            tpk_boot_mark(tpktrace::GfxDirBefore,0);
            const bool traceDirOk=m5gfx::i2c::writeRegister8(i2c_port, aw9523_i2c_addr, 0x05, 0b00001100).has_value();
            if(!traceDirOk)tpk_boot_mark(tpktrace::GfxI2cFail,0x205u);
            tpk_boot_mark(tpktrace::GfxDirAfter,uint32_t(traceDirOk));
'''
    ldo=b'            m5gfx::i2c::writeRegister8(i2c_port, axp_i2c_addr, 0x90, 0xBF); // LDOS ON/OFF control 0\n'
    ldo_new=b'''            tpk_boot_mark(tpktrace::GfxLdoBefore,0xBF);
            const bool traceLdoOk=m5gfx::i2c::writeRegister8(i2c_port, axp_i2c_addr, 0x90, 0xBF).has_value();
            if(!traceLdoOk)tpk_boot_mark(tpktrace::GfxI2cFail,0x490u);
            tpk_boot_mark(tpktrace::GfxLdoAfter,uint32_t(traceLdoOk));
'''
    # Light on/off calls: observe same I2C operations, no brightness changes.
    light=b'''    void setBrightness(uint8_t brightness) override
    {
      if (brightness)
      {
        brightness = ((brightness + 641) >> 5);
    // AXP2101 reg 0x90 = LDOS ON/OFF control
        lgfx::i2c::bitOn(i2c_port, axp_i2c_addr, 0x90, 0x80, i2c_freq); // DLDO1 enable
      }
      else
      {
        lgfx::i2c::bitOff(i2c_port, axp_i2c_addr, 0x90, 0x80, i2c_freq); // DLDO1 disable
      }
    // AXP2101 reg 0x99 = DLDO1 voltage setting
      lgfx::i2c::writeRegister8(i2c_port, axp_i2c_addr, 0x99, brightness, 0, i2c_freq);
    }
'''
    light_new=b'''    void setBrightness(uint8_t brightness) override
    {
      const bool trace=tpk_boot_early();
      if(trace)tpk_boot_mark(tpktrace::LightBefore,brightness);
      bool ok=false;
      if (brightness)
      {
        brightness = ((brightness + 641) >> 5);
        ok=lgfx::i2c::bitOn(i2c_port, axp_i2c_addr, 0x90, 0x80, i2c_freq).has_value();
      }
      else
      {
        ok=lgfx::i2c::bitOff(i2c_port, axp_i2c_addr, 0x90, 0x80, i2c_freq).has_value();
      }
      const bool voltageOk=lgfx::i2c::writeRegister8(i2c_port, axp_i2c_addr, 0x99, brightness, 0, i2c_freq).has_value();
      if(trace){
        if(!ok||!voltageOk)tpk_boot_mark(tpktrace::GfxI2cFail,!ok?0x490u:0x499u);
        tpk_boot_mark(tpktrace::LightAfter,uint32_t(ok)|(uint32_t(voltageOk)<<1));
      }
    }
'''
    pmic=b'      Axp2101.writeRegister8Array(reg_data_array, sizeof(reg_data_array));\n'
    # Anchor includes the unique following CoreS3 comment, since the same
    # writeRegister8Array call appears for other boards.
    pmic_tail=b'      // The touch INT is routed to the ESP32 as TOUCH_INT -> AW9523 P1_2 -> AW9523 INTN\n'
    pmic_full=pmic+pmic_tail
    pmic_new=b'''      {
        const bool tracePmic=tpk_boot_early();
        if(tracePmic)tpk_boot_mark(tpktrace::UnifiedPmicBefore,0);
        const bool tracePmicOk=Axp2101.writeRegister8Array(reg_data_array, sizeof(reg_data_array));
        if(tracePmic){
          if(!tracePmicOk)tpk_boot_mark(tpktrace::UnifiedI2cFail,0x400u);
          tpk_boot_mark(tpktrace::UnifiedPmicAfter,uint32_t(tracePmicOk));
        }
      }
'''+pmic_tail
    ext_read=b'    if (M5.In_I2C.readRegister(aw9523_i2c_addr, port0_reg, buf, sizeof(buf), i2c_freq))\n'
    ext_read_new=b'''    const bool traceExt=tpk_boot_early();
    const bool traceReadOk=M5.In_I2C.readRegister(aw9523_i2c_addr, port0_reg, buf, sizeof(buf), i2c_freq);
    if(traceExt&&!traceReadOk)tpk_boot_mark(tpktrace::ExtI2cFail,0x102u);
    if (traceReadOk)
'''
    ext_write=b'      M5.In_I2C.writeRegister(aw9523_i2c_addr, port0_reg, buf, sizeof(buf), i2c_freq);\n'
    ext_write_new=b'''      if(traceExt)tpk_boot_mark(tpktrace::ExtWriteBefore,uint32_t(p0)|(uint32_t(p1)<<8));
      const bool traceWriteOk=M5.In_I2C.writeRegister(aw9523_i2c_addr, port0_reg, buf, sizeof(buf), i2c_freq);
      if(traceExt){
        if(!traceWriteOk)tpk_boot_mark(tpktrace::ExtI2cFail,0x202u);
        tpk_boot_mark(tpktrace::ExtWriteAfter,uint32_t(traceWriteOk));
      }
'''
    ext=b'''        bool cancel = (enable && !Axp2101.getBatState() && Axp2101.getTSVoltage() > 2.0f && Axp2101.isVBUS());
        if (!cancel)
        {
          _core_s3_output(_core_s3_bus_en, enable);
        } else {
          ESP_LOGW("Power","setExtPower(true) is canceled.");
        }
'''
    ext_new=b'''        const bool trace=tpk_boot_early();
        if(trace)tpk_boot_mark(tpktrace::ExtBefore,uint32_t(enable));
        bool cancel = (enable && !Axp2101.getBatState() && Axp2101.getTSVoltage() > 2.0f && Axp2101.isVBUS());
        if (!cancel)
        {
          _core_s3_output(_core_s3_bus_en, enable);
        } else {
          ESP_LOGW("Power","setExtPower(true) is canceled.");
        }
        if(trace)tpk_boot_mark(tpktrace::ExtAfter,uint32_t(cancel));
'''
    inc=base.GUARD
    inc_new=sub(inc,b'#include "tpk_k151_boost_start.h"',b'#include "tpk_k151_boost_start.h"\n#include "tpk_k151_boot_trace.h"')
    return (tuple((a,guard(a,b)) for a,b in ((inc,inc_new),(base.GFX_NEW,gfx),
                  (base.GFX_START,start),(direction,direction_new),(ldo,ldo_new),(light,light_new))),
            tuple((a,guard(a,b)) for a,b in ((inc,inc_new),(base.UNIFIED_NEW,uni),
                  (pmic_full,pmic_new),(ext_read,ext_read_new),(ext_write,ext_write_new),(ext,ext_new))))

def ensure(libraries,check=False):
    pending=[]; trace=TRACE.read_bytes(); policy=base.HEADER.read_bytes()
    for (name,relative,expected,replacements),diagnostic in zip(base.SPECS,trace_specs()):
        path=libraries/name/relative; current=path.read_bytes(); original=current
        for old,new in reversed(diagnostic):
            if original.count(new)==1: original=original.replace(new,old)
        for old,new in reversed(replacements):
            if original.count(new)==1: original=original.replace(new,old)
        b11m=base.patched(original,expected,replacements); fixed=b11m
        for old,new in diagnostic: fixed=sub(fixed,old,new)
        if current not in (original,b11m,fixed): raise ValueError(f"Unexpected partial patch: {path}")
        if check and current!=fixed: raise ValueError(f"Missing diagnostic source patch: {path}")
        pending.append((path,fixed))
        for dest,data in ((path.with_name('tpk_k151_boost_start.h'),policy),
                          (path.with_name('tpk_k151_boot_trace.h'),trace)):
            if dest.exists() and dest.read_bytes()!=data: raise ValueError(f"Unexpected header: {dest}")
            if check and not dest.is_file(): raise ValueError(f"Missing header: {dest}")
            pending.append((dest,data))
    for path,data in pending:
        if not check and (not path.exists() or path.read_bytes()!=data): path.write_bytes(data)
        print(path.name,"B11n SHA-256",hashlib.sha256(data).hexdigest())

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('libraries',type=Path)
    p.add_argument('--check',action='store_true')
    a=p.parse_args();ensure(a.libraries,a.check)
