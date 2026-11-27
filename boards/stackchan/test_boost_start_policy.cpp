#include "hal/boost_start_policy.h"
#include <cassert>
#include <vector>
using namespace tpkboost;
struct Fake {
  uint8_t dir=0x8c,out=0xbb;
  unsigned writes=0,reads=0,failWrite=0,failRead=0;
  std::vector<uint8_t> history;
  std::vector<uint32_t> waits;
  bool read(uint8_t reg,uint8_t& v){
    if(++reads==failRead)return false;
    assert(reg==OUT||reg==DIR);v=reg==OUT?out:dir;return true;
  }
  bool write(uint8_t reg,uint8_t v){
    assert(reg==OUT);++writes;
    if(writes==failWrite)return false;
    assert((v&0x7f)==(out&0x7f));out=v;history.push_back(v);return true;
  }
  bool prep(){return prepare([&](uint8_t r,uint8_t& v){return read(r,v);},
      [&](uint8_t r,uint8_t v){return write(r,v);});}
  bool run(){return start([&](uint8_t r,uint8_t& v){return read(r,v);},
      [&](uint8_t r,uint8_t v){return write(r,v);},
      [&](uint32_t us){waits.push_back(us);});}
};
int main(){
  Fake a;assert(a.prep()&&a.out==0x3b&&a.writes==1);
  assert(!a.run()&&a.writes==1);a.dir=0x0c;
  assert(a.run()&&a.out==0xbb&&a.writes==42);
  assert(a.waits.size()==41&&a.waits.back()==50000);
  for(unsigned i=0;i<20;++i){
    assert(a.history[1+i*2]==0xbb&&a.history[2+i*2]==0x3b);
    assert(a.waits[2*i]==150);
    if(i)assert(a.waits[2*i+1]<a.waits[2*i-1]);
  }
  assert(a.prep()&&a.run()&&a.writes==42);
  for(unsigned n=1;n<=41;++n){
    Fake b;b.dir=0x0c;b.out=0x3b;b.failWrite=n;
    assert(!b.run()&&b.writes==n);
  }
  for(unsigned n=1;n<=3;++n){
    Fake b;b.dir=0x0c;b.out=0x3b;b.failRead=n;
    assert(!b.run());if(n<3)assert(b.writes==0);
  }
  Fake c;c.failWrite=1;assert(!c.prep()&&c.writes==1);
  Fake d;d.failRead=3;assert(!d.prep()&&d.writes==1);
}
