#include "hal/board_hal.h"
#include <cassert>
#include <cstdlib>
static uint16_t frame[GAME_SIZE*GAME_SIZE];
static uint16_t row[VIEW_SIZE],xMap[VIEW_SIZE];
int main(){
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
}
