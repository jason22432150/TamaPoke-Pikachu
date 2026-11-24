#pragma once
#include <stdint.h>
struct TouchPoint { int16_t x, y; bool pressed; };
struct LogicalPoint { int16_t x, y; bool valid; };
// Preserve original 466x466 game coordinates in a centered 240x240 viewport.
inline LogicalPoint toLogical(TouchPoint p) {
  if (!p.pressed || p.x < 40 || p.x >= 280 || p.y < 0 || p.y >= 240)
    return {0, 0, false};
  return {int16_t((p.x-40)*465/239), int16_t(p.y*465/239), true};
}
class BoardHAL {
public:
  virtual ~BoardHAL() = default;
  virtual bool begin() = 0;
  virtual void update() = 0;
  virtual TouchPoint touch() = 0;
  virtual void tone(uint16_t hz, uint16_t ms) = 0;
  virtual int batteryPercent() = 0;
  virtual void brightness(uint8_t value) = 0;
};
