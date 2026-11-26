#include "hal/perf_policy.h"
#include <cassert>
using namespace tpkperf;
int main(){
  Monitor m;
  m.flushed(2000);assert(!m.due(10000));
  m.start(100);
  m.loopStart(1000);m.loopStart(2000);m.loopStart(102000);
  m.rendered(20000);m.rendered(40000);
  m.flushed(10000);m.flushed(12000);
  assert(!m.due(5099)&&m.due(5100));
  auto w=m.take(5100);
  assert(w.elapsedMs==5000&&w.frames==2&&w.fpsMilli()==400);
  assert(w.loop.count==2&&w.loop.mean()==50500&&w.loop.maximum==100000&&w.slowLoops==1);
  assert(w.render.mean()==30000&&w.render.maximum==40000);
  assert(w.flush.mean()==11000&&w.flush.maximum==12000);
  assert(m.snapshot(5100).fpsMilli()==0);
  m.stop();m.flushed(100);assert(!m.enabled()&&!m.due(20000));
  m.start(UINT32_MAX-100);m.loopStart(UINT32_MAX-50);m.loopStart(49);
  m.flushed(10);assert(m.due(4899));
  w=m.take(4899);assert(w.elapsedMs==5000&&w.loop.maximum==100&&w.fpsMilli()==200);
  // Opt-in phase accounting, all averages per flush including unchanged.
  m.start(0);assert(!m.detailEnabled());m.flushed(100);
  m.setDetail(true,100);assert(m.detailEnabled()&&m.snapshot(100).frames==0);
  FlushSample sample;sample.compare=100;sample.pack=200;sample.transfer=400;sample.shadow=50;
  m.flushedDetailed(800,sample,128,1,true,false);
  FlushSample unchanged;unchanged.compare=80;
  m.flushedDetailed(100,unchanged,0,0,true,false);
  w=m.take(5100);
  assert(w.frames==2&&w.flush.mean()==450&&w.detail.compare.count==2);
  assert(w.detail.compare.mean()==90&&w.detail.pack.mean()==100&&w.detail.transfer.mean()==200);
  assert(w.detail.shadow.mean()==25&&w.detail.other.mean()==35&&w.detail.transfer.maximum==400);
  assert(w.detail.pixels==128&&w.detail.rects==1&&w.detail.shadowBytes==256&&w.detail.unchanged==1&&w.detail.full==0);
  m.flushedDetailed(10,sample,320,1,false,true);w=m.snapshot(5200);
  assert(w.detail.other.mean()==0&&w.detail.full==1&&w.detail.shadowBytes==0);
  m.setDetail(false,5200);assert(m.snapshot(5200).frames==0&&!m.detailEnabled());
  m.flushed(123);w=m.take(5300);assert(w.frames==1&&w.detail.compare.count==0);
  m.stop();m.setDetail(true,5400);assert(m.detailSelected()&&!m.detailEnabled());
  m.flushedDetailed(100,sample,128,1,true,false);assert(m.snapshot(5400).frames==0);
  m.start(5500);assert(m.detailEnabled());
  Timing t;for(int i=0;i<100;i++)t.add(UINT32_MAX);
  assert(t.mean()==UINT32_MAX);
}
