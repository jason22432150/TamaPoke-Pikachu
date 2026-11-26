#pragma once
#include <stdint.h>
#include <stddef.h>
#include <cstring>
namespace tpkdirty {
constexpr int TILE_W=16, STRIP_ROWS=8;
struct Span {int x,w;};
inline bool tileEqual(const uint16_t* current,const uint16_t* previous,int width,int rows,int x,int w){
  for(int y=0;y<rows;y++)
    if(std::memcmp(current+size_t(y)*width+x,previous+size_t(y)*width+x,size_t(w)*sizeof(uint16_t)))return false;
  return true;
}
// One bounding rectangle per strip, preserving the old transfer limit.
// Exact comparison (not hashes): no false negatives from collisions.
inline Span changed(const uint16_t* current,const uint16_t* previous,int width,int rows,bool full){
  if(full||!previous)return {0,width};
  if(!std::memcmp(current,previous,size_t(width)*rows*sizeof(uint16_t)))return {0,0};
  int left=0,right=width;
  // Skip four equal tiles at a time. On a mismatch fall back to the
  // original tile walk, preserving exactly the same bounding span.
  constexpr int GROUP=4*TILE_W;
  while(right-left>=GROUP&&tileEqual(current,previous,width,rows,left,GROUP))left+=GROUP;
  while(left<right){
    int w=right-left<TILE_W?right-left:TILE_W;
    if(!tileEqual(current,previous,width,rows,left,w))break;
    left+=w;
  }
  while(right-left>=GROUP&&tileEqual(current,previous,width,rows,right-GROUP,GROUP))right-=GROUP;
  while(right>left){
    int x=right-TILE_W;if(x<left)x=left;
    if(!tileEqual(current,previous,width,rows,x,right-x))break;
    right=x;
  }
  return {left,right-left};
}
inline void pack(uint16_t* out,const uint16_t* src,int width,int rows,Span s){
  if(!s.w)return;
  if(s.x==0&&s.w==width){std::memcpy(out,src,size_t(width)*rows*sizeof(uint16_t));return;}
  for(int y=0;y<rows;y++)
    std::memcpy(out+size_t(y)*s.w,src+size_t(y)*width+s.x,size_t(s.w)*sizeof(uint16_t));
}
// Commit only the rectangle actually transmitted, using the packed internal
// RAM staging buffer instead of rereading the entire PSRAM raster strip.
// Pixels outside the span were proven equal by changed(). Full/invalid
// frames naturally commit the entire strip.
inline void commitPacked(uint16_t* shadow,const uint16_t* packed,int width,int rows,Span s){
  if(!shadow||!s.w)return;
  if(s.x==0&&s.w==width){std::memcpy(shadow,packed,size_t(width)*rows*sizeof(uint16_t));return;}
  for(int y=0;y<rows;y++)
    std::memcpy(shadow+size_t(y)*width+s.x,packed+size_t(y)*s.w,size_t(s.w)*sizeof(uint16_t));
}
struct Counters{
  uint64_t frames=0,unchanged=0,rects=0,pixels=0,fullPixels=0;
  void frame(int width,int height,uint32_t sent,uint32_t count){
    ++frames;fullPixels+=uint64_t(width)*height;pixels+=sent;rects+=count;
    if(!count)++unchanged;
  }
};
}
