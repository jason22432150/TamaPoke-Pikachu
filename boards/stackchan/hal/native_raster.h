#pragma once
#include "board_hal.h"
#include <algorithm>
#include <stddef.h>

namespace tpkraster {
// Raster storage uses physical viewport pixels; the public drawing API keeps
// 466x466 logical coordinates. Each physical pixel receives precisely the
// same nearest-neighbor sample as the old framebuffer + scaleGameRow path.
constexpr size_t COMPAT_PIXELS=size_t(VIEW_SIZE)*VIEW_SIZE;
constexpr size_t HOME_PIXELS=size_t(HOME_W)*HOME_H;
constexpr size_t PIXELS=COMPAT_PIXELS>HOME_PIXELS?COMPAT_PIXELS:HOME_PIXELS;
static_assert(PIXELS==57600,"physical raster capacity");

struct Axis {
  uint16_t boundary[GAME_SIZE+1]{};
  void init(int count,bool extended){
    int p=0;
    for(int logical=0;logical<=GAME_SIZE;logical++){
      while(p<count && (extended?homeLogicalX(p):logicalAxis(p))<logical)++p;
      boundary[logical]=uint16_t(p);
    }
  }
};

class Raster {
  Axis square_,wide_;
  bool home_=false;
  uint16_t* pixels_=nullptr;
public:
  void begin(uint16_t* pixels){
    pixels_=pixels;square_.init(VIEW_SIZE,false);wide_.init(HOME_W,true);
  }
  void mode(bool home){home_=home;}
  int width()const{return home_?HOME_W:VIEW_SIZE;}
  int height()const{return home_?HOME_H:VIEW_SIZE;}
  const uint16_t* row(int y)const{return pixels_+size_t(y)*width();}
  // Match Arduino_Canvas's negative-size and clipped-line semantics.
  void rect(int32_t x,int32_t y,int32_t w,int32_t h,uint16_t color){
    if(!pixels_||!w||!h)return;
    if(w<0){x+=w+1;w=-w;}
    if(h<0){y+=h+1;h=-h;}
    const int32_t x0=std::max<int32_t>(0,x),y0=std::max<int32_t>(0,y);
    const int32_t x1=std::min<int32_t>(GAME_SIZE,x+w),y1=std::min<int32_t>(GAME_SIZE,y+h);
    if(x0>=x1||y0>=y1)return;
    const auto& a=home_?wide_:square_;
    const int left=a.boundary[x0],right=a.boundary[x1];
    const int top=std::min<int>(height(),square_.boundary[y0]);
    const int bottom=std::min<int>(height(),square_.boundary[y1]);
    if(left>=right||top>=bottom)return;
    for(int py=top;py<bottom;py++)
      std::fill_n(pixels_+size_t(py)*width()+left,right-left,color);
  }
};
}
