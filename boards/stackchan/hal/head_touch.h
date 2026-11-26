#pragma once
#include <M5Unified.h>
#include "head_touch_policy.h"
// Register sequence follows M5Stack StackChan hal_head_touch.cpp and Si12T
// driver, upstream 28b9f0c8bd6acd81cb3c70f1a93c3e373b39d400 (MIT).
// Existing internal bus only; no GPIO, power rail, NVS or servo changes.
class StackChanHeadTouch{
  static constexpr uint8_t ADDR=0x68;
  static constexpr uint32_t FREQ=100000;
  tpkhead::Gesture gesture_;
  bool enabled_=false;
  uint32_t last_=0,errors_=0,presses_=0,swipes_=0,releases_=0;
  uint8_t raw_=0,consecutiveErrors_=0;
  bool write(uint8_t reg,uint8_t v){return M5.In_I2C.writeRegister8(ADDR,reg,v,FREQ);}
  bool read(uint8_t& raw){return M5.In_I2C.readRegister(ADDR,0x10,&raw,1,FREQ);}
public:
  bool begin(){
    enabled_=false;gesture_.reset();consecutiveErrors_=0;
    if(M5.getBoard()!=m5gfx::board_t::board_M5StackChan||!M5.In_I2C.isEnabled()||!read(raw_))return false;
    for(uint8_t r=0x0A;r<=0x0F;++r)if(!write(r,0))return false;
    if(!write(0x09,0x0F)||!write(0x09,0x07)||!write(0x08,0x22))return false;
    for(uint8_t r=0x02;r<=0x06;++r)if(!write(r,0x33))return false;
    last_=millis();enabled_=true;return true;
  }
  void disable(){enabled_=false;gesture_.reset();}
  tpkhead::Event poll(uint32_t now){
    if(!enabled_||now-last_<50)return tpkhead::Event::None;
    last_=now;
    if(!read(raw_)){
      ++errors_;gesture_.reset();
      if(++consecutiveErrors_>=3)disable();
      return tpkhead::Event::None;
    }
    consecutiveErrors_=0;
    auto e=gesture_.update(tpkhead::decode(raw_));
    if(e==tpkhead::Event::Press)++presses_;
    if(e==tpkhead::Event::Forward||e==tpkhead::Event::Backward)++swipes_;
    if(e==tpkhead::Event::Release)++releases_;
    return e;
  }
  bool command(const String& line){
    if(line=="HEAD ON"){Serial.println(begin()?"DONE HEAD enabled":"ERR HEAD unavailable");return true;}
    if(line=="HEAD OFF"){disable();Serial.println("DONE HEAD disabled");return true;}
    if(line=="HEAD?"){
      auto s=tpkhead::decode(raw_);
      Serial.printf("HEAD enabled=%d raw=%u left=%u center=%u right=%u press=%lu swipe=%lu release=%lu errors=%lu\n",
        enabled_,unsigned(raw_),unsigned(s.left),unsigned(s.center),unsigned(s.right),
        (unsigned long)presses_,(unsigned long)swipes_,(unsigned long)releases_,(unsigned long)errors_);
      Serial.println("DONE");return true;
    }
    return false;
  }
};
