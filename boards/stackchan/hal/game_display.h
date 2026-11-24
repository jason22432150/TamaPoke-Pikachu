#pragma once
#include <Arduino_GFX_Library.h>
#include "stackchan_hal.h"
class StackChanCanvas final : public Arduino_Canvas {
  static constexpr int STRIP_ROWS=8;
  uint16_t strip_[VIEW_SIZE*STRIP_ROWS];
  uint16_t xMap_[VIEW_SIZE];
public:
  StackChanCanvas():Arduino_Canvas(466,466,nullptr){}
  bool begin(int32_t = GFX_NOT_DEFINED) override {
    if(!_framebuffer) _framebuffer=static_cast<uint16_t*>(
      heap_caps_malloc(466UL*466*2,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(!_framebuffer) return false;
    for(int x=0;x<VIEW_SIZE;x++) xMap_[x]=logicalAxis(x);
    fillScreen(0); M5.Display.fillScreen(0); return true;
  }
  void flush(bool = false) override {
    if(!_framebuffer) return;
    // Arduino_Canvas stores native uint16_t RGB565. M5GFX's uint16_t
    // overload interprets it as rgb565_t only with swap enabled.
    const bool previousSwap=M5.Display.getSwapBytes();
    M5.Display.setSwapBytes(true);
    M5.Display.startWrite();
    for(int y=0;y<VIEW_SIZE;y+=STRIP_ROWS) {
      const int rows=(VIEW_SIZE-y<STRIP_ROWS)?VIEW_SIZE-y:STRIP_ROWS;
      for(int j=0;j<rows;j++)
        scaleGameRow(_framebuffer,strip_+j*VIEW_SIZE,y+j,xMap_);
      // Synchronous pushImage, not pushImageDMA: the strip can be reused.
      M5.Display.pushImage(VIEW_X,VIEW_Y+y,VIEW_SIZE,rows,strip_);
    }
    M5.Display.endWrite();
    M5.Display.setSwapBytes(previousSwap);
  }
};
struct StackChanPanel { void setBrightness(uint8_t value){M5.Display.setBrightness(value);} };
