# StackChan port (experimental)
This directory contains an isolated hardware smoke test, not the TamaPoke game.
Do not flash upstream Waveshare firmware on StackChan. Back up factory flash first.
The sketch checks display geometry, touch, speaker, battery reading and a temporary
NVS key. Motor control and SD are intentionally omitted until official board APIs
and pin mappings are verified. The generic ESP32-S3 build options are provisional;
verify PSRAM mode and partition layout against the actual K151 before flashing.
The original game uses a 466x466 canvas and board-specific touch, display, power,
audio and SD drivers. The coordinate adapter maps a centered 240x240 viewport
back to that canvas. Next: integrate graphics and input adapters, then audio,
RTC, power and storage while preserving host game tests.
Do not distribute this smoke artifact as game firmware.
