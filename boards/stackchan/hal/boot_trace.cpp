#include "boot_trace.h"
#if defined(BOARD_STACKCHAN) && BOARD_STACKCHAN && defined(TPK_BOOT_TRACE) && TPK_BOOT_TRACE
#include <Arduino.h>
#include <esp_attr.h>
#include <esp_system.h>
#include <inttypes.h>
namespace {
using namespace tpktrace;
// RTC slow/retained memory, NOT NVS or the external calendar RTC.
RTC_NOINIT_ATTR static volatile Record slots[2];
static Record current, previous;
static int slot=-1;
static bool started=false, previousValid=false, earlyDone=false;
static uint32_t resetReason;
static tpkpmic::Snapshot pmicSnapshot={};
static Record readSlot(int i){
  const volatile Record& s=slots[i];
  return {s.magic,s.seq,s.attempt,s.seen_lo,s.seen_hi,s.last,s.detail,
          s.error_stage,s.error_detail,s.reason,s.check};
}
static void barrier(){asm volatile("memw" ::: "memory");}
static void persist(){
  const int next=slot==0?1:0;
  volatile Record& d=slots[next];
  d.check=0;barrier();
  d.magic=current.magic;d.seq=current.seq;d.attempt=current.attempt;
  d.seen_lo=current.seen_lo;d.seen_hi=current.seen_hi;d.last=current.last;
  d.detail=current.detail;d.error_stage=current.error_stage;
  d.error_detail=current.error_detail;d.reason=current.reason;
  barrier();d.check=current.check;barrier();slot=next;
}
static void printRecord(const char* label,const Record& r){
  Serial.printf("BOOTTRACE %s attempt=%" PRIu32 " seq=%" PRIu32
      " seen=0x%08" PRIx32 "%08" PRIx32 " last=%" PRIu32 " detail=0x%" PRIx32
      " error_stage=%" PRIu32 " error_detail=0x%" PRIx32 " boot_reset_reason=%" PRIu32 "\n",
      label,r.attempt,r.seq,r.seen_hi,r.seen_lo,r.last,r.detail,r.error_stage,r.error_detail,r.reason);
}
}
extern "C" bool tpk_boot_early(){return started&&!earlyDone;}
extern "C" bool tpk_pmic_claim(){
  if(!tpk_boot_early()||pmicSnapshot.attempted)return false;
  pmicSnapshot.attempted=true;
  return true;
}
extern "C" void tpk_pmic_record(uint8_t reg,bool ok,uint8_t value){
  if(!pmicSnapshot.attempted||!tpk_boot_early()||!ok)return;
  for(unsigned i=0;i<tpkpmic::count;++i){
    if(tpkpmic::registers[i]==reg){
      pmicSnapshot.value[i]=value;
      pmicSnapshot.valid|=uint16_t(1u<<i);
      return;
    }
  }
}
void tpk_pmic_report(){
  Serial.printf("PMIC SNAPSHOT schema=B11O1 source=gfx-before-power-writes attempted=%u valid=0x%04x\n",
      unsigned(pmicSnapshot.attempted),unsigned(pmicSnapshot.valid));
  for(unsigned i=0;i<tpkpmic::count;++i){
    if(pmicSnapshot.valid&(1u<<i))
      Serial.printf("PMIC reg=0x%02x value=0x%02x\n",unsigned(tpkpmic::registers[i]),unsigned(pmicSnapshot.value[i]));
    else Serial.printf("PMIC reg=0x%02x value=unavailable\n",unsigned(tpkpmic::registers[i]));
  }
  Serial.println("DONE PMIC");
}
extern "C" void tpk_boot_mark(uint32_t stage,uint32_t detail){
  // Synchronous startup task only. No Serial, allocation, I2C or Flash/NVS.
  if(!started||stage<tpktrace::Setup||stage>tpktrace::ExtI2cFail)return;
  tpktrace::advance(current,static_cast<tpktrace::Stage>(stage),detail);persist();
  if(stage==tpktrace::M5After||stage==tpktrace::InitFail)earlyDone=true;
}
void tpk_boot_begin(){
  if(started)return;
  const auto a=readSlot(0),b=readSlot(1);
  slot=tpktrace::latest(a,b);previousValid=slot>=0;
  if(previousValid)previous=slot==0?a:b;
  resetReason=static_cast<uint32_t>(esp_reset_reason());
  current=tpktrace::begin(previousValid?&previous:nullptr,resetReason);
  started=true;tpk_boot_mark(tpktrace::Setup,0);
}
void tpk_boot_report(){
  Serial.printf("BOOTTRACE schema=B11N2 reset_reason=%" PRIu32
      " prior_valid=%d prior_attribution=%s\n",resetReason,int(previousValid),
      !previousValid?"none":resetReason==ESP_RST_POWERON?"poweron-unverified":"retained-unverified");
  if(previousValid)printRecord("prior",previous);
  if(started)printRecord("current",current);
  Serial.println("DONE BOOTTRACE");
}
void tpk_boot_restart(){
  tpk_boot_mark(tpktrace::RestartRequest,0);
  esp_restart();
}
#endif
