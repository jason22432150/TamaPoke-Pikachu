#pragma once
#include <M5Unified.h>
#include "sidebar_policy.h"
namespace tpkside {
struct State {
  Availability available;
  int battery;
  bool charging,sd;
  uint16_t level;
  uint8_t food,joy,energy,hygiene;
};
class Sidebar {
  uint32_t lastDraw_=0;
  bool initialized_=false,previousLandscape_=false;
  State previous_{};
  static bool equal(const State& a,const State& b){
    return a.available.home==b.available.home && a.available.awake==b.available.awake &&
      a.available.egg==b.available.egg && a.available.sleeping==b.available.sleeping &&
      a.battery==b.battery && a.charging==b.charging && a.sd==b.sd &&
      a.level==b.level && a.food==b.food && a.joy==b.joy &&
      a.energy==b.energy && a.hygiene==b.hygiene;
  }
  static constexpr uint16_t BG=0x18E4, FG=0xFFFF, MUTED=0x8410, ACCENT=0x65D4;
  void label(const char* s,int x,int y,uint16_t color=FG) {
    auto& d=M5.Display;
    d.setTextColor(color,BG);
    d.drawString(s,x,y);
  }
  void meter(const char* name,uint8_t value,int y){
    auto& d=M5.Display;
    label(name,3,y);
    d.fillRect(3,y+11,34,5,MUTED);
    int n=value>100?100:value;
    d.fillRect(3,y+11,34*n/100,5,n<25?0xF986:ACCENT);
  }
  void landscapeChrome(const State& s){
    auto& d=M5.Display;
    d.fillRect(0,0,DISPLAY_W,HOME_Y,BG);
    d.fillRect(0,HOME_BOTTOM,DISPLAY_W,DISPLAY_H-HOME_BOTTOM,BG);
    char buf[24];
    if(s.battery>=0&&s.battery<=100)snprintf(buf,sizeof(buf),"BAT %d%%",s.battery);
    else snprintf(buf,sizeof(buf),"BAT --");
    label(buf,4,3);
    label(s.charging?"CHG":"",62,3,ACCENT);
    label(s.sd?"SD OK":"NO SD",99,3,s.sd?ACCENT:MUTED);
    snprintf(buf,sizeof(buf),"Lv.%u",unsigned(s.level));label(buf,155,3);
    const char* names[]={"FOOD","JOY","ENE","HYG"};
    const uint8_t values[]={s.food,s.joy,s.energy,s.hygiene};
    for(int i=0;i<4;i++){
      const int x=i*80+4,n=values[i]>100?100:values[i];
      label(names[i],x,16);
      d.fillRect(x,27,72,5,MUTED);
      if(n)d.fillRect(x,27,72*n/100,5,n<25?0xF986:ACCENT);
    }
    const char* labels[]={"FEED","PLAY","LIGHT","BATH","INFO","DEX","SET"};
    for(int i=0;i<HOME_BUTTON_COUNT;i++){
      int x=HOME_BUTTON_X+i*HOME_BUTTON_STEP;
      bool allowed=s.available.allows(HOME_KEYS[i]);
      d.drawRoundRect(x,HOME_BUTTON_Y,HOME_BUTTON_W,HOME_BUTTON_H,5,allowed?ACCENT:MUTED);
      label(labels[i],x+(HOME_BUTTON_W-int(strlen(labels[i]))*6)/2,HOME_BUTTON_Y+16,allowed?FG:MUTED);
    }
  }
public:
  void update(const State& s,uint32_t now,bool landscape=false) {
    if(!s.available.awake && !landscape) {initialized_=false;return;}
    if(landscape!=previousLandscape_)initialized_=false;
    if(initialized_ && (equal(s,previous_) || (now-lastDraw_<200 && s.available.home==previous_.available.home &&
       s.available.egg==previous_.available.egg && s.available.sleeping==previous_.available.sleeping))) return;
    auto& d=M5.Display;
    d.startWrite();
    d.setFont(&m5gfx::fonts::Font0);d.setTextSize(1);d.setTextDatum(uint8_t(0));
    if(landscape){
      landscapeChrome(s);
      d.endWrite();previous_=s;initialized_=true;previousLandscape_=true;lastDraw_=now;
      return;
    }
    d.fillRect(0,0,SIDE_W,DISPLAY_H,BG);
    d.fillRect(VIEW_X+VIEW_SIZE,0,SIDE_W,DISPLAY_H,BG);
    char buf[12];
    label("BAT",3,5);
    if(s.battery>=0 && s.battery<=100)snprintf(buf,sizeof(buf),"%d%%",s.battery);
    else snprintf(buf,sizeof(buf),"--");
    label(buf,3,17);
    label(s.charging?"CHG":"",3,29,ACCENT);
    label(s.sd?"SD OK":"NO SD",3,43,s.sd?ACCENT:MUTED);
    if(!s.available.egg){
      snprintf(buf,sizeof(buf),"L%u",unsigned(s.level));label(buf,3,60);
      meter("FOOD",s.food,82);meter("JOY",s.joy,120);
      meter("ENE",s.energy,158);meter("HYG",s.hygiene,196);
    }else label("EGG",3,60);
    const char* labels[]={"FEED","PLAY","INFO","DEX","SET"};
    for(int i=0;i<5;i++){
      int y=BUTTON_Y+i*(BUTTON_H+BUTTON_GAP);
      bool allowed=s.available.allows(static_cast<Key>(i+1));
      d.drawRoundRect(281,y,38,BUTTON_H,5,allowed?ACCENT:MUTED);
      label(labels[i],300-int(strlen(labels[i]))*3,y+18,allowed?FG:MUTED);
    }
    d.endWrite();previous_=s;initialized_=true;previousLandscape_=false;lastDraw_=now;
  }
};
}
