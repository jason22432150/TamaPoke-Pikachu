#include "hal/body_policy.h"
#include <cassert>
using namespace tpkbody;
int main(){
  PetState p={false,false,false,false,false,false,false,80,80};
  assert((colorFor(p)==Color{0,8,12}));
  p.lowestStat=24; assert((colorFor(p)==Color{24,4,0}));
  p.egg=true; assert((colorFor(p)==Color{8,12,24}));
  p.eating=true; assert((colorFor(p)==Color{0,24,0}));
  p.heart=true; assert((colorFor(p)==Color{24,0,12}));
  p.evolving=true; assert((colorFor(p)==Color{28,24,0}));
  p.ceremony=true; assert((colorFor(p)==Color{12,0,24}));
  p.sleeping=true; assert((colorFor(p)==Color{0,0,0}));
  p.sleeping=false;p.screenOff=true; assert((colorFor(p)==Color{0,0,0}));
  p.screenOff=false;p.batteryPercent=10;assert((colorFor(p)==Color{0,0,0}));
  p.batteryPercent=-1;assert((colorFor(p)==Color{0,0,0}));
  for(int flags=0;flags<128;flags++){
    p={bool(flags&1),bool(flags&2),bool(flags&4),bool(flags&8),bool(flags&16),
       bool(flags&32),bool(flags&64),80,10};
    auto c=colorFor(p);assert(c.r<=32 && c.g<=32 && c.b<=32);
  }
  assert(calibrationPresent(460,620));
  assert(!calibrationPresent(-1,620));
  assert(!calibrationPresent(460,-1));
  assert(!calibrationPresent(0,620));
  assert(!calibrationPresent(460,1000));
}
