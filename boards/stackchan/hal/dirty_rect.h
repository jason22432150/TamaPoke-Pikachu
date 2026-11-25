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
  while(left<right){
    int w=right-left<TILE_W?right-left:TILE_W;
    if(!tileEqual(current,previous,width,rows,left,w))break;
    left+=w;
  }
  while(right>left){
    int x=right-TILE_W;if(x<left)x=left;
    if(!tileEqual(current,previous,width,rows,x,right-x))break;
    right=x;
  }
  return {left,right-left};
}
inline void pack(uint16_t* out,const uint16_t* src,int width,int rows,Span s){
  for(int y=0;y<rows;y++)
    std::memcpy(out+size_t(y)*s.w,src+size_t(y)*width+s.x,size_t(s.w)*sizeof(uint16_t));
}
struct Counters{
  uint64_t frames=0,unchanged=0,rects=0,pixels=0,fullPixels=0;
  void frame(int width,int height,uint32_t sent,uint32_t count){
    ++frames;fullPixels+=uint64_t(width)*height;pixels+=sent;rects+=count;
    if(!count)++unchanged;
  }
};
}
