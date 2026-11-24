#pragma once
#include "servo_coordinates.h"
#include "servo_diagnostic_policy.h"

namespace tpkbody {
// This executor has no production caller. The transport must already own a
// verified, powered bus. It never enables power, torque or a new servo mode.
// A future supervised hardware controller must supply a real bench permit.
struct ExecutionGuard {
  MotionSafety game;
  bool benchVerified,railConfirmed,busOwned;
};
struct FeedbackPair {
  ServoFeedback yaw,pitch;
  RawRange yawRange,pitchRange;
  uint32_t sampledAt;
};
enum class ExecuteState:uint8_t { Locked, Ready, Moving, Complete, Fault, StopUnconfirmed };
enum class ExecuteResult:uint8_t { Ok, Blocked, Invalid, WriteFailed, Timeout, Stopped, StopUnconfirmed };
constexpr uint32_t FEEDBACK_MAX_MS=250, ARRIVAL_MAX_MS=1500;
constexpr int ARRIVAL_TOLERANCE=2;
constexpr uint16_t COMMAND_TIME_MS=1000;
inline bool sameRange(RawRange a,RawRange b){return a.lo==b.lo && a.hi==b.hi;}
inline bool nearRaw(int a,int b){return a>=b-ARRIVAL_TOLERANCE && a<=b+ARRIVAL_TOLERANCE;}
inline bool executionAllowed(const ExecutionGuard& g) {
  return g.benchVerified && g.railConfirmed && g.busOwned && motionAllowed(g.game);
}
class ServoOutput {
public:
  virtual ~ServoOutput()=default;
  virtual bool writePosition(uint8_t id,uint16_t raw,uint16_t durationMs)=0;
  virtual bool releaseTorque(uint8_t id)=0;
};
class ServoExecutor {
  ServoOutput& output_;
  ExecuteState state_=ExecuteState::Locked;
  ServoCenters centers_{-1,-1};
  RawRange yawRange_{-1,-1},pitchRange_{-1,-1};
  RawPose target_{-1,-1};
  uint32_t sentAt_=0,armedAt_=0;
  bool feedbackOk(const FeedbackPair& f,uint32_t now) const {
    return now-f.sampledAt<=FEEDBACK_MAX_MS &&
      feedbackValid(f.yaw)&&feedbackValid(f.pitch)&&
      sameRange(f.yawRange,yawRange_)&&sameRange(f.pitchRange,pitchRange_)&&
      feedbackInEnvelope({f.yaw.position,f.pitch.position},centers_,yawRange_,pitchRange_);
  }
  ExecuteResult halt(ExecuteResult reason,bool fault) {
    // Always attempt both axes even if the first fails. Acknowledged release
    // is not proof of physical stop; failed release is a distinct latched state.
    bool yaw=output_.releaseTorque(1);
    bool pitch=output_.releaseTorque(2);
    state_=(!yaw||!pitch)?ExecuteState::StopUnconfirmed:
           fault?ExecuteState::Fault:ExecuteState::Locked;
    return (!yaw||!pitch)?ExecuteResult::StopUnconfirmed:reason;
  }
public:
  explicit ServoExecutor(ServoOutput& output):output_(output){}
  ExecuteState state()const{return state_;}
  bool arm(const ExecutionGuard& g,ServoCenters centers,const FeedbackPair& f,uint32_t now) {
    if(state_!=ExecuteState::Locked || !executionAllowed(g) ||
       !safeEnvelope(centers,f.yawRange,f.pitchRange))return false;
    centers_=centers;yawRange_=f.yawRange;pitchRange_=f.pitchRange;
    // Never take ownership of an already moving axis. Torque must already
    // be enabled by the separately reviewed bench controller.
    if(!feedbackOk(f,now)||f.yaw.moving||f.pitch.moving||!f.yaw.torque||!f.pitch.torque)
      return false;
    state_=ExecuteState::Ready;armedAt_=now;return true;
  }
  ExecuteResult start(Pose p,const ExecutionGuard& g,const FeedbackPair& f,uint32_t now) {
    if(state_!=ExecuteState::Ready && state_!=ExecuteState::Complete)
      return ExecuteResult::Blocked;
    if(!executionAllowed(g)||now-armedAt_>=SESSION_MS||!feedbackOk(f,now)||
       f.yaw.moving||f.pitch.moving||!f.yaw.torque||!f.pitch.torque)
      return halt(ExecuteResult::Invalid,true);
    if(!mapPose(p,centers_,yawRange_,pitchRange_,target_))
      return halt(ExecuteResult::Invalid,true);
    // Time mode, not the BSP spring speed parameter. No automatic retry.
    if(!output_.writePosition(1,uint16_t(target_.yaw),COMMAND_TIME_MS))
      return halt(ExecuteResult::WriteFailed,true);
    if(!output_.writePosition(2,uint16_t(target_.pitch),COMMAND_TIME_MS))
      return halt(ExecuteResult::WriteFailed,true);
    sentAt_=now;state_=ExecuteState::Moving;return ExecuteResult::Ok;
  }
  ExecuteResult update(const ExecutionGuard& g,const FeedbackPair& f,uint32_t now) {
    if(state_!=ExecuteState::Ready && state_!=ExecuteState::Moving && state_!=ExecuteState::Complete)
      return ExecuteResult::Blocked;
    if(!executionAllowed(g)||now-armedAt_>=SESSION_MS||
       !feedbackOk(f,now)||!f.yaw.torque||!f.pitch.torque)
      return halt(ExecuteResult::Invalid,true);
    if(state_!=ExecuteState::Moving) {
      if(f.yaw.moving||f.pitch.moving)return halt(ExecuteResult::Invalid,true);
      return ExecuteResult::Ok;
    }
    if(now-sentAt_>=ARRIVAL_MAX_MS)return halt(ExecuteResult::Timeout,true);
    // Never treat a sample from before the command as arrival feedback.
    if(now-f.sampledAt>=now-sentAt_)return ExecuteResult::Ok;
    if(!f.yaw.moving&&!f.pitch.moving&&nearRaw(f.yaw.position,target_.yaw)&&
       nearRaw(f.pitch.position,target_.pitch))state_=ExecuteState::Complete;
    return ExecuteResult::Ok;
  }
  ExecuteResult stop() {
    if(state_==ExecuteState::StopUnconfirmed)return ExecuteResult::StopUnconfirmed;
    if(state_==ExecuteState::Fault||state_==ExecuteState::Locked)return ExecuteResult::Blocked;
    return halt(ExecuteResult::Stopped,false);
  }
};
}
