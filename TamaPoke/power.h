#pragma once
#include <stdint.h>

// Politica de consumo. Todo lo que decide cuanto trabaja la placa vive aqui como
// funciones puras (sin hardware), para poder probarlas en el PC (test/test_power.cpp).
//
// Donde se gasta la bateria: la pantalla AMOLED (brillo y contenido), la CPU mientras
// dibuja y vuelca el lienzo por QSPI (~70 ms de cada 100 a 10 fps), el amplificador del
// altavoz si esta encendido sin sonar, y los despertares del bucle principal.

// Escalones de inactividad (ms desde el ultimo toque o evento visible)
#define POWER_CALM_MS 60000UL   // pasado este tiempo, se dibuja algo menos
#define POWER_DIM1_MS 90000UL   // pantalla atenuada
#define POWER_DIM2_MS 300000UL  // pantalla casi apagada

enum DimStage : uint8_t { DIM_AWAKE = 0, DIM_LOW = 1, DIM_OFF = 2 };

struct PowerCtx {
  uint32_t idleMs;    // ms sin interaccion
  bool screenOff;     // apagada con el boton PWR
  bool sleeping;      // el bicho duerme
  bool gameOpen;      // minijuego o saco: la fisica esta afinada a 85 ms por frame
  bool usb;           // alimentacion externa
  bool charging;
  int batPct;         // 0-100, -1 si no hay bateria
  uint8_t userDim;    // nivel de brillo elegido en ajustes: 0 = alto (el de siempre), 1 = medio, 2 = bajo
};

// niveles de brillo de ajustes (#34): porcentaje que se aplica a todos los brillos de abajo
#define BRIGHT_LEVELS 3
inline uint8_t userBrightPct(uint8_t userDim) { return userDim == 1 ? 60 : userDim >= 2 ? 30 : 100; }

// ms desde `last`, sin desbordar si `last` es posterior a `now` (un toque atendido despues de
// leer el reloj al principio del bucle): se tomaba como 49 dias de inactividad y el panel
// pasaba un instante a brillo 8 en cada toque
inline uint32_t idleSince(uint32_t now, uint32_t last) {
  int32_t d = (int32_t)(now - last);
  return d < 0 && d > -1000 ? 0 : now - last;  // solo un adelanto de unos ms cuenta como "ahora"; 25 dias sin tocar siguen siendo 25 dias
}

inline uint8_t dimStageFor(uint32_t idleMs) {
  return idleMs > POWER_DIM2_MS ? DIM_OFF : idleMs > POWER_DIM1_MS ? DIM_LOW : DIM_AWAKE;
}

// bateria baja: se ahorra mas (solo si de verdad depende de la bateria)
inline bool batteryLow(const PowerCtx &c) { return c.batPct >= 0 && c.batPct < 20 && !c.charging && !c.usb; }
inline bool batteryCritical(const PowerCtx &c) { return c.batPct >= 0 && c.batPct < 10 && !c.charging && !c.usb; }

// brillo del panel (0-255): el de siempre, con un tope cuando queda poca bateria y escalado
// por el nivel elegido en ajustes
inline uint8_t brightnessFor(const PowerCtx &c) {
  if (c.screenOff) return 0;
  uint8_t stage = dimStageFor(c.idleMs);
  uint8_t t = c.sleeping ? 25 : (c.usb ? 180 : 145);
  if (stage == DIM_LOW) t = c.sleeping ? 10 : 60;
  else if (stage == DIM_OFF) t = 8;
  if (batteryCritical(c) && t > 60) t = 60;
  else if (batteryLow(c) && t > 100) t = 100;
  if (c.userDim) {  // el nivel elegido escala todo, sin bajar de 2 (0 seria pantalla apagada)
    t = (uint8_t)((uint16_t)t * userBrightPct(c.userDim) / 100);
    if (t < 2) t = 2;
  }
  return t;
}

// ms entre frames; 0 = no se dibuja (pantalla apagada). Cada frame cuesta un render
// completo y el volcado del lienzo por QSPI, y el panel solo cambia si se redibuja.
inline uint32_t frameIntervalMs(const PowerCtx &c) {
  if (c.screenOff) return 0;
  if (c.gameOpen) return 85;  // el juego manda: su fisica esta afinada a este periodo
  uint32_t ms;
  uint8_t stage = dimStageFor(c.idleMs);
  if (stage == DIM_OFF) ms = 1000;
  else if (c.sleeping && c.idleMs > POWER_CALM_MS) ms = 500;  // dormido y sin tocar: casi nada se mueve
  else if (stage == DIM_LOW) ms = 250;
  else ms = c.idleMs > POWER_CALM_MS ? 150 : 100;
  if (batteryLow(c)) ms *= 2;
  return ms;
}

