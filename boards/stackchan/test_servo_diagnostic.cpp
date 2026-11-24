#include "hal/servo_diagnostic_policy.h"
#include <cassert>
using namespace tpkbody;
int main(){
  ProbeSafety s{true,true,true,true,true,true,80};
  ServoFeedback f{460,60,25,0,0};
  assert(feedbackValid(f));
  for(int i=0;i<6;i++){
    ProbeSafety blocked=s;
    switch(i){case 0:blocked.correctBoard=false;break;case 1:blocked.railKnown=false;break;
      case 2:blocked.railOn=false;break;case 3:blocked.uartFree=false;break;
      case 4:blocked.awake=false;break;case 5:blocked.previewOff=false;break;}
    ServoProbePolicy p;assert(p.begin(blocked,0)==ProbeResult::Blocked);
  }
  ServoProbePolicy p;
  s.battery=24;assert(p.begin(s,0)==ProbeResult::Blocked);
  s.battery=80;assert(p.begin(s,0)==ProbeResult::Ok);
  assert(p.begin(s,0)==ProbeResult::Busy);
  assert(p.finish(true,f,f)==ProbeResult::Ok);
  assert(p.begin(s,4999)==ProbeResult::RateLimited);
  assert(p.begin(s,5000)==ProbeResult::Ok);
  assert(p.finish(false,f,f)==ProbeResult::Transport);
  assert(p.begin(s,10000)==ProbeResult::FaultLatched);
  ServoProbePolicy q;assert(q.begin(s,UINT32_MAX-100)==ProbeResult::Ok);
  assert(q.finish(true,f,f)==ProbeResult::Ok);
  assert(q.begin(s,4899)==ProbeResult::Ok);
  f.position=1001;assert(!feedbackValid(f));
  assert(q.finish(true,f,f)==ProbeResult::Feedback);
  assert(q.begin(s,10000)==ProbeResult::FaultLatched);
  f={460,60,25,0,2};assert(!feedbackValid(f));
  f={460,60,25,-1,0};assert(!feedbackValid(f));
  f={460,-1,25,0,0};assert(!feedbackValid(f));
}
