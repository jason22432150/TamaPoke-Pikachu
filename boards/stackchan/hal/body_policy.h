#pragma once
#include <stdint.h>
namespace tpkbody {
struct Color {
  uint8_t r,g,b;
  bool operator==(const Color& c) const { return r==c.r && g==c.g && b==c.b; }
  bool operator!=(const Color& c) const { return !(*this==c); }
};
struct PetState {
  bool sleeping,screenOff,evolving,heart,eating,egg,ceremony;
  int batteryPercent;
  uint8_t lowestStat;
};
inline bool ledAllowed(const PetState& p){return !p.screenOff&&!p.sleeping&&p.batteryPercent>10&&p.batteryPercent<=100;}
inline Color testColor(uint32_t elapsed){return elapsed<1000?Color{24,0,0}:elapsed<2000?Color{0,24,0}:Color{0,0,24};}
inline Color colorFor(const PetState& p) {
  if(!ledAllowed(p))
    return {0,0,0};
  if(p.ceremony) return {12,0,24};
  if(p.evolving) return {28,24,0};
  if(p.heart) return {24,0,12};
  if(p.eating) return {0,24,0};
  if(p.egg) return {8,12,24};
  if(p.lowestStat<25) return {24,4,0};
  return {0,8,12};
}
// A raw calibration reading is not proof of safe mechanical travel.
// No default center may be substituted for missing factory calibration.
inline bool calibrationPresent(int yaw,int pitch) {
  return yaw>0 && yaw<1000 && pitch>0 && pitch<1000;
}
}
