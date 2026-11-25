#pragma once
#include <stdint.h>
struct TouchPoint { int16_t x, y; bool pressed; };
struct LogicalPoint { int16_t x, y; bool valid; };
constexpr int VIEW_X=40, VIEW_Y=0, VIEW_SIZE=240, GAME_SIZE=466;
// Shared nearest-neighbour sampling for display and touch.
constexpr int logicalAxis(int pixel) {
  return (pixel*(GAME_SIZE-1)+(VIEW_SIZE-1)/2)/(VIEW_SIZE-1);
}
inline void scaleGameRow(const uint16_t* frame, uint16_t* out, int y, const uint16_t* xMap) {
  const uint16_t* src=frame+logicalAxis(y)*GAME_SIZE;
  for(int x=0;x<VIEW_SIZE;x++) out[x]=src[xMap[x]];
}
inline LogicalPoint toLogical(TouchPoint p) {
  if (!p.pressed || p.x<VIEW_X || p.x>=VIEW_X+VIEW_SIZE ||
      p.y<VIEW_Y || p.y>=VIEW_Y+VIEW_SIZE) return {0,0,false};
  return {int16_t(logicalAxis(p.x-VIEW_X)),
          int16_t(logicalAxis(p.y-VIEW_Y)),true};
}
inline TouchPoint toPhysical(LogicalPoint p) {
  if (!p.valid || p.x<0 || p.x>=GAME_SIZE || p.y<0 || p.y>=GAME_SIZE)
    return {0,0,false};
  return {int16_t(VIEW_X+(p.x*(VIEW_SIZE-1)+(GAME_SIZE-1)/2)/(GAME_SIZE-1)),
          int16_t(VIEW_Y+(p.y*(VIEW_SIZE-1)+(GAME_SIZE-1)/2)/(GAME_SIZE-1)),true};
}
// Landscape home uses the same isotropic sampling as the compatibility view.
constexpr int HOME_W=320, HOME_Y=36, HOME_H=160, HOME_BOTTOM=HOME_Y+HOME_H;
constexpr int HOME_X=(HOME_W-VIEW_SIZE)/2;
constexpr int homeLogicalX(int x) {
  return logicalAxis(x<HOME_X?0:x>=HOME_X+VIEW_SIZE?VIEW_SIZE-1:x-HOME_X);
}
inline LogicalPoint homeToLogical(TouchPoint p) {
  if(!p.pressed || p.x<0 || p.x>=HOME_W || p.y<HOME_Y || p.y>=HOME_BOTTOM)
    return {0,0,false};
  return {int16_t(homeLogicalX(p.x)),int16_t(logicalAxis(p.y-HOME_Y)),true};
}
inline void scaleHomeRow(const uint16_t* frame,uint16_t* out,int y,const uint16_t* xMap) {
  const uint16_t* src=frame+logicalAxis(y)*GAME_SIZE;
  // Extend the edge scenery, not the central pet or text. No aspect-ratio stretch.
  for(int x=0;x<HOME_W;x++)out[x]=src[xMap[x]];
}
enum class BootStatus { Ok, Flash, Psram, Board, Display, Touch };
class BoardHAL {
public:
  virtual ~BoardHAL() = default;
  virtual BootStatus begin() = 0;
  virtual void update() = 0;
  virtual TouchPoint touch() = 0;
  virtual void tone(uint16_t hz, uint16_t ms) = 0;
  virtual int batteryPercent() = 0;
  virtual void brightness(uint8_t value) = 0;
};
