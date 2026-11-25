#pragma once
#include "board_hal.h"
namespace tpkside {
enum class Key:uint8_t { None, Feed, Play, Profile, Dex, Settings, Light, Bath };
constexpr int DISPLAY_W=320, DISPLAY_H=240, SIDE_W=40;
constexpr int BUTTON_Y=4, BUTTON_H=44, BUTTON_GAP=4;
constexpr int HOME_BUTTON_X=2, HOME_BUTTON_W=42, HOME_BUTTON_STEP=45;
constexpr int HOME_BUTTON_Y=198, HOME_BUTTON_H=40, HOME_BUTTON_COUNT=7;
constexpr Key HOME_KEYS[HOME_BUTTON_COUNT]={Key::Feed,Key::Play,Key::Light,Key::Bath,Key::Profile,Key::Dex,Key::Settings};
inline Key keyAt(TouchPoint p,bool landscape=false) {
  if(landscape){
    if(!p.pressed||p.x<HOME_BUTTON_X||p.x>=DISPLAY_W||p.y<HOME_BUTTON_Y||p.y>=HOME_BUTTON_Y+HOME_BUTTON_H)return Key::None;
    int dx=p.x-HOME_BUTTON_X,slot=dx/HOME_BUTTON_STEP;
    return slot<HOME_BUTTON_COUNT&&dx%HOME_BUTTON_STEP<HOME_BUTTON_W?HOME_KEYS[slot]:Key::None;
  }
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
    return k==Key::Profile || k==Key::Light || !sleeping;
  }
};
struct Route { bool forward, cancel, wake; Key action; };
class TouchRouter {
  enum class Owner { Idle, Center, Side, Blocked };
  Owner owner_=Owner::Idle;
  Key key_=Key::None;
  uint32_t started_=0;
  bool landscape_=false;
  uint8_t page_=0;
public:
  // A screen/state transition can occur before its new pixels are presented.
  void block(TouchPoint p){owner_=p.pressed?Owner::Blocked:Owner::Idle;key_=Key::None;}
  Route update(TouchPoint p,Availability a,uint32_t now,bool landscape=false,uint8_t page=0) {
    Route r={false,false,false,Key::None};
    // Never complete a gesture against a different displayed geometry.
    if(landscape!=landscape_ || page!=page_){
      landscape_=landscape;page_=page;
      r.cancel=owner_==Owner::Center;
      if(owner_!=Owner::Idle || p.pressed){
        owner_=p.pressed?Owner::Blocked:Owner::Idle;key_=Key::None;
        return r;
      }
    }
    if(!p.pressed) {
      if(owner_==Owner::Center)r.forward=true;
      if(owner_==Owner::Side && now-started_<1000 && a.allows(key_))r.action=key_;
      owner_=Owner::Idle;key_=Key::None;
      return r;
    }
    const bool center=(landscape?homeToLogical(p):toLogical(p)).valid;
    if(owner_==Owner::Idle) {
      if(center){owner_=Owner::Center;r.forward=true;return r;}
      r.wake=p.x>=0 && p.x<DISPLAY_W && p.y>=0 && p.y<DISPLAY_H;
      key_=keyAt(p,landscape);started_=now;
      owner_=a.allows(key_)?Owner::Side:Owner::Blocked;
      return r;
    }
    if(owner_==Owner::Center) {
      if(center){r.forward=true;return r;}
      r.cancel=true;owner_=Owner::Blocked;
    }else if(owner_==Owner::Side && (keyAt(p,landscape)!=key_ || !a.allows(key_) || now-started_>=1000)) {
      owner_=Owner::Blocked;
    }
    return r;
  }
};
}
