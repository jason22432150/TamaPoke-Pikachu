#pragma once
#include <stdint.h>
namespace tpkbody {
struct ServoFeedback {
  int position, voltage, temperature, moving, torque;
};
inline bool feedbackValid(const ServoFeedback& f) {
  return f.position>=0 && f.position<=1000 && f.voltage>0 && f.voltage<=255 &&
         f.temperature>=0 && f.temperature<=100 &&
         (f.moving==0 || f.moving==1) && (f.torque==0 || f.torque==1);
}
struct ProbeSafety {
  bool correctBoard,railKnown,railOn,uartFree,awake,previewOff;
  int battery;
};
enum class ProbeResult:uint8_t { Ok, Blocked, Busy, RateLimited, FaultLatched, Transport, Feedback };
class ServoProbePolicy {
  bool active_=false,attempted_=false,fault_=false;
  uint32_t last_=0;
public:
  ProbeResult begin(const ProbeSafety& s,uint32_t now) {
    if(fault_)return ProbeResult::FaultLatched;
    if(active_)return ProbeResult::Busy;
    if(!s.correctBoard || !s.railKnown || !s.railOn || !s.uartFree ||
        !s.awake || !s.previewOff || s.battery<25 || s.battery>100)
      return ProbeResult::Blocked;
    if(attempted_ && now-last_<5000)return ProbeResult::RateLimited;
    active_=attempted_=true;last_=now;
    return ProbeResult::Ok;
  }
  ProbeResult finish(bool transport,const ServoFeedback& a,const ServoFeedback& b) {
    if(!active_)return ProbeResult::Blocked;
    active_=false;
    if(!transport){fault_=true;return ProbeResult::Transport;}
    if(!feedbackValid(a)||!feedbackValid(b)){fault_=true;return ProbeResult::Feedback;}
    return ProbeResult::Ok;
  }
};
}
