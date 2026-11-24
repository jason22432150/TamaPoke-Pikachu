#pragma once
#include <M5Unified.h>
#include <Preferences.h>
#include "src/drivers/PY32IOExpander/PY32IOExpander.hpp"
#include "body_policy.h"
#include "motion_policy.h"
#include "servo_diagnostic.h"
// Compile-check the future actuator adapter without constructing it or routing commands to it.
#include "scs_output.h"
#include "scs_power_io.h"

class StackChanBody {
  m5::PY32IOExpander_Class io_;
  bool rgbEnabled_=false;
  tpkbody::Color last_{0,0,0};
  uint32_t lastUpdate_=0;
  tpkbody::MotionPolicy motion_;
  tpkbody::ServoDiagnostic servoDiagnostic_;
  bool calibrationValid_=false;
  tpkbody::ServoCenters centers_{-1,-1};
  tpkbody::MotionSafety safety_{true,true,true,true,false,-1};

  void readCalibration(int& yaw,int& pitch) {
    Preferences p;
    yaw=pitch=-1;
    if(p.begin("servo",true)) {
      yaw=p.getInt("zero_pos_1",-1);pitch=p.getInt("zero_pos_2",-1);p.end();
    }
    centers_={yaw,pitch};
    calibrationValid_=tpkbody::calibrationPresent(yaw,pitch);
    safety_.calibrationValid=calibrationValid_;
  }
  void logMotion(tpkbody::MotionCommand c) {
    if(c.action==tpkbody::Action::Pose) {
      tpkbody::RawPose raw{-1,-1};
      if(!tpkbody::mapPose(c.pose,centers_,tpkbody::BSP_RAW,tpkbody::BSP_RAW,raw)) {
        motion_.stop();
        Serial.println("MOTION PREVIEW STOP invalid calibration envelope");
        return;
      }
      Serial.printf("MOTION PREVIEW yaw=%d pitch=%d speed=%u raw_yaw=%d raw_pitch=%d (NO MOTOR OUTPUT)\n",
        int(c.pose.yaw),int(c.pose.pitch),unsigned(c.pose.speed),raw.yaw,raw.pitch);
    } else if(c.action==tpkbody::Action::Stop) Serial.println("MOTION PREVIEW STOP");
  }
public:
  void updateMotion(const tpkbody::PetState& p,bool menu,tpkbody::Reaction r,uint32_t now) {
    safety_={p.sleeping,p.screenOff,p.ceremony,menu,calibrationValid_,p.batteryPercent};
    logMotion(motion_.update(now,safety_,r));
  }
  void stopMotion(){logMotion(motion_.stop());}
private:

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
    if(line=="BODY MOTION PREVIEW ON") {
      int yaw,pitch;readCalibration(yaw,pitch);
      const bool envelope=tpkbody::safeEnvelope(centers_,tpkbody::BSP_RAW,tpkbody::BSP_RAW);
      Serial.println((envelope && motion_.arm(millis(),safety_))?"DONE preview only; no motor output":"ERR preview unavailable or already enabled");
      return true;
    }
    if(line=="BODY MOTION PREVIEW OFF") {
      stopMotion();Serial.println("DONE preview disabled");return true;
    }
    if(line=="BODY SERVO PROBE") {
      int yaw,pitch;readCalibration(yaw,pitch);
      servoDiagnostic_.probe(!safety_.sleeping && !safety_.screenOff && !safety_.menu && !safety_.ceremony,
          !motion_.enabled(),M5.Power.getBatteryLevel(),centers_);
      return true;
    }
    if(line=="BODY CHECK") {
      // Official BSP calibration namespace and signed integer keys.
      // Read only; never create the namespace or synthesize/write default centers.
      int yaw,pitch;
      readCalibration(yaw,pitch);
      const bool present=calibrationValid_;
      Serial.printf("BODY rgb=%d calibration=%s yaw=%d pitch=%d motor=disabled\n",
          rgbEnabled_,present?"present-unverified":"missing-or-invalid",yaw,pitch);
      Serial.printf("MOTION preview=%d active=%d hardware=disabled\n",motion_.enabled(),motion_.active());
      Serial.println("DONE");
      return true;
    }
    return false;
  }
};