// K151-only caller: selected active render cap, not panel refresh or game speed.
// Keep the original mini-game cadence and never accelerate power-saving states.
inline bool stackFpsAllowed(uint8_t fps) {
  return fps == 5 || fps == 10 || fps == 15 || fps == 20 || fps == 30;
}
inline uint8_t stackNextFps(uint8_t fps) {
  switch(fps){
    case 5:return 10; case 10:return 15; case 15:return 20;
    case 20:return 30; case 30:return 5; default:return 10;
  }
}
inline uint32_t stackFrameIntervalMs(const PowerCtx &c, uint8_t fps) {
  const uint32_t base = frameIntervalMs(c);
  if (!base || c.gameOpen || !stackFpsAllowed(fps)) return base;
  const uint32_t requested = (1000u + fps - 1u) / fps;
  if (c.sleeping || c.idleMs > POWER_CALM_MS || batteryLow(c)) {
    const uint32_t cap = batteryLow(c) ? requested * 2u : requested;
    return base > cap ? base : cap;
  }
  return requested;
}

// Route the cached M5 touch sample sooner during active high-FPS UI.
// Minigame, idle, sleep and dim/off routing intervals are unchanged.
inline uint32_t stackTouchPollMs(bool game,bool active,uint8_t fps){
  return game||(active&&stackFpsAllowed(fps)&&fps>=20)?10u:20u;
}
// Precise cadence only for the normal active K151 renderer. All other
// modes keep the millisecond policy and its original wake behavior.
inline uint32_t stackActivePeriodUs(const PowerCtx &c,uint8_t fps){
  if(c.screenOff||c.gameOpen||c.sleeping||c.idleMs>POWER_CALM_MS||batteryLow(c)||!stackFpsAllowed(fps))return 0;
  return (1000000u+fps-1u)/fps;
}
// One render attempt per loop. Compensate at most 2 ms of polling jitter;
// rebase on longer stalls, never issue a batch of missed frames. Unsigned
// elapsed arithmetic supports micros() wrap. No hardware/timer dependency.
class StackFrameCadence {
  uint32_t anchor_=0,last_=0,period_=0;
  bool seen_=false;
public:
  void legacyAttempt(uint32_t now){anchor_=last_=now;period_=0;seen_=true;}
  void reset(){seen_=false;period_=0;}
  bool due(uint32_t now,uint32_t period){
    if(!period)return false;
    if(!seen_){anchor_=last_=now;period_=period;seen_=true;return true;}
    if(period_!=period){anchor_=last_;period_=period;}
    const uint32_t elapsed=now-anchor_;
    if(elapsed<period)return false;
    const uint32_t late=elapsed-period;
    anchor_=late<=2000u?anchor_+period:now;
    last_=now;return true;
  }
};

// el amplificador del altavoz consume en reposo: solo se tiene encendido mientras
// alguien puede estar jugando
inline bool amplifierWanted(const PowerCtx &c) {
  return !c.screenOff && !c.sleeping && dimStageFor(c.idleMs) == DIM_AWAKE;
}

// pausa del bucle principal en un pase que no dibuja
inline uint32_t idleDelayMs(const PowerCtx &c) { return c.screenOff ? 20 : 1; }
// K151: bounded task yield, not MCU sleep or frequency scaling. Keep USB,
// charging, gestures, games, serial and active rendering on the 1 ms path.
// Only relax battery-powered calm/off loops; never wait past a legacy frame.
inline uint32_t stackIdleDelayMs(const PowerCtx &c,bool busy,uint32_t sinceRenderMs,uint32_t interval){
  if(busy||c.usb||c.charging||c.gameOpen||(!c.screenOff&&c.idleMs<=POWER_CALM_MS))return 1;
  const uint32_t limit=c.screenOff?5u:4u;
  if(!interval)return limit;
  if(sinceRenderMs>=interval)return 1;
  const uint32_t remaining=interval-sinceRenderMs;
  return remaining<limit?remaining:limit;
}

// con la pantalla apagada, o casi apagada (5 min sin tocar), y sin USB se duerme la CPU (light
// sleep) entre frames y sondeos; con USB no: se perderia el puerto serie de la tarjeta SD
inline bool lightSleepAllowed(const PowerCtx &c) {
  return !c.usb && (c.screenOff || dimStageFor(c.idleMs) == DIM_OFF);
}
#define POWER_SLEEP_MS 200  // duracion de cada sueno; el toque despierta antes

// cada cuanto se lee la bateria por I2C
inline uint32_t powerCacheMs(const PowerCtx &c) {
  return (c.screenOff || dimStageFor(c.idleMs) == DIM_OFF) ? 10000 : 2000;
}
