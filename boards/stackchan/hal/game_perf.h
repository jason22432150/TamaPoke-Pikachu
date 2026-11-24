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
    memory();
  }
public:
  Monitor& monitor(){return monitor_;}
  void tick(bool off,bool dim,bool game){
    if(monitor_.due(millis()))report(off,dim,game);
  }
  bool command(const String& line,bool off,bool dim,bool game){
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
