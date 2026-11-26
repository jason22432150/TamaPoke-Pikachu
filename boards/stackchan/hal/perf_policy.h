#pragma once
#include <stdint.h>
namespace tpkperf {
struct Timing {
  uint64_t total=0;
  uint32_t count=0,maximum=0;
  void add(uint32_t us){total+=us;++count;if(us>maximum)maximum=us;}
  uint32_t mean()const{return count?uint32_t(total/count):0;}
};
// One sample per flush, including zero-cost stages in unchanged frames.
struct FlushSample {
  uint32_t compare=0,pack=0,transfer=0,shadow=0;
};
struct FlushDetail {
  Timing compare,pack,transfer,shadow,other;
  uint64_t pixels=0,rects=0,shadowBytes=0;
  uint32_t unchanged=0,full=0;
  void add(uint32_t elapsed,const FlushSample& s,uint32_t sent,uint32_t count,bool cached,bool forced){
    compare.add(s.compare);pack.add(s.pack);transfer.add(s.transfer);shadow.add(s.shadow);
    const uint64_t sum=uint64_t(s.compare)+s.pack+s.transfer+s.shadow;
    other.add(sum<elapsed?uint32_t(elapsed-sum):0);
    pixels+=sent;rects+=count;if(cached)shadowBytes+=uint64_t(sent)*2u;
    if(!count)++unchanged;
    if(forced)++full;
  }
};
struct Window {
  uint32_t elapsedMs=0;
  Timing loop,render,flush;
  FlushDetail detail;
  uint32_t frames=0,slowLoops=0;
  uint32_t fpsMilli()const{return elapsedMs?uint32_t(uint64_t(frames)*1000000/elapsedMs):0;}
};
constexpr uint32_t REPORT_MS=5000;
class Monitor {
  bool enabled_=false,hasLoop_=false,detail_=false;
  uint32_t startMs_=0,lastLoopUs_=0;
  Window w_;
public:
  bool enabled()const{return enabled_;}
  bool detailEnabled()const{return enabled_&&detail_;}
  bool detailSelected()const{return detail_;}
  // Do not mix instrumented and uninstrumented frames in a window.
  void setDetail(bool value,uint32_t ms){if(detail_==value)return;detail_=value;if(enabled_)start(ms);}
  void start(uint32_t ms){enabled_=true;startMs_=ms;hasLoop_=false;w_=Window{};}
  void stop(){enabled_=false;hasLoop_=false;}
  void loopStart(uint32_t us){
    if(!enabled_)return;
    if(hasLoop_){uint32_t gap=us-lastLoopUs_;w_.loop.add(gap);if(gap>=100000)++w_.slowLoops;}
    lastLoopUs_=us;hasLoop_=true;
  }
  void rendered(uint32_t us){if(enabled_)w_.render.add(us);}
  void flushed(uint32_t us){if(enabled_){w_.flush.add(us);++w_.frames;}}
  void flushedDetailed(uint32_t us,const FlushSample& s,uint32_t sent,uint32_t count,bool cached,bool forced){
    if(!enabled_)return;
    flushed(us);
    if(detail_)w_.detail.add(us,s,sent,count,cached,forced);
  }
  bool due(uint32_t ms)const{return enabled_&&ms-startMs_>=REPORT_MS;}
  Window snapshot(uint32_t ms)const{Window copy=w_;copy.elapsedMs=ms-startMs_;return copy;}
  Window take(uint32_t ms){Window copy=snapshot(ms);w_=Window{};startMs_=ms;return copy;}
};
}
