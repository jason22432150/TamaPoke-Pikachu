#include "hal/serial_line_policy.h"
#include "hal/head_touch_policy.h"
#include "hal/body_policy.h"
#include <cassert>
#include <cstring>
int main(){
  tpkserial::Line l;
  using R=tpkserial::Result;
  auto send=[&](const char* s){R r=R::Pending;while(*s)r=l.feed(uint8_t(*s++));return r;};
  assert(send("PERF")==R::Pending&&l.pending()==4);
  assert(send("?\r\n")==R::Ready&&std::strcmp(l.text(),"PERF?")==0);
  assert(send("WI\rPE\n")==R::Rejected);
  assert(send("TIME\n")==R::Ready&&std::strcmp(l.text(),"TIME")==0);
  for(int i=0;i<257;i++)assert(l.feed('X')==R::Pending);
  assert(l.discarding());assert(send("WIPE\n")==R::Rejected);
  assert(send("PUT /mons/p001.bin 123\n")==R::Ready);
  assert(l.feed(0)==R::Pending);assert(l.feed('\n')==R::Rejected);
  assert(l.accepted()==3&&l.rejected()==3);
  using E=tpkhead::Event;
  tpkhead::Gesture g;
  auto left=tpkhead::decode(3),right=tpkhead::decode(48),none=tpkhead::decode(0);
  assert(left.position()==-100&&right.position()==100);
  assert(g.update(left)==E::None); // held at startup
  assert(g.update(none)==E::None&&g.update(none)==E::None);
  assert(g.update(left)==E::None&&g.update(left)==E::Press);
  assert(g.update(right)==E::Forward&&g.update(left)==E::None);
  assert(g.update(none)==E::None&&g.update(none)==E::Release);
  assert(g.update(right)==E::None&&g.update(right)==E::Press);
  assert(g.update(left)==E::Backward);
  g.reset();assert(g.update(left)==E::None);
  tpkbody::PetState p={false,false,false,false,false,false,false,80,80};
  assert(tpkbody::ledAllowed(p));p.batteryPercent=10;assert(!tpkbody::ledAllowed(p));
  assert((tpkbody::testColor(0)==tpkbody::Color{24,0,0}));
  assert((tpkbody::testColor(1000)==tpkbody::Color{0,24,0}));
  assert((tpkbody::testColor(2000)==tpkbody::Color{0,0,24}));
}
