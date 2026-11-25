#include "hal/sidebar_policy.h"
#include "hal/home_dialog_policy.h"
#include "hal/minigame_policy.h"
#include <cassert>
#include <initializer_list>
using namespace tpkside;
int main(){
  Availability a={true,true,false,false};
  TouchRouter t;
  assert(keyAt({280,4,true})==Key::Feed);
  assert(keyAt({319,239,true})==Key::Settings);
  assert(keyAt({319,240,true})==Key::None);
  for(int y=0;y<DISPLAY_H;y++) for(int x=0;x<DISPLAY_W;x++){
    Key expected=Key::None;
    if(x>=280)for(int i=0;i<5;i++)
      if(y>=4+i*48 && y<48+i*48)expected=static_cast<Key>(i+1);
    assert(keyAt({int16_t(x),int16_t(y),true})==expected);
  }
  assert(keyAt({280,48,true})==Key::None);
  assert(keyAt({280,52,true})==Key::Play);
  assert(t.update({300,10,true},a,0).wake);
  assert(t.update({300,10,false},a,80).action==Key::Feed);
  assert(t.update({100,100,true},a,100).forward);
  assert(t.update({300,10,true},a,120).cancel);
  assert(!t.update({100,100,true},a,140).forward);
  assert(t.update({0,0,false},a,160).action==Key::None);
  assert(t.update({300,10,true},a,200).wake);
  assert(t.update({100,100,true},a,220).action==Key::None);
  assert(t.update({300,10,false},a,240).action==Key::None);
  a.awake=false;assert(t.update({300,10,true},a,300).wake);
  a.awake=true;assert(t.update({300,10,false},a,320).action==Key::None);
  a.egg=true;assert(!a.allows(Key::Feed));assert(a.allows(Key::Dex));
  a.egg=false;a.sleeping=true;assert(!a.allows(Key::Play));assert(a.allows(Key::Profile));
  a.sleeping=false;t.update({300,10,true},a,400);a.home=false;
  assert(t.update({300,10,false},a,420).action==Key::None);
  a.home=true;t.update({300,10,true},a,500);
  assert(t.update({300,10,false},a,1500).action==Key::None);
  t.update({300,10,true},a,UINT32_MAX-20);
  assert(t.update({300,10,false},a,30).action==Key::Feed);
  assert(t.update({100,100,true},a,100).forward);
  assert(t.update({100,100,false},a,120).forward);
  for(int y=0;y<DISPLAY_H;y++)for(int x=0;x<DISPLAY_W;x++){
    Key expected=Key::None;
    for(int i=0;i<HOME_BUTTON_COUNT;i++)
      if(x>=HOME_BUTTON_X+i*HOME_BUTTON_STEP&&x<HOME_BUTTON_X+i*HOME_BUTTON_STEP+HOME_BUTTON_W&&
         y>=HOME_BUTTON_Y&&y<HOME_BUTTON_Y+HOME_BUTTON_H)expected=HOME_KEYS[i];
    assert(keyAt({int16_t(x),int16_t(y),true},true)==expected);
  }
  TouchRouter home;
  home.update({0,0,false},a,0,true);
  for(int i=0;i<HOME_BUTTON_COUNT;i++){
    int16_t x=HOME_BUTTON_X+i*HOME_BUTTON_STEP;
    assert(home.update({x,210,true},a,100+i*100,true).wake);
    assert(home.update({x,210,false},a,150+i*100,true).action==HOME_KEYS[i]);
  }
  a.sleeping=true;
  assert(a.allows(Key::Light)&&!a.allows(Key::Bath));
  a.sleeping=false;
  assert(home.update({160,100,true},a,1000,true).forward);
  assert(home.update({160,100,true},a,1020,false).cancel);
  assert(home.update({160,100,false},a,1040,false).action==Key::None);
  home.update({0,0,false},a,1060,true);
  home.update({10,210,true},a,1080,true);
  assert(home.update({10,210,false},a,1100,false).action==Key::None);
  home.update({0,0,false},a,1120,true);
  a.awake=false;assert(home.update({10,210,true},a,1140,true).wake);
  a.awake=true;assert(home.update({10,210,false},a,1160,true).action==Key::None);
  using tpkhome::Page;
  static_assert(tpkhome::landscape(Page::BallGame)&&tpkhome::landscape(Page::Training),"landscape games");
  float bx=0,by=140,vx=-4,vy=0;
  assert(!tpkmini::walls(bx,by,vx,vy)&&bx==tpkmini::LEFT&&vx>0);
  bx=500;vx=4;
  assert(!tpkmini::walls(bx,by,vx,vy)&&bx==tpkmini::RIGHT&&vx<0);
  bx=200;by=0;vy=-4;
  assert(!tpkmini::walls(bx,by,vx,vy)&&by==tpkmini::CEILING&&vy>0);
  by=tpkmini::FLOOR+1;assert(tpkmini::walls(bx,by,vx,vy));
  assert(tpkmini::hitBall(233,150,233,150));
  assert(!tpkmini::hitBall(233,150,0,150));
  assert(!tpkmini::hitBall(390,88,390,40));
  assert(tpkmini::nextScore(254)==255&&tpkmini::nextScore(255)==255);
  bool exitSeen=false,bagSeen=false,backSeen=false;
  for(int y=HOME_Y;y<HOME_BOTTOM;y++)for(int x=0;x<HOME_W;x++){
    auto p=homeToLogical({int16_t(x),int16_t(y),true});
    bool exit=tpkmini::EXIT.contains(p.x,p.y),bag=tpkmini::BAG_HIT.contains(p.x,p.y);
    assert(!(exit&&bag));exitSeen|=exit;bagSeen|=bag;
    backSeen|=tpkmini::RESULT_BACK.contains(p.x,p.y);
  }
  assert(exitSeen&&bagSeen&&backSeen);
  TouchRouter game;
  game.update({0,0,false},a,0,true,uint8_t(Page::BallGame));
  assert(game.update({160,110,true},a,10,true,uint8_t(Page::BallGame)).forward);
  assert(game.update({160,110,true},a,20,true,uint8_t(Page::BallResult)).cancel);
  assert(!game.update({160,110,false},a,30,true,uint8_t(Page::BallResult)).forward);
  bool gallerySeen[16]={},keyboardSeen[30]={},clockSeen[9]={};
  for(int y=HOME_Y;y<HOME_BOTTOM;y++)for(int x=0;x<HOME_W;x++){
    const auto p=homeToLogical({int16_t(x),int16_t(y),true});
    int g=tpkhome::galleryHit(p.x,p.y),k=tpkhome::keyboardHit(p.x,p.y),c=tpkhome::clockHit(p.x,p.y);
    assert(g>=-1&&g<16&&k>=-1&&k<30&&c>=-1&&c<9);
    if(g>=0)gallerySeen[g]=true;
    if(k>=0)keyboardSeen[k]=true;
    if(c>=0)clockSeen[c]=true;
    if(tpkhome::NAV_BACK.contains(p.x,p.y)||tpkhome::NAV_PREV.contains(p.x,p.y)||tpkhome::NAV_NEXT.contains(p.x,p.y))assert(g<0);
  }
  for(bool seen:gallerySeen)assert(seen);
  for(bool seen:keyboardSeen)assert(seen);
  for(bool seen:clockSeen)assert(seen);
  assert(tpkhome::keyboardHit(82,70)==-1);
  assert(tpkhome::galleryHit(119,43)==-1);
  TouchRouter paging;
  paging.update({0,0,false},a,0,true,32);
  assert(paging.update({160,100,true},a,10,true,32).forward);
  assert(paging.update({160,100,true},a,20,true,33).cancel);
  assert(!paging.update({160,100,false},a,30,true,33).forward);
  for(Page page:{Page::Starter,Page::Feed,Page::Release,Page::EvolveChoice,Page::FarewellChoice}){
    bool seen[4]={};
    const int count=page==Page::Starter?3:page==Page::Feed?4:2;
    for(int y=HOME_Y;y<HOME_BOTTOM;y++)for(int x=0;x<HOME_W;x++){
      auto p=homeToLogical({int16_t(x),int16_t(y),true});
      const int k=tpkhome::hit(page,p.x,p.y);
      assert(k>=-1&&k<count);
      if(k>=0)seen[k]=true;
    }
    for(int i=0;i<count;i++)assert(seen[i]);
  }
  assert(tpkhome::hit(Page::Feed,48,224)==0);
  assert(tpkhome::hit(Page::Feed,136,224)==-1);
  assert(tpkhome::hit(Page::Release,54,220)==0);
  assert(tpkhome::hit(Page::Release,228,220)==-1);
  assert(tpkhome::hit(Page::EvolveChoice,0,0)==-1);
  TouchRouter modal;
  modal.update({0,0,false},a,0,true,uint8_t(Page::Pet));
  assert(modal.update({160,100,true},a,10,true,uint8_t(Page::Pet)).forward);
  assert(modal.update({160,100,true},a,20,true,uint8_t(Page::Release)).cancel);
  assert(!modal.update({160,100,false},a,30,true,uint8_t(Page::Release)).forward);
  assert(modal.update({160,100,true},a,40,true,uint8_t(Page::Release)).forward);
  modal.block({160,100,true});
  assert(!modal.update({160,100,true},a,50,true,uint8_t(Page::Pet)).forward);
  assert(!modal.update({160,100,false},a,60,true,uint8_t(Page::Pet)).forward);
}
