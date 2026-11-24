#include "hal/servo_executor.h"
#include <cassert>
#include <vector>
using namespace tpkbody;
struct Fake:ServoOutput {
  std::vector<int> calls;
  int failWrite=0,failStop=0;
  bool writePosition(uint8_t id,uint16_t raw,uint16_t ms)override{
    assert(raw<=1000&&ms==COMMAND_TIME_MS);
    calls.push_back(id);return id!=failWrite;
  }
  bool releaseTorque(uint8_t id)override{calls.push_back(-int(id));return id!=failStop;}
};
static FeedbackPair sample(uint32_t t,int y=460,int p=620){
  return {{y,60,25,0,1},{p,60,25,0,1},BSP_RAW,BSP_RAW,t};
}
int main(){
  ExecutionGuard g{{false,false,false,false,true,80},true,true,true};
  ServoCenters c{460,620};
  Pose p{0,50,100};
  Fake f;ServoExecutor x(f);
  auto denied=g;denied.benchVerified=false;
  assert(!x.arm(denied,c,sample(0),0)&&f.calls.empty());
  assert(!x.arm(g,c,sample(0),251)&&f.calls.empty());
  assert(x.arm(g,c,sample(0),0));
  assert(x.start(p,g,sample(0),0)==ExecuteResult::Ok);
  assert((f.calls==std::vector<int>{1,2}));
  assert(x.update(g,sample(0,460,636),0)==ExecuteResult::Ok);
  assert(x.state()==ExecuteState::Moving);
  assert(x.update(g,sample(100,460,636),100)==ExecuteResult::Ok);
  assert(x.state()==ExecuteState::Complete);
  assert(x.stop()==ExecuteResult::Stopped);
  assert((f.calls==std::vector<int>{1,2,-1,-2}));
  Fake partial;partial.failWrite=2;ServoExecutor y(partial);
  assert(y.arm(g,c,sample(0),0));
  assert(y.start(p,g,sample(0),0)==ExecuteResult::WriteFailed);
  assert((partial.calls==std::vector<int>{1,2,-1,-2}));
  assert(y.state()==ExecuteState::Fault&&!y.arm(g,c,sample(1),1));
  Fake bad;bad.failWrite=1;bad.failStop=1;ServoExecutor z(bad);
  assert(z.arm(g,c,sample(0),0));
  assert(z.start(p,g,sample(0),0)==ExecuteResult::StopUnconfirmed);
  assert((bad.calls==std::vector<int>{1,-1,-2}));
  assert(z.state()==ExecuteState::StopUnconfirmed);
  assert(!z.arm(g,c,sample(100),100));
  Fake timeout;ServoExecutor a(timeout);
  assert(a.arm(g,c,sample(0),0));
  assert(a.start(p,g,sample(0),0)==ExecuteResult::Ok);
  assert(a.update(g,sample(1500),1500)==ExecuteResult::Timeout);
  Fake stale;ServoExecutor b(stale);
  assert(b.arm(g,c,sample(0),0));
  assert(b.start(p,g,sample(0),0)==ExecuteResult::Ok);
  assert(b.update(g,sample(0),251)==ExecuteResult::Invalid);
  Fake changed;ServoExecutor d(changed);
  assert(d.arm(g,c,sample(0),0));
  auto diff=sample(1);diff.pitchRange={1,1000};
  assert(d.start(p,g,diff,1)==ExecuteResult::Invalid);
  assert((changed.calls==std::vector<int>{-1,-2}));
  Fake rollover;ServoExecutor k(rollover);
  assert(k.arm(g,c,sample(UINT32_MAX-10),UINT32_MAX-10));
  assert(k.start(p,g,sample(UINT32_MAX-10),UINT32_MAX-10)==ExecuteResult::Ok);
  assert(k.update(g,sample(20,460,636),20)==ExecuteResult::Ok);
  assert(k.state()==ExecuteState::Complete);
  g.railConfirmed=false;
  assert(k.update(g,sample(21),21)==ExecuteResult::Invalid);
}
