#pragma once
#include "board_hal.h"
namespace tpkside {
enum class Key:uint8_t { None, Feed, Play, Profile, Dex, Settings };
constexpr int DISPLAY_W=320, DISPLAY_H=240, SIDE_W=40;
constexpr int BUTTON_Y=4, BUTTON_H=44, BUTTON_GAP=4;
inline Key keyAt(TouchPoint p) {
  if(!p.pressed || p.x<VIEW_X+VIEW_SIZE || p.x>=DISPLAY_W || p.y<BUTTON_Y || p.y>=DISPLAY_H) return Key::None;
  int slot=(p.y-BUTTON_Y)/(BUTTON_H+BUTTON_GAP);
  if(slot>=5 || (p.y-BUTTON_Y)%(BUTTON_H+BUTTON_GAP)>=BUTTON_H)return Key::None;
  return static_cast<Key>(slot+1);
}
struct Availability {
  bool home, awake, egg, sleeping;
  bool allows(Key k) const {
    if(!home || !awake || k==Key::None)return false;
    if(k==Key::Settings || k==Key::Dex)return true;
    if(egg)return false;
    return k==Key::Profile || !sleeping;
  }
};
struct Route { bool forward, cancel, wake; Key action; };
class TouchRouter {
  enum class Owner { Idle, Center, Side, Blocked };
  Owner owner_=Owner::Idle;
  Key key_=Key::None;
  uint32_t started_=0;
public:
  Route update(TouchPoint p,Availability a,uint32_t now) {
    Route r={false,false,false,Key::None};
    if(!p.pressed) {
      if(owner_==Owner::Center)r.forward=true;
      if(owner_==Owner::Side && now-started_<1000 && a.allows(key_))r.action=key_;
      owner_=Owner::Idle;key_=Key::None;
      return r;
    }
    const bool center=toLogical(p).valid;
    if(owner_==Owner::Idle) {
      if(center){owner_=Owner::Center;r.forward=true;return r;}
      r.wake=p.x>=0 && p.x<DISPLAY_W && p.y>=0 && p.y<DISPLAY_H;
      key_=keyAt(p);started_=now;
      owner_=a.allows(key_)?Owner::Side:Owner::Blocked;
      return r;
    }
    if(owner_==Owner::Center) {
      if(center){r.forward=true;return r;}
      r.cancel=true;owner_=Owner::Blocked;
    }else if(owner_==Owner::Side && (keyAt(p)!=key_ || !a.allows(key_) || now-started_>=1000)) {
      owner_=Owner::Blocked;
    }
    return r;
  }
};
}
