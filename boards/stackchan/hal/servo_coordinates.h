#pragma once
#include "motion_policy.h"

namespace tpkbody {
struct RawRange { int lo,hi; };
struct ServoCenters { int yaw,pitch; };
struct RawPose { int yaw,pitch; };
constexpr RawRange BSP_RAW={0,1000};
constexpr int RAW_MARGIN=8;
// BSP 1.1.0: angle in tenths of a degree, 1 raw unit = 0.3125 degree.
// Use the original truncation toward zero; reject unsafe targets, never clamp.
inline int rawOffset(int16_t angle) {return int(angle)*16/50;}
inline bool validRange(RawRange r) {
  return r.lo>=BSP_RAW.lo && r.hi<=BSP_RAW.hi && r.hi-r.lo>=2*RAW_MARGIN;
}
inline bool insideRange(int value,RawRange r) {
  return validRange(r) && value>=r.lo+RAW_MARGIN && value<=r.hi-RAW_MARGIN;
}
inline bool safeEnvelope(ServoCenters c,RawRange yaw,RawRange pitch) {
  return calibrationPresent(c.yaw,c.pitch) &&
    insideRange(c.yaw+rawOffset(-YAW_MAX),yaw) &&
    insideRange(c.yaw+rawOffset(YAW_MAX),yaw) &&
    insideRange(c.pitch,pitch) &&
    insideRange(c.pitch+rawOffset(PITCH_MAX),pitch);
}
inline bool mapPose(Pose p,ServoCenters c,RawRange yaw,RawRange pitch,RawPose& out) {
  if(!safePose(p)||!safeEnvelope(c,yaw,pitch))return false;
  RawPose candidate={c.yaw+rawOffset(p.yaw),c.pitch+rawOffset(p.pitch)};
  if(!insideRange(candidate.yaw,yaw)||!insideRange(candidate.pitch,pitch))return false;
  out=candidate;return true;
}
inline bool feedbackInEnvelope(RawPose current,ServoCenters c,RawRange yaw,RawRange pitch) {
  return safeEnvelope(c,yaw,pitch) &&
    insideRange(current.yaw,yaw) && insideRange(current.pitch,pitch) &&
    current.yaw>=c.yaw+rawOffset(-YAW_MAX) &&
    current.yaw<=c.yaw+rawOffset(YAW_MAX) &&
    current.pitch>=c.pitch && current.pitch<=c.pitch+rawOffset(PITCH_MAX);
}
}
