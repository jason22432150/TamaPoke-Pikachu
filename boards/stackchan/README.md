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

## Read-only factory flash archive (before any experimental flash)
Python 3.11+ and esptool 5.x are required. Use a private local directory outside
this repository; flash archives can include Wi-Fi credentials and device secrets.
Disconnect other ESP boards, stop serial monitors, connect K151 via USB and
enter its documented download mode if automatic reset fails. Do not modify eFuses,
use --force, or bypass security restrictions. The tool does not write flash or eFuses.

    python3 -m pip install 'esptool>=5,<6'
    python3 tools/stackchan_backup.py capture --port /dev/cu.usbmodemXXXX --out ~/k151-factory-backup
    python3 tools/stackchan_backup.py verify --out ~/k151-factory-backup

The first command installs the official serial utility in your Python environment
(prefer a virtual environment). Replace the port with the actual USB serial port.
Capture creates a new private directory, records MAC and security/flash reports,
reads exactly 16 MiB twice, and checks sizes, device identity and SHA256. Verify
checks local archives without contacting a device. If reads differ or fail, no
success manifest is created. The chip may remain in the loader until manually
reset; capture does not resume normal firmware between reads. A valid MD5 table
at 0x8000 is only a candidate layout, not proof of factory boot configuration.
The tool does not authorize recovery or flashing. Keep both images and reports
privately on a separate drive; never commit them. eFuses, external SD, and separate
controller firmware are not backed up by this tool. Security settings and actual
partition layout must be reviewed separately, and restoration is device-specific.
No automated restore command is provided until those facts are established.

## Motion preview (no physical output)
After START, BODY MOTION PREVIEW ON enables a serial-only preview for up to 60
seconds if calibration values exist, the game is awake, no menu is open and
battery is 25-100%. BODY MOTION PREVIEW OFF stops it. BODY CHECK reports preview
state. Hatch, eat, heart and evolve transitions generate bounded pose requests
(yaw ±10 degrees, pitch 0–10 degrees, speed <=200), a return to center, and stop.
A six-second cooldown, stale-loop cancellation, screen-off/low-battery/sleep/menu
cancellation and rollover-safe timers are covered by host tests. Play is defined
in the policy for later integration; it is not emitted by the current game hook.
No actual servo power, UART, torque or motion command is implemented. These
software limits are not verified mechanical limits. Physical backend must be
validated against the actual device calibration and travel before any movement.

## Traditional Chinese (TW)
K151 enables LANG_ZH_TW (appended ID 8; existing language IDs unchanged).
The settings language pill cycles to TW. All existing translation IDs, medal
labels and 151 species have Traditional Chinese entries. Original Waveshare
builds keep the original eight languages by default. The font is generated at
build time from the pinned U8g2 upstream GNU Unifont BDF (font license and
copyright are carried in the generated header), selecting all codepoints in
marked translation blocks plus printable ASCII. Generation fails on missing
codepoints or a mismatched glyph count. A clean checkout of the pinned source
at .deps/u8g2 (or U8G2_SOURCE_DIR) is required for the K151 build. CI includes
localization format/persistence/name checks. Readability and text layout on the
physical display still require testing. Nickname input remains ASCII.

## Native landscape side panels
The central 240x240 original game viewport is preserved at x=40..279. The left
40px strip displays battery, charging, SD availability, level and four needs.
The right 40px strip provides Feed, Play, Info, Dex and Settings shortcuts
with 40x44px targets and language-independent compact ASCII labels. Shortcuts
reuse the original game handlers and are disabled during menus, dialogs,
ceremonies, starter selection and other blocked states. A side touch can wake
the screen without triggering an action. Contacts crossing regions are cancelled
until release; a side press must end within one second without changing key.
Host tests cover boundaries, wake-only behavior, state transitions, cross-region
cancellation and timer rollover. This is a native side-panel extension, not a
complete redesign of all central screens. Physical usability is unverified.

## Offline recovery review and compile evidence
After capturing a private factory archive, run:

    python3 tools/stackchan_review.py archive --out ~/k151-factory-backup

This re-verifies hashes, reads captured security reports, compares the actual
candidate partition map to the experimental layout and lists remaining blockers.
It does not connect to hardware or authorize a restore, even if all historical
reports match. No write/erase/eFuse commands are provided.
The full game build validates application/bootloader image magic and size,
compiled partition table MD5 and exact expected entries, then generates a
source-commit-bound SHA256 manifest. CI publishes only that manifest; temporary
binaries are discarded. Neither this evidence nor the diagnostic artifact is
permission to flash. Actual device security, layout and recovery still require
review before preparing an authorized hardware test package.

## Local bench candidate (not flashable or approved)
The optional local build mode retains three validated compiled images and their
SHA256 manifest instead of discarding them. It refuses an existing output
folder and tracked/untracked source changes; CI still exports only evidence.
With the pinned build dependencies already installed and checked out:

    bash tools/build_stackchan_game.sh --local-candidate ~/stackchan-candidate
    python3 tools/stackchan_package.py verify --out ~/stackchan-candidate

The first command builds the game and creates a private local candidate folder;
the second verifies its files offline. Neither writes to a device. This is not a
complete image or installer: OTA selection data and a reviewed write plan are
not included. See BENCH_TEST.md for the hardware acceptance checklist.
