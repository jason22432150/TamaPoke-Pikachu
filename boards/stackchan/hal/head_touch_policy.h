#pragma once
#include <stdint.h>
namespace tpkhead {
struct Sample{
  uint8_t left,center,right;
  bool touched()const{return left||center||right;}
  int position()const{
    int sum=left+center+right;
    return sum?100*(int(right)-int(left))/sum:0;
  }
};
inline Sample decode(uint8_t raw){return {uint8_t(raw&3),uint8_t((raw>>2)&3),uint8_t((raw>>4)&3)};}
enum class Event {None,Press,Forward,Backward,Release};
class Gesture{
  bool armed_=false,down_=false,swiped_=false;
  uint8_t quiet_=0,contact_=0;
  int origin_=0;
public:
  void reset(){armed_=down_=swiped_=false;quiet_=contact_=0;origin_=0;}
  Event update(Sample s){
    if(!s.touched()){
      contact_=0;
      if(quiet_<2)++quiet_;
      if(quiet_<2)return Event::None;
      armed_=true;
      if(down_){down_=swiped_=false;return Event::Release;}
      return Event::None;
    }
    quiet_=0;
    if(!armed_)return Event::None;
    if(!down_){
      if(++contact_<2)return Event::None;
      down_=true;origin_=s.position();return Event::Press;
    }
    if(!swiped_){
      int delta=s.position()-origin_;
      if(delta>40||delta< -40){swiped_=true;return delta>0?Event::Forward:Event::Backward;}
    }
    return Event::None;
  }
};
}
