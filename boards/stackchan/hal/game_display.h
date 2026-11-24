#pragma once
#include <Arduino_GFX_Library.h>
#include "stackchan_hal.h"
class StackChanCanvas final : public Arduino_Canvas {
  uint16_t row_[240];
public:
  StackChanCanvas():Arduino_Canvas(466,466,nullptr){}
  bool begin(int32_t = GFX_NOT_DEFINED) override {
    if(!_framebuffer) _framebuffer=static_cast<uint16_t*>(
      heap_caps_malloc(466UL*466*2,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(!_framebuffer) return false;
    fillScreen(0); M5.Display.fillScreen(0); return true;
  }
  void flush(bool = false) override {
    if(!_framebuffer) return;
    M5.Display.startWrite();
    for(int y=0;y<VIEW_SIZE;y++) {
      const auto src=toLogical({VIEW_X,int16_t(y),true});
      for(int x=0;x<VIEW_SIZE;x++) {
        const auto q=toLogical({int16_t(x+VIEW_X),int16_t(y),true});
        row_[x]=_framebuffer[size_t(src.y)*GAME_SIZE+q.x];
      }
      M5.Display.pushImage(VIEW_X,y,VIEW_SIZE,1,row_);
    }
    M5.Display.endWrite();
  }
};
struct StackChanPanel { void setBrightness(uint8_t value){M5.Display.setBrightness(value);} };
