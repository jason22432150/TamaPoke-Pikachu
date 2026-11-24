#include "stackchan_hal.h"
#include <Preferences.h>
StackChanHAL board;
bool ready = false;
uint32_t last = 0;
bool wasPressed = false;
void setup() {
  Serial.begin(115200);
  ready = board.begin();
  if (!ready) { Serial.println("Unexpected display geometry; stopped"); return; }
  board.brightness(96);
  M5.Display.fillScreen(0);
  M5.Display.drawRect(40, 0, 240, 240, 0xffff);
  M5.Display.setTextColor(0xffff, 0);
  M5.Display.setCursor(48, 15);
  M5.Display.println("StackChan HAL smoke test");
  Preferences prefs;
  bool nvs = prefs.begin("tpk-smoke", false);
  if (nvs) {
    nvs = prefs.putUInt("probe", 0x1234) == sizeof(uint32_t) &&
          prefs.getUInt("probe") == 0x1234;
    prefs.remove("probe");
    prefs.end();
  }
  Serial.printf("NVS: %s; PSRAM: %u bytes\n", nvs ? "OK" : "FAIL", unsigned(ESP.getPsramSize()));
  M5.Display.setCursor(48, 40);
  M5.Display.printf("NVS: %s\n", nvs ? "OK" : "FAIL");
  M5.Display.setCursor(48, 60);
  M5.Display.println("Tap inside square for tone");
}
void loop() {
  if (!ready) { delay(100); return; }
  board.update();
  auto p = board.touch();
  auto q = toLogical(p);
  if (p.pressed && !wasPressed && q.valid) {
    board.tone(880, 80);
    Serial.printf("Touch %d,%d -> %d,%d\n", p.x,p.y,q.x,q.y);
    M5.Display.fillRect(48, 90, 224, 30, 0);
    M5.Display.setCursor(48, 90);
    M5.Display.printf("Game: %d,%d", q.x,q.y);
  }
  wasPressed = p.pressed;
  if (millis()-last >= 2000) {
    last = millis();
    M5.Display.fillRect(48, 130, 224, 20, 0);
    M5.Display.setCursor(48, 130);
    M5.Display.printf("Battery: %d%%", board.batteryPercent());
  }
  delay(10);
}
