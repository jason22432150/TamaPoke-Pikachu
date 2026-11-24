#include "hal/sidebar_policy.h"
#include <cassert>
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
}
