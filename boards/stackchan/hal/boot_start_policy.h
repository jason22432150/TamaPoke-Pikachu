#pragma once
#include "board_hal.h"
namespace tpkboot {
constexpr uint32_t AUTO_MS=3000;
struct Rect {
  int x,y,w,h;
  constexpr bool contains(TouchPoint p)const{
    return p.x>=x&&p.x<x+w&&p.y>=y&&p.y<y+h;
  }
};
constexpr Rect START={20,66,280,52}, DIAG={20,130,280,52};
enum class Choice:uint8_t { None, Start, Diagnostic };
enum class Action:uint8_t { Wait, StartAuto, StartTouch, StartSerial };
enum class Command:uint8_t { None, Start, Diagnostic, Calibration };
inline Choice hit(TouchPoint p){
  return START.contains(p)?Choice::Start:DIAG.contains(p)?Choice::Diagnostic:Choice::None;
}
class Gate {
  uint32_t started_;
  bool automatic_=true,sampled_=false,down_=false;
  Choice pressed_=Choice::None;
public:
  explicit Gate(uint32_t now):started_(now){}
  bool automatic()const{return automatic_;}
  uint32_t secondsLeft(uint32_t now)const{
    const uint32_t elapsed=now-started_;
    return automatic_&&elapsed<AUTO_MS?(AUTO_MS-elapsed+999)/1000:0;
  }
  Action update(uint32_t now,TouchPoint p,Command cmd=Command::None){
    // Any contact pauses auto-start before checking the deadline. A finger
    // held when the menu first appears never counts as a new button press.
    if(p.pressed){
      automatic_=false;
      if(!down_)pressed_=sampled_?hit(p):Choice::None;
      else if(hit(p)!=pressed_)pressed_=Choice::None;
      down_=true;
    }
    Choice released=Choice::None;
    if(!p.pressed&&down_){released=pressed_;pressed_=Choice::None;down_=false;}
    sampled_=true;
    // Explicit diagnostic/calibration requests win over a concurrent release.
    if(cmd==Command::Diagnostic||cmd==Command::Calibration){
      automatic_=false;pressed_=Choice::None;return Action::Wait;
    }
    if(cmd==Command::Start)return Action::StartSerial;
    if(released==Choice::Start)return Action::StartTouch;
    if(released==Choice::Diagnostic)automatic_=false;
    if(automatic_&&now-started_>=AUTO_MS)return Action::StartAuto;
    return Action::Wait;
  }
};
}
