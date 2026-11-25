#pragma once
#include <Arduino_GFX_Library.h>
#include <cstring>
#include "stackchan_hal.h"
#include "perf_policy.h"
#include "native_raster.h"

// Use Arduino_GFX (not Arduino_Canvas) so all primitives, including future
// generic bitmap calls, route through bounded physical-raster writes rather
// than the old canvas's direct 466x466 buffer operations.
class StackChanCanvas final : public Arduino_GFX {
  static constexpr int STRIP_ROWS=8;
  uint16_t strip_[HOME_W*STRIP_ROWS];
  uint16_t* pixels_=nullptr;
  tpkraster::Raster raster_;
  bool requestedHome_=false,presentedHome_=false;
  tpkperf::Monitor* perf_=nullptr;
public:
  StackChanCanvas():Arduino_GFX(GAME_SIZE,GAME_SIZE){setRotation(0);}
  ~StackChanCanvas(){if(pixels_)heap_caps_free(pixels_);}
  void setLandscapeHome(bool home){requestedHome_=home;raster_.mode(home);}
  bool landscapeRequested() const{return requestedHome_;}
  bool landscapePresented() const{return presentedHome_;}
  void attachPerf(tpkperf::Monitor& monitor){perf_=&monitor;}
  bool begin(int32_t = GFX_NOT_DEFINED) override {
    if(!pixels_)pixels_=static_cast<uint16_t*>(
      heap_caps_malloc(tpkraster::PIXELS*sizeof(uint16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(!pixels_)return false;
    raster_.begin(pixels_);
    raster_.mode(requestedHome_);
    fillScreen(0); M5.Display.fillScreen(0); return true;
  }
  void writePixelPreclipped(int16_t x,int16_t y,uint16_t color) override {
    raster_.rect(x,y,1,1,color);
  }
  void writeFillRectPreclipped(int16_t x,int16_t y,int16_t w,int16_t h,uint16_t color) override {
    raster_.rect(x,y,w,h,color);
  }
  void writeFastVLine(int16_t x,int16_t y,int16_t h,uint16_t color) override {
    raster_.rect(x,y,1,h,color);
  }
  void writeFastHLine(int16_t x,int16_t y,int16_t w,uint16_t color) override {
    raster_.rect(x,y,w,1,color);
  }
  void flush(bool = false) override {
    if(!pixels_)return;
    const bool measure=perf_&&perf_->enabled();
    const uint32_t started=measure?micros():0;
    const bool previousSwap=M5.Display.getSwapBytes();
    M5.Display.setSwapBytes(true);
    M5.Display.startWrite();
    const bool home=requestedHome_;
    const int width=raster_.width(),height=raster_.height();
    for(int y=0;y<height;y+=STRIP_ROWS){
      const int rows=(height-y<STRIP_ROWS)?height-y:STRIP_ROWS;
      // Keep synchronous internal-RAM strip transfers: never give the LCD
      // driver a PSRAM buffer that might outlive this render.
      memcpy(strip_,raster_.row(y),size_t(width)*rows*sizeof(uint16_t));
      M5.Display.pushImage(home?0:VIEW_X,(home?HOME_Y:VIEW_Y)+y,width,rows,strip_);
    }
    presentedHome_=home;
    M5.Display.endWrite();
    M5.Display.setSwapBytes(previousSwap);
    if(measure)perf_->flushed(micros()-started);
  }
};
struct StackChanPanel { void setBrightness(uint8_t value){M5.Display.setBrightness(value);} };
