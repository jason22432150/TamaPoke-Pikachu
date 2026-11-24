#pragma once
#include "servo_executor.h"

namespace tpkbody {
// Bench only. These guards require an independently reviewed fixture and
// device-specific permit. No game or serial caller is allowed to construct it.
struct PowerGuard {
  MotionSafety game;
  bool benchVerified,exclusiveHardware,physicalStopAvailable;
};
inline bool powerAllowed(const PowerGuard& g){
  return g.benchVerified && g.exclusiveHardware && g.physicalStopAvailable && motionAllowed(g.game);
}
struct PowerSample {
  FeedbackPair feedback;
  RawPose goal;
};
class ServoPowerIO {
public:
  virtual ~ServoPowerIO()=default;
  virtual bool readRailLatch(bool& on)=0;
  virtual bool openBus()=0;
  virtual void closeBus()=0;
  virtual bool setRailLatch(bool on)=0;
  virtual bool sample(PowerSample& data)=0;
  virtual uint32_t clockMs()=0;
  virtual bool setTorque(uint8_t id,bool on)=0;
};
enum class PowerState:uint8_t { Locked, Settling, Ready, Fault, ShutdownUnconfirmed };
constexpr uint32_t RAIL_SETTLE_MS=250, RAIL_START_MAX_MS=1500;
class ServoPowerSession {
  ServoPowerIO& io_;
  PowerState state_=PowerState::Locked;
  ServoCenters centers_{-1,-1};
  uint32_t started_=0;
  bool ownsBus_=false,railAttempted_=false,torqueAttempted_=false;
  bool checkedRail(bool expected) {
    bool on=false;return io_.readRailLatch(on)&&on==expected;
  }
  PowerState cleanup(bool fault) {
    bool yaw=true,pitch=true,rail=true;
    // If torque activation was attempted, independently disable both axes.
    if(ownsBus_&&torqueAttempted_){
      yaw=io_.setTorque(1,false);
      pitch=io_.setTorque(2,false);
    }
    if(railAttempted_){
      const bool write=io_.setRailLatch(false);
      const bool read=checkedRail(false);
      rail=write&&read;
    }
    if(ownsBus_)io_.closeBus();
    ownsBus_=railAttempted_=torqueAttempted_=false;
    state_=!yaw||!pitch||!rail?PowerState::ShutdownUnconfirmed:
        fault?PowerState::Fault:PowerState::Locked;
    return state_;
  }
  bool stationary(const PowerSample& s,uint32_t now,bool torque) const {
    const auto& f=s.feedback;
    return now-f.sampledAt<=FEEDBACK_MAX_MS &&
      feedbackValid(f.yaw)&&feedbackValid(f.pitch)&&
      feedbackInEnvelope({f.yaw.position,f.pitch.position},centers_,f.yawRange,f.pitchRange)&&
      !f.yaw.moving&&!f.pitch.moving&&f.yaw.torque==int(torque)&&f.pitch.torque==int(torque)&&
      s.goal.yaw==f.yaw.position&&s.goal.pitch==f.pitch.position;
  }
public:
  explicit ServoPowerSession(ServoPowerIO& io):io_(io){}
  ServoPowerSession(const ServoPowerSession&)=delete;
  ServoPowerSession& operator=(const ServoPowerSession&)=delete;
  PowerState state()const{return state_;}
  bool begin(const PowerGuard& g,ServoCenters centers,uint32_t now) {
    if(state_!=PowerState::Locked||!powerAllowed(g)||
       !safeEnvelope(centers,BSP_RAW,BSP_RAW)||!checkedRail(false))return false;
    if(!io_.openBus())return false;
    ownsBus_=true;
    // Do not touch a rail that another owner may have enabled.
    if(!checkedRail(false)){cleanup(true);return false;}
    centers_=centers;started_=now;railAttempted_=true;
    if(!io_.setRailLatch(true)||!checkedRail(true)){cleanup(true);return false;}
    state_=PowerState::Settling;return true;
  }
  PowerState tick(const PowerGuard& g,uint32_t now) {
    if(state_!=PowerState::Settling&&state_!=PowerState::Ready)return state_;
    if(!powerAllowed(g)||now-started_>=SESSION_MS||!checkedRail(true))
      return cleanup(true);
    if(state_==PowerState::Ready)return state_;
    if(now-started_>=RAIL_START_MAX_MS)return cleanup(true);
    if(now-started_<RAIL_SETTLE_MS)return state_;
    PowerSample before{};
    if(!io_.sample(before)||!stationary(before,io_.clockMs(),false)||io_.clockMs()-started_>=RAIL_START_MAX_MS)return cleanup(true);
    // Never write a goal to an unpowered/unvalidated servo. Only enable
    // torque if its existing goal already equals its measured position.
    torqueAttempted_=true;
    if(!io_.setTorque(1,true)||!io_.setTorque(2,true))return cleanup(true);
    PowerSample after{};
    if(!io_.sample(after)||!stationary(after,io_.clockMs(),true)||io_.clockMs()-started_>=RAIL_START_MAX_MS||
       !sameRange(before.feedback.yawRange,after.feedback.yawRange)||
       !sameRange(before.feedback.pitchRange,after.feedback.pitchRange)||
       before.goal.yaw!=after.goal.yaw||before.goal.pitch!=after.goal.pitch)
      return cleanup(true);
    state_=PowerState::Ready;return state_;
  }
  PowerState stop(){
    if(state_==PowerState::Settling||state_==PowerState::Ready)return cleanup(false);
    return state_;
  }
};
}
