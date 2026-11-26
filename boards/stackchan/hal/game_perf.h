#pragma once
#include <Arduino.h>
#include <esp_heap_caps.h>
#include <esp_system.h>
#include "perf_policy.h"

namespace tpkperf {
class GamePerf {
  Monitor monitor_;
  uint32_t sequence_=0;
  void memory() {
    Serial.printf("PERF_MEM seq=%lu up_ms=%lu heap=%lu heap_min=%lu heap_largest=%lu psram=%lu psram_total=%lu psram_largest=%lu reset=%d cpu_mhz=%lu\n",
      (unsigned long)sequence_,(unsigned long)millis(),
      (unsigned long)ESP.getFreeHeap(),(unsigned long)ESP.getMinFreeHeap(),
      (unsigned long)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT),
      (unsigned long)ESP.getFreePsram(),(unsigned long)ESP.getPsramSize(),
      (unsigned long)heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT),
      int(esp_reset_reason()),(unsigned long)ESP.getCpuFreqMHz());
  }
  void report(bool off,bool dim,bool game) {
    auto w=monitor_.take(millis());++sequence_;
    Serial.printf("PERF_TIME seq=%lu window_ms=%lu frames=%lu fps_milli=%lu render_avg_us=%lu render_max_us=%lu flush_avg_us=%lu flush_max_us=%lu loop_avg_us=%lu loop_max_us=%lu slow_loops=%lu off=%d dim=%d game=%d\n",
      (unsigned long)sequence_,(unsigned long)w.elapsedMs,(unsigned long)w.frames,(unsigned long)w.fpsMilli(),
      (unsigned long)w.render.mean(),(unsigned long)w.render.maximum,
      (unsigned long)w.flush.mean(),(unsigned long)w.flush.maximum,
      (unsigned long)w.loop.mean(),(unsigned long)w.loop.maximum,
      (unsigned long)w.slowLoops,off,dim,game);
    if(monitor_.detailSelected()){
      const auto& d=w.detail;
      Serial.printf("PERF_LCD seq=%lu samples=%lu compare_avg_us=%lu compare_max_us=%lu pack_avg_us=%lu pack_max_us=%lu transfer_avg_us=%lu transfer_max_us=%lu shadow_avg_us=%lu shadow_max_us=%lu other_avg_us=%lu pixels=%llu rects=%llu shadow_bytes=%llu unchanged=%lu full=%lu\n",
        (unsigned long)sequence_,(unsigned long)d.compare.count,
        (unsigned long)d.compare.mean(),(unsigned long)d.compare.maximum,
        (unsigned long)d.pack.mean(),(unsigned long)d.pack.maximum,
        (unsigned long)d.transfer.mean(),(unsigned long)d.transfer.maximum,
        (unsigned long)d.shadow.mean(),(unsigned long)d.shadow.maximum,
        (unsigned long)d.other.mean(),(unsigned long long)d.pixels,(unsigned long long)d.rects,
        (unsigned long long)d.shadowBytes,(unsigned long)d.unchanged,(unsigned long)d.full);
      const auto& t=w.touch;
      Serial.printf("PERF_TOUCH seq=%lu samples=%lu gaps=%lu gap_avg_us=%lu gap_max_us=%lu pressed=%lu press_edges=%lu release_edges=%lu stale=%lu\n",
        (unsigned long)sequence_,(unsigned long)t.samples,(unsigned long)t.gap.count,
        (unsigned long)t.gap.mean(),(unsigned long)t.gap.maximum,(unsigned long)t.pressed,
        (unsigned long)t.pressEdges,(unsigned long)t.releaseEdges,(unsigned long)t.stale);
    }
    memory();
  }
public:
  Monitor& monitor(){return monitor_;}
  void tick(bool off,bool dim,bool game){
    if(monitor_.due(millis()))report(off,dim,game);
  }
  bool command(const String& line,bool off,bool dim,bool game){
    if(line=="PERF DETAIL ON"||line=="PERF DETAIL OFF"){
      monitor_.setDetail(line=="PERF DETAIL ON",millis());
      Serial.println(monitor_.detailSelected()?"DONE PERF DETAIL ON":"DONE PERF DETAIL OFF");return true;
    }
    if(line=="PERF DETAIL?"){Serial.printf("PERF_DETAIL selected=%d active=%d\n",monitor_.detailSelected(),monitor_.detailEnabled());Serial.println("DONE");return true;}
    if(line=="PERF ON"){monitor_.start(millis());Serial.println("DONE PERF ON");return true;}
    if(line=="PERF OFF"){monitor_.stop();Serial.println("DONE PERF OFF");return true;}
    if(line=="PERF?"){
      if(monitor_.enabled())report(off,dim,game);else{++sequence_;memory();}
      Serial.println("DONE");return true;
    }
    return false;
  }
};
}
