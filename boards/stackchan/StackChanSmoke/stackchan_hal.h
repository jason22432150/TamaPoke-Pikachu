#pragma once
#include "board_hal.h"
#include <M5Unified.h>
class StackChanHAL final : public BoardHAL {
public:
  bool begin() override {
    auto cfg = M5.config();
    cfg.internal_mic = false;
    cfg.internal_spk = true;
    M5.begin(cfg);
    M5.Display.setRotation(1);
    return M5.Display.width() == 320 && M5.Display.height() == 240;
  }
  void update() override { M5.update(); }
  TouchPoint touch() override {
    auto d = M5.Touch.getDetail();
    return {int16_t(d.x), int16_t(d.y), d.isPressed()};
  }
  void tone(uint16_t hz, uint16_t ms) override {
    M5.Speaker.setVolume(48);
    M5.Speaker.tone(hz, ms);
  }
  int batteryPercent() override { return M5.Power.getBatteryLevel(); }
  void brightness(uint8_t value) override { M5.Display.setBrightness(value); }
};
