#pragma once
#include "board_hal.h"
#include "efuse_policy.h"
#include <M5Unified.h>
#include <Arduino.h>
#include <esp_heap_caps.h>
#include <time.h>
class StackChanHAL final : public BoardHAL {
  bool ready_ = false;
  static bool testPsram() {
    constexpr size_t words = (466UL*466*2+3)/4;
    if (!psramFound() || ESP.getPsramSize()!=8UL*1024*1024) return false;
    volatile uint32_t* p = static_cast<volatile uint32_t*>(
        heap_caps_malloc(words*sizeof(uint32_t), MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if (!p) return false;
    bool ok=true;
    for (unsigned pass=0;pass<2;pass++) {
      for (size_t i=0;i<words;i++) p[i]=uint32_t(i)^ (pass?0xAAAAAAAAu:0x55555555u);
      for (size_t i=0;i<words;i++)
        if(p[i]!=(uint32_t(i)^(pass?0xAAAAAAAAu:0x55555555u))) {ok=false;break;}
      if(!ok) break;
    }
    heap_caps_free(const_cast<uint32_t*>(p));
    return ok;
  }
public:
  BootStatus begin() override {
    if (ESP.getFlashChipSize()!=16UL*1024*1024) return BootStatus::Flash;
    if (!testPsram()) return BootStatus::Psram;
    auto cfg=M5.config();
    cfg.internal_mic=false;
    cfg.internal_spk=true;
    M5.begin(cfg);
    if(M5.getBoard()!=m5gfx::board_t::board_M5StackChan) return BootStatus::Board;
    if(M5.Display.width()!=320 || M5.Display.height()!=240) M5.Display.setRotation(1);
    if(M5.Display.width()!=320 || M5.Display.height()!=240) return BootStatus::Display;
    if(!M5.Touch.isEnabled()) return BootStatus::Touch;
    ready_=true;
    return BootStatus::Ok;
  }
  void update() override { if(ready_) M5.update(); }
  TouchPoint touch() override {
    if(!ready_) return {0,0,false};
    auto d=M5.Touch.getDetail();
    return {int16_t(d.x),int16_t(d.y),d.isPressed()};
  }
  void tone(uint16_t hz,uint16_t ms) override {
    if(ready_) { M5.Speaker.setVolume(48); M5.Speaker.tone(hz,ms); }
  }
  int batteryPercent() override { return ready_?M5.Power.getBatteryLevel():-1; }
  void brightness(uint8_t value) override { if(ready_) M5.Display.setBrightness(value); }
  bool rtcAvailable() const { return ready_ && M5.Rtc.isEnabled(); }
};
