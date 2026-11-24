#pragma once
#include <stdint.h>
#include "body_policy.h"

namespace tpkbody {
// Units match official BSP: 10 units/degree. These are conservative
// provisional software limits, not measured mechanical limits.
struct Pose { int16_t yaw,pitch; uint16_t speed; };
constexpr int16_t YAW_MAX=100, PITCH_MAX=100;
constexpr uint16_t SPEED_MAX=200;
constexpr uint32_t STEP_MS=1500, COOLDOWN_MS=6000, SESSION_MS=60000;
enum class Reaction:uint8_t { None, Hatch, Eat, Happy, Evolve, Play };
enum class Action:uint8_t { None, Pose, Stop };
struct MotionCommand { Action action; Pose pose; };
struct MotionSafety {
  bool sleeping,screenOff,ceremony,menu,calibrationValid;
  int batteryPercent;
};
inline bool motionAllowed(const MotionSafety& s) {
  return !s.sleeping && !s.screenOff && !s.ceremony && !s.menu &&
         s.calibrationValid && s.batteryPercent>=25 && s.batteryPercent<=100;
}
inline bool safePose(Pose p) {
  return p.yaw>=-YAW_MAX && p.yaw<=YAW_MAX &&
      p.pitch>=0 && p.pitch<=PITCH_MAX && p.speed>0 && p.speed<=SPEED_MAX;
}
inline Pose reactionPose(Reaction r) {
  switch(r) {
    case Reaction::Hatch: return {0,60,100};
    case Reaction::Eat: return {0,40,100};
    case Reaction::Happy: return {-80,50,150};
    case Reaction::Evolve: return {0,100,150};
    case Reaction::Play: return {100,40,150};
    default: return {0,0,100};
  }
}
// Preview only. No hardware backend, no servo rail or calibration writes.
class MotionPolicy {
  bool enabled_=false,active_=false,returning_=false,hasFinished_=false;
  uint32_t armedAt_=0,stepAt_=0,finishedAt_=0;
  Reaction previous_=Reaction::None;
public:
  bool enabled() const {return enabled_;}
  bool active() const {return active_;}
  bool arm(uint32_t now,const MotionSafety& s) {
    if(enabled_ || !motionAllowed(s)) return false;
    enabled_=true;active_=returning_=hasFinished_=false;
    armedAt_=now;previous_=Reaction::None;
    return true;
  }
  MotionCommand stop() {
    const bool wasActive=active_;
    enabled_=active_=returning_=false;previous_=Reaction::None;
    return {wasActive?Action::Stop:Action::None,{0,0,0}};
  }
  MotionCommand update(uint32_t now,const MotionSafety& s,Reaction r) {
    if(!enabled_) return {Action::None,{0,0,0}};
    if(!motionAllowed(s) || now-armedAt_>=SESSION_MS) return stop();
    bool edge=r!=previous_;previous_=r;
    if(active_) {
      if(now-stepAt_<STEP_MS) return {Action::None,{0,0,0}};
      // A stalled loop must cancel, not emit a late move.
      if(now-stepAt_>=2*STEP_MS) return stop();
      if(!returning_) {
        returning_=true;stepAt_=now;return {Action::Pose,{0,0,100}};
      }
      active_=returning_=false;hasFinished_=true;finishedAt_=now;
      return {Action::Stop,{0,0,0}};
    }
    if(!edge || r==Reaction::None ||
       (hasFinished_ && now-finishedAt_<COOLDOWN_MS))
      return {Action::None,{0,0,0}};
    Pose pose=reactionPose(r);
    if(!safePose(pose)) return stop();
    active_=true;returning_=false;stepAt_=now;
    return {Action::Pose,pose};
  }
};
}
