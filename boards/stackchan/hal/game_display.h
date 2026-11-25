#pragma once
#include <Arduino_GFX_Library.h>
#include <cstring>
#include "stackchan_hal.h"
#include "perf_policy.h"
#include "native_raster.h"
#include "dirty_rect.h"

// Use Arduino_GFX (not Arduino_Canvas) so all primitives, including future
// generic bitmap calls, route through bounded physical-raster writes rather
// than the old canvas's direct 466x466 buffer operations.
class StackChanCanvas final : public Arduino_GFX {
  static constexpr int STRIP_ROWS=tpkdirty::STRIP_ROWS;
  uint16_t strip_[HOME_W*STRIP_ROWS];
  uint16_t* pixels_=nullptr;
  uint16_t* previous_=nullptr;
  bool previousValid_=false,dirtyEnabled_=true;
  tpkdirty::Counters lcd_;
  tpkraster::Raster raster_;
  bool requestedHome_=false,presentedHome_=false;
  tpkperf::Monitor* perf_=nullptr;
public:
  StackChanCanvas():Arduino_GFX(GAME_SIZE,GAME_SIZE){setRotation(0);}
  ~StackChanCanvas(){if(pixels_)heap_caps_free(pixels_);if(previous_)heap_caps_free(previous_);}
  void invalidate(){previousValid_=false;}
  void setDirtyEnabled(bool enabled){dirtyEnabled_=enabled;invalidate();}
  bool dirtyActive()const{return dirtyEnabled_&&previous_;}
  bool cacheAvailable()const{return previous_!=nullptr;}
  const tpkdirty::Counters& lcdCounters()const{return lcd_;}
  void resetLcdCounters(){lcd_=tpkdirty::Counters{};}
  void setLandscapeHome(bool home){requestedHome_=home;raster_.mode(home);}
  bool landscapeRequested() const{return requestedHome_;}
  bool landscapePresented() const{return presentedHome_;}
  void attachPerf(tpkperf::Monitor& monitor){perf_=&monitor;}
  bool begin(int32_t = GFX_NOT_DEFINED) override {
    if(!pixels_)pixels_=static_cast<uint16_t*>(
      heap_caps_malloc(tpkraster::PIXELS*sizeof(uint16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(!pixels_)return false;
    // Optional exact shadow. Allocation failure is not a boot failure.
    if(!previous_)previous_=static_cast<uint16_t*>(
      heap_caps_malloc(tpkraster::PIXELS*sizeof(uint16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    invalidate();
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
  void flush(bool force=false) override {
    if(!pixels_)return;
    const bool measure=perf_&&perf_->enabled();
    const uint32_t started=measure?micros():0;
    const bool home=requestedHome_;
    const int width=raster_.width(),height=raster_.height();
    const bool cached=dirtyActive();
    const bool full=force||!cached||!previousValid_||home!=presentedHome_;
    const bool previousSwap=M5.Display.getSwapBytes();
    uint32_t sent=0,count=0;
    for(int y=0;y<height;y+=STRIP_ROWS){
      const int rows=(height-y<STRIP_ROWS)?height-y:STRIP_ROWS;
      const uint16_t* current=raster_.row(y);
      uint16_t* shadow=cached?previous_+size_t(y)*width:nullptr;
      auto span=tpkdirty::changed(current,shadow,width,rows,full);
      if(!span.w)continue;
      if(!count){M5.Display.setSwapBytes(true);M5.Display.startWrite();}
      // Keep synchronous internal-RAM strip transfers; no DMA lifetime change.
      tpkdirty::pack(strip_,current,width,rows,span);
      M5.Display.pushImage((home?0:VIEW_X)+span.x,(home?HOME_Y:VIEW_Y)+y,span.w,rows,strip_);
      if(shadow)std::memcpy(shadow,current,size_t(width)*rows*sizeof(uint16_t));
      sent+=uint32_t(span.w)*rows;++count;
    }
    if(count){M5.Display.endWrite();M5.Display.setSwapBytes(previousSwap);}
    presentedHome_=home;previousValid_=cached;
    lcd_.frame(width,height,sent,count);
    if(measure)perf_->flushed(micros()-started);
  }
};
struct StackChanPanel { void setBrightness(uint8_t value){M5.Display.setBrightness(value);} };
