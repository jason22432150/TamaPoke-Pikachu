// Compile-only core integration probe. NOT a full game or flash release.
#include "stackchan_hal.h"
#include "pet.h"
#include "dex.h"
#include "audio.h"
#include <SD.h>
#include <SPI.h>
#include <time.h>
StackChanHAL board;
Pet pet;
M5Canvas frame(&M5.Display);
bool ready=false, started=false, previous=false;
uint32_t lastDraw=0, lastClock=0;
char line[16]; size_t used=0; bool overflow=false;
static uint32_t rtcEpoch() {
  m5::rtc_datetime_t t;
  if(!board.rtcAvailable() || !M5.Rtc.getDateTime(&t)) return 0;
  if(t.date.year<2025 || t.date.year>2099 || t.date.month<1 || t.date.month>12 ||
     t.date.date<1 || t.date.date>31 || t.time.hours<0 || t.time.hours>23 ||
     t.time.minutes<0 || t.time.minutes>59 || t.time.seconds<0 || t.time.seconds>59) return 0;
  tm v={}; v.tm_year=t.date.year-1900; v.tm_mon=t.date.month-1;
  v.tm_mday=t.date.date; v.tm_hour=t.time.hours; v.tm_min=t.time.minutes; v.tm_sec=t.time.seconds;
  time_t result=mktime(&v);
  return result>0?uint32_t(result):0;
}
static void draw() {
  frame.fillScreen(0);
  frame.setTextColor(0xffff,0);
  frame.setCursor(8,8);
  frame.println("K151 core probe");
  frame.printf("Battery: %d%%\n",board.batteryPercent());
  if(!started) { frame.println("Serial: START to opt in"); frame.pushSprite(40,0); return; }
  frame.printf("%s  Lv %u\n",pet.isEgg()?"Egg":dexName(pet.speciesId),unsigned(pet.level()));
  frame.printf("Food %u Joy %u\n",unsigned(pet.fullness),unsigned(pet.joy));
  frame.printf("Energy %u Clean %u\n",unsigned(pet.energy),unsigned(pet.hygiene));
  if(pet.isEgg()) frame.fillEllipse(120,110,27,36,0xffe0);
  else frame.fillCircle(120,110,32,0xffe0);
  const char* labels[]={"Feed","Play","Clean"};
  for(int i=0;i<3;i++) {frame.drawRect(i*80,190,80,50,0xffff);frame.setCursor(i*80+6,205);frame.print(labels[i]);}
  frame.pushSprite(40,0);
}
static void command() {
  if(!strcmp(line,"START") && !started) {
    if(!pet.beginWithNamespace("tpk-k151")) {Serial.println("NVS unavailable; start refused");return;}
    started=true; audioBegin();
    if(pet.awaitingStarter()) pet.chooseStarter(25);
    pet.syncClock(rtcEpoch());
    lastClock=millis();
    Serial.println("Core probe started; isolated NVS namespace tpk-k151");
  } else if(!strcmp(line,"SD") && started) {
    // Official StackChan pin map. No formatting or write-mode file handles.
    SPI.begin(36,35,37,4);
    if(SD.begin(4,SPI,4000000)) {
      File f=SD.open("/mons",FILE_READ);
      Serial.printf("SD /mons: %s\n",f && f.isDirectory()?"present":"not found");
      f.close(); SD.end();
    } else Serial.println("SD mount failed; no formatting attempted");
  }
}
void setup() {
  Serial.begin(115200);
  Serial.println("Compile-only K151 core probe; not production firmware");
  if(board.begin()!=BootStatus::Ok) return;
  frame.setColorDepth(16);
  if(!frame.createSprite(240,240)) return;
  setenv("TZ","UTC0",1); tzset();
  ready=true; board.brightness(96); M5.Display.fillScreen(0); draw();
}
void loop() {
  if(!ready) {delay(100);return;}
  board.update();
  while(Serial.available()) {
    int ch=Serial.read();
    if(ch=='\n'||ch=='\r') { if(!overflow && used) {line[used]=0;command();} used=0;overflow=false;}
    else if(used<sizeof(line)-1) line[used++]=char(ch); else overflow=true;
  }
  if(started) {
    pet.update(millis());
    if(millis()-lastClock>=60000) {lastClock=millis();uint32_t now=rtcEpoch();if(now)pet.setClock(now);}
    auto p=board.touch();auto q=toLogical(p);
    if(q.valid && !previous) {
      if(q.y>=369) {
        if(q.x<155) pet.feed(); else if(q.x<310) pet.play(); else pet.clean();
      } else if(pet.isEgg()) pet.eggTap(); else if(pet.canEvolveNow()) pet.evolve(); else pet.caress();
    }
    previous=p.pressed;
  }
  if(millis()-lastDraw>=250) {lastDraw=millis();draw();}
  delay(10);
}
