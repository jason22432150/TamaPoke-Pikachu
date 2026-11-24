#include "hal/servo_reaction_session.h"
#include <cassert>
#include <vector>
using namespace tpkbody;
struct Fake:ServoPowerIO,ServoOutput{
  uint32_t now=0;
  bool rail=false,open=false,yaw=false,pitch=false,failSample=false,failOff=false;
  int failWrite=0;
  RawPose pos{460,620},goal{460,620};
  std::vector<int> writes;
  bool readRailLatch(bool& on)override{on=rail;return true;}
  bool openBus()override{open=true;return true;}
  void closeBus()override{open=false;}
  bool setRailLatch(bool on)override{if(!on&&failOff)return false;rail=on;return true;}
  uint32_t clockMs()override{return now;}
  bool sample(PowerSample& s)override{
    assert(open&&rail);
    s={{{pos.yaw,60,25,int(pos.yaw!=goal.yaw),int(yaw)},
         {pos.pitch,60,25,int(pos.pitch!=goal.pitch),int(pitch)},BSP_RAW,BSP_RAW,now},goal};
    return !failSample;
  }
  bool setTorque(uint8_t id,bool on)override{assert(open);(id==1?yaw:pitch)=on;return true;}
  bool writePosition(uint8_t id,uint16_t raw,uint16_t)override{
    assert(open&&rail&&yaw&&pitch);writes.push_back(id);
    if(id==failWrite)return false;
    (id==1?goal.yaw:goal.pitch)=raw;return true;
  }
  bool releaseTorque(uint8_t id)override{return setTorque(id,false);}
};
int main(){
  PowerGuard g{{false,false,false,false,true,80},true,true,true};
  ServoCenters c{460,620};
  Fake f;ServoReactionSession s(f,f);
  auto denied=g;denied.benchVerified=false;assert(!s.begin(denied,c,Reaction::None));
  assert(s.begin(g,c,Reaction::Eat));
  f.now=250;assert(s.tick(g,Reaction::Eat)==ReactionState::Waiting);
  f.now=300;assert(s.tick(g,Reaction::Eat)==ReactionState::Waiting&&f.writes.empty());
  f.now=350;s.tick(g,Reaction::None);
  f.now=400;assert(s.tick(g,Reaction::Happy)==ReactionState::Outbound);
  assert(f.goal.yaw==435&&f.goal.pitch==636);
  f.now=500;assert(s.tick(g,Reaction::Happy)==ReactionState::Outbound);
  f.now=1000;f.pos=f.goal;assert(s.tick(g,Reaction::Happy)==ReactionState::Returning);
  assert(f.goal.yaw==460&&f.goal.pitch==620);
  f.now=1600;f.pos=f.goal;assert(s.tick(g,Reaction::Happy)==ReactionState::Complete);
  assert(!f.rail&&!f.open&&!f.yaw&&!f.pitch&&f.writes.size()==4);
  assert(!s.begin(g,c,Reaction::None));
  Fake a;a.failWrite=2;ServoReactionSession x(a,a);
  assert(x.begin(g,c,Reaction::None));a.now=250;x.tick(g,Reaction::None);
  a.now=300;assert(x.tick(g,Reaction::Eat)==ReactionState::Fault&&!a.rail&&!a.open);
  Fake b;ServoReactionSession y(b,b);
  assert(y.begin(g,c,Reaction::None));b.now=250;y.tick(g,Reaction::None);
  b.now=300;y.tick(g,Reaction::Eat);
  b.now=1800;assert(y.tick(g,Reaction::Eat)==ReactionState::Fault&&!b.rail);
  Fake d;ServoReactionSession z(d,d);
  assert(z.begin(g,c,Reaction::None));d.now=250;z.tick(g,Reaction::None);
  d.failOff=true;assert(z.stop()==ReactionState::ShutdownUnconfirmed&&!d.open);
  Fake j;ServoReactionSession q(j,j);
  assert(q.begin(g,c,Reaction::None));j.now=250;q.tick(g,Reaction::None);
  g.game.menu=true;assert(q.tick(g,Reaction::Happy)==ReactionState::Fault&&!j.rail);
  g.game.menu=false;
  Fake k;ServoReactionSession t(k,k);
  assert(t.begin(g,c,Reaction::None));k.now=250;t.tick(g,Reaction::None);
  k.failSample=true;k.now=300;assert(t.tick(g,Reaction::Eat)==ReactionState::Fault&&!k.rail);
}
