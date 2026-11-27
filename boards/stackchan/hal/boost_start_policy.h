#pragma once
#include <stdint.h>
// K151-only experimental precharge. Preserve every other AW9523 latch bit.
namespace tpkboost {
constexpr uint8_t OUT=0x03,DIR=0x05,MASK=0x80;
template<class Read,class Write> bool prepare(Read read,Write write){
  uint8_t dir=0,out=0;
  if(!read(DIR,dir)||!read(OUT,out))return false;
  // Clear a high latch while still input. Never interrupt a driven-high rail.
  if((dir&MASK)&&(out&MASK)){
    if(!write(OUT,uint8_t(out&~MASK)))return false;
    uint8_t check=0;
    if(!read(OUT,check)||check!=uint8_t(out&~MASK))return false;
  }
  return true;
}
template<class Read,class Write,class Delay> bool start(Read read,Write write,Delay delay){
  uint8_t dir=0,out=0;
  if(!read(DIR,dir)||!read(OUT,out)||(dir&MASK))return false;
  if(out&MASK)return true;
  // Based on reported K151 workaround; actual pulse width includes I2C latency.
  const uint32_t recovery[]={30000,25000,20000,16000,13000,10000,8000,6000,
      5000,4000,3000,2500,2000,1500,1200,1000,800,600,400,300};
  for(uint32_t us:recovery){
    if(!write(OUT,uint8_t(out|MASK)))return false;
    delay(150);
    if(!write(OUT,out))return false;
    delay(us);
  }
  if(!write(OUT,uint8_t(out|MASK)))return false;
  delay(50000);
  uint8_t check=0;
  return read(OUT,check)&&check==uint8_t(out|MASK);
}
}
