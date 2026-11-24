#include "hal/motion_policy.h"
#include <cassert>
#include <initializer_list>
using namespace tpkbody;
int main(){
  MotionSafety s={false,false,false,false,true,80};
  MotionPolicy m;
  assert(m.update(0,s,Reaction::Happy).action==Action::None);
  for(int flags=1;flags<16;flags++){
    MotionSafety blocked={bool(flags&1),bool(flags&2),bool(flags&4),bool(flags&8),true,80};
    assert(!m.arm(0,blocked));
  }
  s.calibrationValid=false;assert(!m.arm(0,s));s.calibrationValid=true;
  for(int pct:{-1,0,24,101}) {s.batteryPercent=pct;assert(!m.arm(0,s));}
  s.batteryPercent=25;
  assert(m.arm(100,s));assert(!m.arm(100,s));
  auto c=m.update(100,s,Reaction::Happy);assert(c.action==Action::Pose&&safePose(c.pose));
  assert(m.update(1599,s,Reaction::Happy).action==Action::None);
  c=m.update(1600,s,Reaction::Happy);assert(c.action==Action::Pose&&c.pose.yaw==0&&c.pose.pitch==0);
  assert(m.update(3100,s,Reaction::Happy).action==Action::Stop);
  assert(m.update(3200,s,Reaction::Eat).action==Action::None);
  assert(m.update(9100,s,Reaction::Eat).action==Action::None);
  assert(m.update(9101,s,Reaction::Play).action==Action::Pose);
  s.screenOff=true;assert(m.update(9102,s,Reaction::Play).action==Action::Stop);assert(!m.enabled());
  s.screenOff=false;assert(m.arm(10000,s));
  assert(m.update(10000,s,Reaction::Hatch).action==Action::Pose);
  assert(m.update(13000,s,Reaction::Hatch).action==Action::Stop);assert(!m.enabled());
  assert(m.arm(20000,s));assert(m.update(80000,s,Reaction::Happy).action==Action::None);assert(!m.enabled());
  assert(m.arm(UINT32_MAX-100,s));assert(m.update(UINT32_MAX-100,s,Reaction::Evolve).action==Action::Pose);
  assert(m.update(1399,s,Reaction::Evolve).action==Action::Pose);
  assert(m.stop().action==Action::Stop);assert(!m.enabled());
  assert(!safePose({101,0,100}));assert(!safePose({0,-1,100}));assert(!safePose({0,0,201}));
  for(unsigned i=0;i<=unsigned(Reaction::Play);i++)assert(safePose(reactionPose(Reaction(i))));
}
