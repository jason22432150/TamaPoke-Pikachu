#pragma once
#include "board_hal.h"
namespace tpkhome {
enum class Page:uint8_t { Compat, Starter, Egg, Pet, Feed, Release, EvolveChoice,
  FarewellChoice, Ceremony, Bath, EvolvePrompt, FarewellPrompt, RunawayPrompt, GalleryGrid, GalleryDetail,
  CardProfile, CardStats, CardMedals, CardProgress, Clock, Keyboard };
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
// B4 uses the same logical-space geometry for drawing and hit-testing.
constexpr Rect galleryCell(int i){return {13+(i%4)*111,43+(i/4)*53,106,49};}
constexpr Rect NAV_PREV={14,265,105,43}, NAV_NEXT={347,265,105,43},
  NAV_BACK={142,265,182,43};
constexpr Rect CARD_RENAME={16,211,202,43}, CARD_TRAIN={100,211,266,43};
constexpr Rect KEY_CANCEL={338,8,114,40};
constexpr Rect keyboard(int i){return {12+(i%6)*74,70+(i/6)*47,70,43};}
constexpr Rect clockControl(int i){
  return i<4?Rect{22+i*108,92,100,55}:
    i<7?Rect{16+(i-4)*146,165,140,49}:
    i==7?Rect{16,238,211,56}:Rect{239,238,211,56};
}
inline int galleryHit(int x,int y){
  for(int i=0;i<16;i++)if(galleryCell(i).contains(x,y))return i;
  return -1;
}
inline int keyboardHit(int x,int y){
  for(int i=0;i<30;i++)if(keyboard(i).contains(x,y))return i;
  return -1;
}
inline int clockHit(int x,int y){
  for(int i=0;i<9;i++)if(clockControl(i).contains(x,y))return i;
  return -1;
}
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
static_assert(visible(galleryCell(0))&&visible(galleryCell(15))&&
  visible(NAV_PREV)&&visible(NAV_NEXT)&&visible(NAV_BACK)&&visible(CARD_RENAME)&&
  visible(CARD_TRAIN)&&visible(KEY_CANCEL)&&visible(keyboard(0))&&visible(keyboard(29))&&
  visible(clockControl(0))&&visible(clockControl(8)),"B4 controls fit");
static_assert(visible(starter(0))&&visible(starter(2))&&visible(feed(0))&&visible(feed(3))&&
  visible(choice(0))&&visible(choice(1))&&visible(release(0))&&visible(release(1))&&
  visible(FEED_PANEL)&&visible(CHOICE_PANEL)&&visible(RELEASE_PANEL),"dialog fits landscape viewport");
}
