#pragma once
#include <stdint.h>
struct TouchPoint { int16_t x, y; bool pressed; };
struct LogicalPoint { int16_t x, y; bool valid; };
constexpr int VIEW_X=40, VIEW_Y=0, VIEW_SIZE=240, GAME_SIZE=466;
inline LogicalPoint toLogical(TouchPoint p) {
  if (!p.pressed || p.x<VIEW_X || p.x>=VIEW_X+VIEW_SIZE ||
      p.y<VIEW_Y || p.y>=VIEW_Y+VIEW_SIZE) return {0,0,false};
  return {int16_t(((p.x-VIEW_X)*(GAME_SIZE-1)+(VIEW_SIZE-1)/2)/(VIEW_SIZE-1)),
          int16_t(((p.y-VIEW_Y)*(GAME_SIZE-1)+(VIEW_SIZE-1)/2)/(VIEW_SIZE-1)),true};
}
inline TouchPoint toPhysical(LogicalPoint p) {
  if (!p.valid || p.x<0 || p.x>=GAME_SIZE || p.y<0 || p.y>=GAME_SIZE)
    return {0,0,false};
  return {int16_t(VIEW_X+(p.x*(VIEW_SIZE-1)+(GAME_SIZE-1)/2)/(GAME_SIZE-1)),
          int16_t(VIEW_Y+(p.y*(VIEW_SIZE-1)+(GAME_SIZE-1)/2)/(GAME_SIZE-1)),true};
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
