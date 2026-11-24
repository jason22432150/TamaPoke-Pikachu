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
  bool initialized_=false;
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
public:
  void update(const State& s,uint32_t now) {
    if(!s.available.awake) {initialized_=false;return;}
    if(initialized_ && (equal(s,previous_) || (now-lastDraw_<200 && s.available.home==previous_.available.home &&
       s.available.egg==previous_.available.egg && s.available.sleeping==previous_.available.sleeping))) return;
    auto& d=M5.Display;
    d.startWrite();
    d.fillRect(0,0,SIDE_W,DISPLAY_H,BG);
    d.fillRect(VIEW_X+VIEW_SIZE,0,SIDE_W,DISPLAY_H,BG);
    d.setFont(&m5gfx::fonts::Font0);d.setTextSize(1);d.setTextDatum(uint8_t(0));
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
    d.endWrite();previous_=s;initialized_=true;lastDraw_=now;
  }
};
}
