#pragma once
#include <M5Unified.h>
#include <Preferences.h>
#include "src/drivers/PY32IOExpander/PY32IOExpander.hpp"
#include "body_policy.h"

class StackChanBody {
  m5::PY32IOExpander_Class io_;
  bool rgbEnabled_=false;
  tpkbody::Color last_{0,0,0};
  uint32_t lastUpdate_=0;

  void show(tpkbody::Color c) {
    // Driver uses RGB565 internally; cap each channel even if future policy changes.
    const auto cap=[](uint8_t v)->uint8_t { return v>32?32:v; };
    for(uint8_t i=0;i<12;i++) io_.setLedColor(i,cap(c.r),cap(c.g),cap(c.b));
    io_.refreshLeds();
    last_=c;
  }

public:
  bool enableRgb() {
    if(rgbEnabled_) return true;
    if(M5.getBoard()!=m5gfx::board_t::board_M5StackChan || !io_.begin()) return false;
    // Only RGB pin 13, as in BSP 1.1.0. Never initialize VM EN (pin 0).
    io_.setDirection(13,true);
    io_.setPullMode(13,true);
    io_.setDriveMode(13,false);
    io_.setLedCount(12);
    rgbEnabled_=true;
    show({0,0,0});
    return true;
  }
  void disableRgb() {
    if(rgbEnabled_) show({0,0,0});
    rgbEnabled_=false;
  }
  void update(const tpkbody::PetState& state,uint32_t now) {
    if(!rgbEnabled_) return;
    auto next=tpkbody::colorFor(state);
    if(next==last_) return;
    // Switch off immediately; limit nonzero color changes to 5 Hz.
    if(next!=tpkbody::Color{0,0,0} && now-lastUpdate_<200) return;
    show(next);lastUpdate_=now;
  }
  bool command(const String& line) {
    if(line=="BODY RGB ON") {
      Serial.println(enableRgb()?"DONE RGB request enabled":"ERR RGB expander unavailable");
      return true;
    }
    if(line=="BODY RGB OFF") {
      disableRgb();Serial.println("DONE RGB disabled");return true;
    }
    if(line=="BODY CHECK") {
      // Official BSP calibration namespace and signed integer keys.
      // Read only; never create the namespace or synthesize/write default centers.
      Preferences p;
      int yaw=-1,pitch=-1;
      if(p.begin("servo",true)) {
        yaw=p.getInt("zero_pos_1",-1);pitch=p.getInt("zero_pos_2",-1);p.end();
      }
      const bool present=tpkbody::calibrationPresent(yaw,pitch);
      Serial.printf("BODY rgb=%d calibration=%s yaw=%d pitch=%d motor=disabled\n",
          rgbEnabled_,present?"present-unverified":"missing-or-invalid",yaw,pitch);
      Serial.println("DONE");
      return true;
    }
    return false;
  }
};
