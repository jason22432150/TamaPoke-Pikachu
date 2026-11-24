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
  Timing t;for(int i=0;i<100;i++)t.add(UINT32_MAX);
  assert(t.mean()==UINT32_MAX);
}
