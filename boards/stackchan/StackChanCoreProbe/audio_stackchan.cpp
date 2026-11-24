#include "audio.h"
#include <M5Unified.h>
static bool enabled=true,sleeping=false;
static uint8_t volume=0;
void audioBegin(){audioSetVolume(volume);}
void sfxPlay(uint8_t id){
  static const uint16_t hz[]={880,660,784,1047,523,1319,1175,300,523,988};
  if(id<SFX_COUNT && enabled && !sleeping && M5.Speaker.isEnabled())
    M5.Speaker.tone(hz[id],90,0,true);
}
void audioSetEnabled(bool on){enabled=on;if(!on)M5.Speaker.stop();}
bool audioEnabled(){return enabled;}
void audioSetVolume(uint8_t v){volume=v%VOL_LEVELS;static const uint8_t levels[]={64,32,12};M5.Speaker.setVolume(levels[volume]);}
uint8_t audioVolume(){return volume;}
void audioSetSleeping(bool v){sleeping=v;if(v)M5.Speaker.stop();}
bool audioBusy(){return M5.Speaker.isPlaying();}
void audioSetIdle(bool){}
