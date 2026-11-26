#include "hal/board_hal.h"
#include "hal/native_raster.h"
#include "hal/dirty_rect.h"
#include <cassert>
#include <cstdlib>
static uint16_t frame[GAME_SIZE*GAME_SIZE];
static uint16_t row[VIEW_SIZE],xMap[VIEW_SIZE];
static uint16_t native[tpkraster::PIXELS+2];
static void referenceRect(int x,int y,int w,int h,uint16_t color){
  if(w<0){x+=w+1;w=-w;}
  if(h<0){y+=h+1;h=-h;}
  for(int py=std::max(0,y);py<std::min(GAME_SIZE,y+h);py++)
    for(int px=std::max(0,x);px<std::min(GAME_SIZE,x+w);px++)
      frame[py*GAME_SIZE+px]=color;
}
static void checkNative(bool home){
  tpkraster::Raster raster;
  native[0]=0xA55A;native[tpkraster::PIXELS+1]=0x5AA5;
  raster.begin(native+1);raster.mode(home);
  referenceRect(0,0,GAME_SIZE,GAME_SIZE,0x1234);
  raster.rect(0,0,GAME_SIZE,GAME_SIZE,0x1234);
  // Exercise thin glyph/pixel runs, negative and clipped dimensions, edge
  // extension, and overwrite order. Deterministic without a random library.
  uint32_t state=123456789;
  auto next=[&](){state=state*1664525u+1013904223u;return state;};
  for(int i=0;i<2000;i++){
    const int x=int(next()%600)-70,y=int(next()%600)-70;
    const int w=int(next()%121)-60,h=int(next()%121)-60;
    const uint16_t color=uint16_t(next());
    referenceRect(x,y,w,h,color);raster.rect(x,y,w,h,color);
    referenceRect(x,y,1,1,color^0xFFFF);raster.rect(x,y,1,1,color^0xFFFF);
  }
  for(int y=0;y<raster.height();y++)
    for(int x=0;x<raster.width();x++){
      int lx=home?homeLogicalX(x):logicalAxis(x),ly=logicalAxis(y);
      assert(raster.row(y)[x]==frame[ly*GAME_SIZE+lx]);
    }
  assert(native[0]==0xA55A&&native[tpkraster::PIXELS+1]==0x5AA5);
}
static void checkDirty(){
  uint16_t old[37*8]={},cur[37*8]={},packed[37*8]={};
  auto span=tpkdirty::changed(cur,old,37,8,false);assert(span.w==0);
  span=tpkdirty::changed(cur,old,37,8,true);assert(span.x==0&&span.w==37);
  span=tpkdirty::changed(cur,nullptr,37,8,false);assert(span.w==37);
  // Odd width and final partial strip; every changed pixel must be covered.
  uint32_t state=42;
  for(int n=0;n<300;n++){
    int rows=1+n%8;
    std::memcpy(cur,old,sizeof(cur));
    for(int j=0;j<n%11;j++){
      state=state*1664525u+1013904223u;
      cur[state%(37*rows)]^=uint16_t(state|1u);
    }
    span=tpkdirty::changed(cur,old,37,rows,false);
    assert(span.x>=0&&span.w>=0&&span.x+span.w<=37);
    if(span.w)tpkdirty::pack(packed,cur,37,rows,span);
    uint16_t updated[37*8];std::memcpy(updated,old,sizeof(updated));
    tpkdirty::commitPacked(updated,packed,37,rows,span);
    for(int y=0;y<rows;y++)for(int x=0;x<37;x++){
      if(cur[y*37+x]!=old[y*37+x])assert(x>=span.x&&x<span.x+span.w);
      if(x>=span.x&&x<span.x+span.w)old[y*37+x]=packed[y*span.w+x-span.x];
      assert(old[y*37+x]==cur[y*37+x]);
      assert(updated[y*37+x]==cur[y*37+x]);
    }
  }
  tpkdirty::Counters c;c.frame(320,160,0,0);c.frame(320,160,128,1);
  assert(c.frames==2&&c.unchanged==1&&c.rects==1&&c.pixels==128&&c.fullPixels==102400);
}
// Compare against the original B10 tile policy, including odd widths and
// partial final strips. Guard packed and shadow buffers against overrun.
static tpkdirty::Span legacyChanged(const uint16_t* cur,const uint16_t* old,int width,int rows){
  if(!std::memcmp(cur,old,size_t(width)*rows*sizeof(uint16_t)))return {0,0};
  int left=0,right=width;
  while(left<right){int w=std::min(right-left,tpkdirty::TILE_W);if(!tpkdirty::tileEqual(cur,old,width,rows,left,w))break;left+=w;}
  while(right>left){int x=std::max(left,right-tpkdirty::TILE_W);if(!tpkdirty::tileEqual(cur,old,width,rows,x,right-x))break;right=x;}
  return {left,right-left};
}
static void checkDirtyWide(){
  constexpr int CAP=320*8;
  uint16_t cur[CAP]={},old[CAP+2]={},packed[CAP+2]={};
  const int widths[]={1,15,16,17,37,63,64,65,160,319,320};
  uint32_t rng=98765;
  for(int width:widths)for(int rows=1;rows<=8;rows++){
    const int n=width*rows;old[0]=packed[0]=0xA55A;old[n+1]=packed[n+1]=0x5AA5;
    std::memset(old+1,0,size_t(n)*sizeof(uint16_t));
    for(int trial=0;trial<100;trial++){
      std::memcpy(cur,old+1,size_t(n)*sizeof(uint16_t));
      for(int k=0;k<trial%9;k++){rng=rng*1664525u+1013904223u;cur[(rng>>8)%n]^=uint16_t(rng|1u);}
      auto ref=legacyChanged(cur,old+1,width,rows);
      const bool full=trial%17==0;
      auto got=tpkdirty::changed(cur,old+1,width,rows,full);
      assert(got.x==(full?0:ref.x)&&got.w==(full?width:ref.w));
      tpkdirty::pack(packed+1,cur,width,rows,got);
      tpkdirty::commitPacked(old+1,packed+1,width,rows,got);
      assert(!std::memcmp(cur,old+1,size_t(n)*sizeof(uint16_t)));
      assert(old[0]==0xA55A&&old[n+1]==0x5AA5&&packed[0]==0xA55A&&packed[n+1]==0x5AA5);
    }
  }
  tpkdirty::commitPacked(nullptr,packed,320,8,{0,320});
}
int main(){
  checkDirty();checkDirtyWide();
  for(int x=0;x<VIEW_SIZE;x++) xMap[x]=logicalAxis(x);
  for(int y=0;y<GAME_SIZE;y++) for(int x=0;x<GAME_SIZE;x++)
    frame[y*GAME_SIZE+x]=uint16_t((x*97u+y*311u)^0xF800u);
  for(int y=0;y<VIEW_SIZE;y++) {
    scaleGameRow(frame,row,y,xMap);
    for(int x=0;x<VIEW_SIZE;x++) {
      auto p=toLogical({int16_t(x+VIEW_X),int16_t(y+VIEW_Y),true});
      assert(row[x]==frame[p.y*GAME_SIZE+p.x]);
    }
  }
  for(int y=0;y<240;y++) for(int x=40;x<280;x++){
    auto q=toLogical({int16_t(x),int16_t(y),true});
    assert(q.valid && q.x>=0 && q.x<466 && q.y>=0 && q.y<466);
    auto p=toPhysical(q); assert(p.pressed && p.x==x && p.y==y);
  }
  auto a=toLogical({40,0,true}); assert(a.x==0 && a.y==0);
  auto b=toLogical({279,239,true}); assert(b.x==465 && b.y==465);
  assert(!toLogical({39,0,true}).valid);
  assert(!toLogical({280,0,true}).valid);
  assert(!toLogical({40,-1,true}).valid);
  assert(!toLogical({40,240,true}).valid);
  assert(!toLogical({40,0,false}).valid);
  assert(!toPhysical({466,0,true}).pressed);
  assert(!toPhysical({0,-1,true}).pressed);
  assert(!toPhysical({0,0,false}).pressed);
  uint16_t homeRow[HOME_W],homeMap[HOME_W];
  for(int x=0;x<HOME_W;x++)homeMap[x]=homeLogicalX(x);
  for(int y=0;y<HOME_H;y++){
    scaleHomeRow(frame,homeRow,y,homeMap);
    for(int x=0;x<HOME_W;x++){
      auto q=homeToLogical({int16_t(x),int16_t(HOME_Y+y),true});
      assert(q.valid && homeRow[x]==frame[q.y*GAME_SIZE+q.x]);
      if(x>=HOME_X&&x<HOME_X+VIEW_SIZE)assert(q.x==logicalAxis(x-HOME_X));
    }
  }
  assert(!homeToLogical({0,HOME_Y-1,true}).valid);
  assert(!homeToLogical({0,HOME_BOTTOM,true}).valid);
  assert(!homeToLogical({-1,HOME_Y,true}).valid);
  assert(!homeToLogical({HOME_W,HOME_Y,true}).valid);
  assert(homeToLogical({HOME_W-1,HOME_BOTTOM-1,true}).y<312);
  checkNative(false);checkNative(true);checkNative(false);
}
