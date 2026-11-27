#include "hal/boot_trace.h"
#include <cassert>
using namespace tpktrace;
int main(){
  Record empty={}; assert(!valid(empty));assert(latest(empty,empty)==-1);
  auto a=begin(nullptr,1);assert(!valid(a));advance(a,Setup,0);assert(valid(a));
  auto b=a;advance(b,PsramBefore,0);assert(valid(b)&&latest(a,b)==1);
  auto torn=b;torn.check=0;assert(latest(a,torn)==0);
  torn=b;torn.detail^=1;assert(latest(a,torn)==0);
  advance(b,PsramAfter,0);advance(b,GfxI2cFail,0x105);
  advance(b,ExtWriteBefore,0x783);advance(b,ExtI2cFail,0x202);
  advance(b,InitFail,0x300);
  assert(b.error_stage==GfxI2cFail&&b.error_detail==0x105);
  assert(seen(b,PsramBefore)&&seen(b,ExtWriteBefore)&&seen(b,ExtI2cFail));
  assert(!seen(b,0)&&!seen(b,65)&&!seen(b,GameReady));assert(b.last==InitFail);
  auto c=begin(&b,3);advance(c,Setup,0);assert(c.attempt==2&&c.error_stage==0&&c.seen_lo==1&&c.seen_hi==0);
  assert(latest(b,c)==1);assert(c.reason==3);
  a.seq=0xffffffffu;a.check=checksum(a);b=a;advance(b,SerialReady,0);assert(b.seq==0&&latest(a,b)==1);
  for(uint32_t i=1;i<=ExtI2cFail;++i){auto r=begin(nullptr,0);advance(r,static_cast<Stage>(i),i);assert(valid(r)&&seen(r,i));}
  auto unchanged=b;advance(b,static_cast<Stage>(0),0);assert(b.check==unchanged.check);
  tpkpmic::Snapshot snapshot={};
  unsigned calls=0;
  tpkpmic::capture(snapshot,[&](uint8_t reg,uint8_t& value){
    assert(reg==tpkpmic::registers[calls++]);
    value=reg;return reg!=0x49;
  });
  assert(snapshot.attempted && calls==tpkpmic::count);
  assert(tpkpmic::registers[0]==0x21 && snapshot.value[0]==0x21);
  assert(snapshot.valid==uint16_t(((1u<<tpkpmic::count)-1u)&~(1u<<8)));
  tpkpmic::capture(snapshot,[&](uint8_t,uint8_t&){++calls;return true;});
  assert(calls==tpkpmic::count);
}
