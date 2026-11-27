#pragma once
#include <stdint.h>
namespace tpktrace {
enum Stage : uint32_t {
  Setup=1, SerialReady, NvsBefore, NvsAfter, FlashCheck, PsramBefore, PsramAfter,
  M5Before, GfxPrepareBefore, GfxPrepareAfter, GfxDirBefore, GfxDirAfter,
  GfxStartBefore, GfxFirstOnBefore, GfxFirstOnAfter, GfxStartAfter, GfxI2cFail,
  UnifiedStartBefore, UnifiedFirstOnBefore, UnifiedFirstOnAfter, UnifiedStartAfter,
  UnifiedI2cFail, M5After, DisplayReady, CanvasReady, MenuReady, MenuExit,
  GameReady, RestartRequest, InitFail, GfxLdoBefore, GfxLdoAfter,
  LightBefore, LightAfter, UnifiedPmicBefore, UnifiedPmicAfter,
  ExtBefore, ExtAfter, ExtWriteBefore, ExtWriteAfter, ExtI2cFail
};
static_assert(ExtI2cFail<=64,"stage mask capacity");
struct Record {
  uint32_t magic, seq, attempt, seen_lo, seen_hi, last, detail,
           error_stage, error_detail, reason, check;
};
static_assert(sizeof(Record)==44,"fixed record layout");
static constexpr uint32_t Magic=0x42314e32U; // B11N2
inline uint32_t checksum(const Record& r) {
  const uint32_t words[]={r.magic,r.seq,r.attempt,r.seen_lo,r.seen_hi,r.last,
      r.detail,r.error_stage,r.error_detail,r.reason};
  uint32_t h=2166136261u;
  for(uint32_t w:words){h^=w;h*=16777619u;}
  return h?h:1u;
}
inline bool seen(const Record& r,uint32_t stage) {
  if(stage<1||stage>64)return false;
  const uint32_t i=stage-1;
  return ((i<32?r.seen_lo:r.seen_hi)&(uint32_t(1)<<(i%32)))!=0;
}
inline bool valid(const Record& r) {
  return r.magic==Magic && r.last>=Setup && r.last<=ExtI2cFail &&
      seen(r,r.last) && r.check==checksum(r);
}
inline int latest(const Record& a,const Record& b){
  if(!valid(a))return valid(b)?1:-1;
  if(!valid(b))return 0;
  const uint32_t d=b.seq-a.seq;
  return d && d<0x80000000u?1:0;
}
inline Record begin(const Record* prior,uint32_t reason){
  return {Magic,prior?prior->seq:0u,prior?prior->attempt+1u:1u,0,0,0,0,0,0,reason,0};
}
inline void advance(Record& r,Stage stage,uint32_t detail){
  const uint32_t n=uint32_t(stage);
  if(n<Setup||n>ExtI2cFail)return;
  const uint32_t i=n-1;
  ++r.seq;
  (i<32?r.seen_lo:r.seen_hi)|=uint32_t(1)<<(i%32);
  r.last=n;r.detail=detail;
  if((stage==GfxI2cFail||stage==UnifiedI2cFail||stage==ExtI2cFail||stage==InitFail)&&!r.error_stage){
    r.error_stage=stage;r.error_detail=detail;
  }
  r.check=checksum(r);
}
}
extern "C" void tpk_boot_mark(uint32_t stage,uint32_t detail);
extern "C" bool tpk_boot_early();
void tpk_boot_begin();
void tpk_boot_report();
void tpk_boot_restart();
