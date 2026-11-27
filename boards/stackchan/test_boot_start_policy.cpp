#include "hal/boot_start_policy.h"
#include <cassert>
using namespace tpkboot;
int main(){
  const TouchPoint up={0,0,false},start={40,90,true},diag={40,150,true},outside={0,0,true};
  Gate a(100);assert(a.secondsLeft(100)==3);
  assert(a.update(100,up)==Action::Wait);assert(a.secondsLeft(1100)==2);
  assert(a.update(3099,up)==Action::Wait);assert(a.update(3100,up)==Action::StartAuto);
  Gate b(0);b.update(0,up);assert(b.update(2999,diag)==Action::Wait);
  assert(!b.automatic()&&b.update(3000,up)==Action::Wait);
  assert(b.update(999999,up)==Action::Wait);
  b.update(1000000,start);assert(b.update(1000020,up)==Action::StartTouch);
  Gate c(0);c.update(0,start);assert(c.update(20,up)==Action::Wait&&!c.automatic());
  c.update(40,start);c.update(60,outside);c.update(80,start);assert(c.update(100,up)==Action::Wait);
  c.update(120,start);assert(c.update(140,up)==Action::StartTouch);
  Gate d(0);d.update(0,up);assert(d.update(3000,diag)==Action::Wait);
  assert(d.update(3020,up)==Action::Wait);
  assert(d.update(5000,up,Command::Start)==Action::StartSerial);
  Gate e(0);assert(e.update(3000,up,Command::Calibration)==Action::Wait&&!e.automatic());
  assert(e.update(100000,up)==Action::Wait);
  Gate f(0);f.update(0,up);f.update(20,start);
  assert(f.update(40,up,Command::Diagnostic)==Action::Wait);
  assert(f.update(60,up,Command::Start)==Action::StartSerial);
  Gate g(UINT32_MAX-999);g.update(UINT32_MAX-999,up);
  assert(g.secondsLeft(0)==2);assert(g.update(1999,up)==Action::Wait);
  assert(g.update(2000,up)==Action::StartAuto);
  assert(hit({20,66,true})==Choice::Start&&hit({299,117,true})==Choice::Start);
  assert(hit({300,117,true})==Choice::None&&hit({20,118,true})==Choice::None);
  assert(hit({20,130,true})==Choice::Diagnostic&&hit({299,181,true})==Choice::Diagnostic);
}
