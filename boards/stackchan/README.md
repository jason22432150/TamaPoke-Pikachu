# StackChan K151 experimental port
This branch is NOT ready to flash. The diagnostic uses a provisional standalone
16 MiB partition layout, NOT the factory layout. A full flash backup, security
state and actual factory partition map must be checked on the target unit first.
There is no upload command, web installer or factory-compatible release.
The smoke sketch does not write Preferences, mount/format SD, touch servos,
or directly program PMIC registers. M5Unified itself initializes board hardware
and Arduino may initialize NVS at boot; this is not a guarantee of preserving
factory data. Do not flash merely because CI passes.
The shared HAL rejects unexpected flash/PSRAM capacity, failed memory pattern
tests, non-StackChan detection, invalid display geometry and disabled touch.
RTC availability is reported but not altered. Audio and battery are manual/visual
diagnostics. Full body identification, orientation and speaker/RTC/SD testing
require hardware. Library candidate versions are in versions.env; BSP is pinned
for future use, not yet linked or tested.
CI runs original game tests and coordinate/partition checks, then builds a
diagnostic artifact with source commit, target, version and SHA256 metadata.
A compile-only CoreProbe reuses upstream pet.cpp and i18n, with simple native
M5Canvas UI, touch, simplified tones, RTC read and opt-in SD directory probe.
It requires explicit serial START before creating isolated tpk-k151 NVS data.
RTC is read only and SD is mounted without formatting; no file writes.
No full game assets, UI parity, body controls or release yet. Original Waveshare
behavior keeps its tamapoke namespace; the core adds a checked alternate namespace.

## Full game compile target (experimental)
The BOARD_STACKCHAN target compiles the original TamaPoke sketch, sprites, CJK
fonts, menus, animations and game logic, preserving logical 466x466 coordinates.
The Arduino_GFX RAM canvas is transmitted through M5GFX to a 240x240 viewport.
It uses the dedicated tpk-k151-game namespace, opt-in START and SDWRITE ON,
SPI SD with no auto-format, M5Unified RTC/power/speaker APIs. The Waveshare
sleep GPIO path is excluded. Runtime and all interactions remain unverified;
no full game artifact is published. Motor/RGB and native widescreen redesign
are outside this target. Do not flash before factory backup/security/layout review.

The first full K151 game build passed at d60d4a0 (Actions run 45306960321):
1,588,595 bytes of a 3 MiB app slot. Subsequent changes require new CI.
The display adapter explicitly sets native RGB565 byte order and samples eight
rows per transfer with a precomputed coordinate map. Host tests verify display
sampling and touch mapping agree. CI also compiles the original Waveshare 1.75
using the dependency versions recorded in evidence/build-manifest.json.

## Experimental body adapter
Uses only the official BSP 1.1.0 PY32IOExpander driver at the exact commit in
versions.env. No full BSP begin(), servo rail enable, servo bus commands, motor
motion or factory calibration writes. After START, BODY RGB ON opts into low
brightness RGB game reactions; BODY RGB OFF clears the LEDs and disables the
feature. Sleeping, screen off, unknown battery or <=10% battery clears LEDs.
BODY CHECK reads factory servo/zero_pos_1 and zero_pos_2 read-only and reports
whether calibration is present; it is not proof of safe travel. These commands
are intended for future supervised bench testing only, not factory firmware.
The full game compile requires a clean official BSP checkout at the pinned SHA
in .deps/stackchan-bsp (or STACKCHAN_BSP_DIR). CI checks out that exact commit.
Motor movement is deliberately not implemented until real calibration and
mechanical limits have been checked. No full game binary is published.
