#include "hal/servo_power_session.h"
#include <cassert>
#include <vector>
using namespace tpkbody;
struct Fake:ServoPowerIO {
  bool rail=false,known=true,opened=false,failOn=false,failOff=false,failRead=false;
  bool yaw=false,pitch=false,wrongGoal=false,stale=false;
  int failEnable=0,failDisable=0;
  uint32_t now=0;
  std::vector<int> calls;
  bool readRailLatch(bool& on)override{on=rail;return known;}
  bool openBus()override{calls.push_back(10);opened=true;return true;}
  void closeBus()override{calls.push_back(-10);opened=false;}
  bool setRailLatch(bool on)override{
    calls.push_back(on?20:-20);
    if(on&&failOn){rail=true;return false;}
    if(!on&&failOff)return false;
    rail=on;return true;
  }
  uint32_t clockMs()override{return now;}
  bool sample(PowerSample& s)override{
    calls.push_back(30);
    s={{{460,60,25,0,int(yaw)},{620,60,25,0,int(pitch)},BSP_RAW,BSP_RAW,
        stale?now-251:now},{wrongGoal?461:460,620}};
    return !failRead;
  }
  bool setTorque(uint8_t id,bool on)override{
    calls.push_back(on?int(id):-int(id));
    if(on&&id==failEnable)return false;
    if(!on&&id==failDisable)return false;
    (id==1?yaw:pitch)=on;return true;
  }
};
int main(){
  PowerGuard g{{false,false,false,false,true,80},true,true,true};
  ServoCenters c{460,620};
  Fake f;ServoPowerSession p(f);
  auto denied=g;denied.physicalStopAvailable=false;
  assert(!p.begin(denied,c,0)&&f.calls.empty());
  f.rail=true;assert(!p.begin(g,c,0)&&f.calls.empty());f.rail=false;
  assert(p.begin(g,c,0));
  assert((f.calls==std::vector<int>{10,20}));
  f.now=249;assert(p.tick(g,249)==PowerState::Settling);
  f.now=250;assert(p.tick(g,250)==PowerState::Ready);
  assert((f.calls==std::vector<int>{10,20,30,1,2,30}));
  assert(p.stop()==PowerState::Locked&&!f.rail&&!f.yaw&&!f.pitch&&!f.opened);
  assert((f.calls==std::vector<int>{10,20,30,1,2,30,-1,-2,-20,-10}));
  Fake a;a.wrongGoal=true;ServoPowerSession x(a);
  assert(x.begin(g,c,0));a.now=250;assert(x.tick(g,250)==PowerState::Fault);
  assert((a.calls==std::vector<int>{10,20,30,-20,-10}));
  assert(!x.begin(g,c,300));
  Fake b;b.failEnable=2;ServoPowerSession y(b);
  assert(y.begin(g,c,0));b.now=250;assert(y.tick(g,250)==PowerState::Fault);
  assert((b.calls==std::vector<int>{10,20,30,1,2,-1,-2,-20,-10}));
  Fake d;d.failEnable=2;d.failDisable=1;ServoPowerSession z(d);
  assert(z.begin(g,c,0));d.now=250;assert(z.tick(g,250)==PowerState::ShutdownUnconfirmed);
  assert(!d.rail&&!d.opened);
  Fake e;e.failOn=true;ServoPowerSession v(e);
  assert(!v.begin(g,c,0)&&v.state()==PowerState::Fault&&!e.rail);
  Fake h;h.failOff=true;ServoPowerSession w(h);
  assert(w.begin(g,c,0));assert(w.stop()==PowerState::ShutdownUnconfirmed);
  Fake j;j.stale=true;ServoPowerSession stale(j);
  assert(stale.begin(g,c,0));j.now=250;assert(stale.tick(g,250)==PowerState::Fault);
  Fake k;ServoPowerSession rollover(k);
  assert(rollover.begin(g,c,UINT32_MAX-100));
  k.now=149;assert(rollover.tick(g,149)==PowerState::Ready);
  g.game.batteryPercent=24;assert(rollover.tick(g,150)==PowerState::Fault);
  Fake l;ServoPowerSession timeout(l);g.game.batteryPercent=80;
  assert(timeout.begin(g,c,0));l.now=1500;assert(timeout.tick(g,1500)==PowerState::Fault);
}
