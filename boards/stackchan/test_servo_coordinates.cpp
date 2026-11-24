#include "hal/servo_coordinates.h"
#include <cassert>
using namespace tpkbody;
int main(){
  ServoCenters c{460,620};
  RawPose p{-1,-1};
  assert(rawOffset(-80)==-25 && rawOffset(100)==32 && rawOffset(60)==19);
  assert(safeEnvelope(c,BSP_RAW,BSP_RAW));
  assert(mapPose({-80,50,150},c,BSP_RAW,BSP_RAW,p));
  assert(p.yaw==435 && p.pitch==636);
  for(int y=-YAW_MAX;y<=YAW_MAX;y++)for(int x=0;x<=PITCH_MAX;x++){
    assert(mapPose({int16_t(y),int16_t(x),100},c,BSP_RAW,BSP_RAW,p));
    assert(feedbackInEnvelope(p,c,BSP_RAW,BSP_RAW));
  }
  assert(!safeEnvelope({-1,620},BSP_RAW,BSP_RAW));
  assert(!safeEnvelope({20,620},BSP_RAW,BSP_RAW));
  assert(!safeEnvelope({460,970},BSP_RAW,BSP_RAW));
  assert(!safeEnvelope(c,{0,0},BSP_RAW)); // PWM mode or unreadable range
  assert(!safeEnvelope(c,{500,400},BSP_RAW));
  assert(!safeEnvelope(c,{0,1023},BSP_RAW));
  assert(!safeEnvelope(c,{440,480},BSP_RAW)); // entire travel must fit
  assert(safeEnvelope(c,{420,500},{612,660}));
  p={123,456};
  assert(!mapPose({101,0,100},c,BSP_RAW,BSP_RAW,p));
  assert(p.yaw==123 && p.pitch==456);
  assert(!mapPose({0,-1,100},c,BSP_RAW,BSP_RAW,p));
  assert(!mapPose({0,0,0},c,BSP_RAW,BSP_RAW,p));
  assert(!feedbackInEnvelope({427,620},c,BSP_RAW,BSP_RAW));
  assert(!feedbackInEnvelope({460,619},c,BSP_RAW,BSP_RAW));
  assert(!feedbackInEnvelope({460,653},c,BSP_RAW,BSP_RAW));
}
