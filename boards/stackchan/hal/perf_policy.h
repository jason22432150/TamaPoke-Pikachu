#pragma once
#include <stdint.h>
namespace tpkperf {
struct Timing {
  uint64_t total=0;
  uint32_t count=0,maximum=0;
  void add(uint32_t us){total+=us;++count;if(us>maximum)maximum=us;}
  uint32_t mean()const{return count?uint32_t(total/count):0;}
};
struct Window {
  uint32_t elapsedMs=0;
  Timing loop,render,flush;
  uint32_t frames=0,slowLoops=0;
  uint32_t fpsMilli()const{return elapsedMs?uint32_t(uint64_t(frames)*1000000/elapsedMs):0;}
};
constexpr uint32_t REPORT_MS=5000;
class Monitor {
  bool enabled_=false,hasLoop_=false;
  uint32_t startMs_=0,lastLoopUs_=0;
  Window w_;
public:
  bool enabled()const{return enabled_;}
  void start(uint32_t ms){enabled_=true;startMs_=ms;hasLoop_=false;w_=Window{};}
  void stop(){enabled_=false;hasLoop_=false;}
  void loopStart(uint32_t us){
    if(!enabled_)return;
    if(hasLoop_){uint32_t gap=us-lastLoopUs_;w_.loop.add(gap);if(gap>=100000)++w_.slowLoops;}
    lastLoopUs_=us;hasLoop_=true;
  }
  void rendered(uint32_t us){if(enabled_)w_.render.add(us);}
  void flushed(uint32_t us){if(enabled_){w_.flush.add(us);++w_.frames;}}
  bool due(uint32_t ms)const{return enabled_&&ms-startMs_>=REPORT_MS;}
  Window snapshot(uint32_t ms)const{Window copy=w_;copy.elapsedMs=ms-startMs_;return copy;}
  Window take(uint32_t ms){Window copy=snapshot(ms);w_=Window{};startMs_=ms;return copy;}
};
}
