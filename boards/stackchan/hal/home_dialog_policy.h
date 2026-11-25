#pragma once
#include "board_hal.h"
namespace tpkhome {
enum class Page:uint8_t { Compat, Starter, Egg, Pet, Feed, Release, EvolveChoice,
  FarewellChoice, Ceremony, Bath, EvolvePrompt, FarewellPrompt, RunawayPrompt };
constexpr bool landscape(Page p){return p!=Page::Compat;}
constexpr bool modal(Page p){return p==Page::Feed||p==Page::Release||
  p==Page::EvolveChoice||p==Page::FarewellChoice;}
struct Rect {
  int x,y,w,h;
  constexpr bool contains(int px,int py)const{
    return px>=x&&px<x+w&&py>=y&&py<y+h;
  }
};
constexpr Rect starter(int i){return {18+146*i,98,138,186};}
constexpr Rect feed(int i){return {48+94*i,224,88,68};}
constexpr Rect choice(int i){return {54,168+62*i,358,54};}
constexpr Rect release(int i){return {54+184*i,220,174,64};}
constexpr Rect FEED_PANEL={38,207,390,97};
constexpr Rect CHOICE_PANEL={34,112,398,186};
constexpr Rect RELEASE_PANEL={34,145,398,153};
inline int hit(Page page,int x,int y){
  const int count=page==Page::Starter?3:page==Page::Feed?4:
    (page==Page::Release||page==Page::EvolveChoice||page==Page::FarewellChoice)?2:0;
  for(int i=0;i<count;i++){
    Rect b=page==Page::Starter?starter(i):page==Page::Feed?feed(i):
      page==Page::Release?release(i):choice(i);
    if(b.contains(x,y))return i;
  }
  return -1;
}
constexpr bool visible(Rect r){
  return r.x>=0&&r.y>=0&&r.x+r.w<=GAME_SIZE&&
    r.y+r.h-1<=logicalAxis(HOME_H-1);
}
static_assert(visible(starter(0))&&visible(starter(2))&&visible(feed(0))&&visible(feed(3))&&
  visible(choice(0))&&visible(choice(1))&&visible(release(0))&&visible(release(1))&&
  visible(FEED_PANEL)&&visible(CHOICE_PANEL)&&visible(RELEASE_PANEL),"dialog fits landscape viewport");
}
