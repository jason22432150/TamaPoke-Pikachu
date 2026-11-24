#include "stackchan_hal.h"
StackChanHAL board;
bool ready=false, wasPressed=false;
uint32_t last=0;
void setup() {
  Serial.begin(115200);
  Serial.println("TamaPoke K151 diagnostic; NOT GAME; no NVS writes");
  auto result=board.begin();
  ready=result==BootStatus::Ok;
  Serial.printf("Boot status: %u, flash: %u, PSRAM: %u\n",unsigned(result),
      unsigned(ESP.getFlashChipSize()),unsigned(ESP.getPsramSize()));
  if(!ready) return;
  board.brightness(96);
  M5.Display.fillScreen(0);
  M5.Display.drawRect(40,0,240,240,0xffff);
  M5.Display.setTextColor(0xffff,0);
  M5.Display.setCursor(48,15);
  M5.Display.println("StackChan HAL diagnostic");
  M5.Display.setCursor(48,40);
  M5.Display.printf("PSRAM: OK RTC: %s",board.rtcAvailable()?"OK":"missing");
  M5.Display.setCursor(48,60);
  M5.Display.println("Tap square for tone");
}
void loop() {
  if(!ready) {delay(100);return;}
  board.update();
  auto p=board.touch(); auto q=toLogical(p);
  if(p.pressed && !wasPressed && q.valid) {
    board.tone(880,80);
    Serial.printf("Touch %d,%d -> %d,%d\n",p.x,p.y,q.x,q.y);
    M5.Display.fillRect(48,90,224,30,0);
    M5.Display.setCursor(48,90);
    M5.Display.printf("Game: %d,%d",q.x,q.y);
  }
  wasPressed=p.pressed;
  if(millis()-last>=2000) {
    last=millis(); M5.Display.fillRect(48,130,224,20,0);
    M5.Display.setCursor(48,130);
    int pct=board.batteryPercent();
    if(pct>=0 && pct<=100) M5.Display.printf("Battery: %d%%",pct);
    else M5.Display.print("Battery: unknown");
  }
  delay(10);
}
