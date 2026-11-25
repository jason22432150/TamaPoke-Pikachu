# StackChan K151 experimental port
This branch is NOT ready to flash. The 16 MiB candidate layout now matches the user-provided read-only K151
partition report. It is not a general factory-compatibility claim. Security
state and exact partition bytes must still be checked on the target unit.
Full factory backup is optional. Factory firmware restoration is outside project scope.
StackChan installation is local USB only, using tools/stackchan_flash.py.
No web installer, browser flashing or Pages deployment is supported for K151.
The installer is currently gated; no factory-compatible release exists.
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
the full game is now published only as an unapproved candidate. Motor/RGB and native widescreen redesign
are outside this target. Do not flash before security/layout review.

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

## Optional read-only factory flash archive
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
Factory restoration is handled externally and will not be implemented here.

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
candidate partition map to the observed K151 layout and lists remaining blockers.
It does not connect to hardware or authorize a restore, even if all historical
reports match. No write/erase/eFuse commands are provided.
The full game build validates application/bootloader image magic and size,
compiled partition table MD5 and exact expected entries, then generates a
source-commit-bound SHA256 manifest. CI publishes only that manifest; temporary
binaries are discarded. Neither this evidence nor the diagnostic artifact is
permission to flash. Actual device security, layout and recovery still require
review before preparing an authorized hardware test package.

## Local bench candidate (not flashable or approved)
The optional local build mode retains three validated compiled images, an erased 8 KiB initial OTA selection image, and their
SHA256 manifest instead of discarding them. It refuses an existing output
folder and tracked/untracked source changes; CI still exports only evidence.
With the pinned build dependencies already installed and checked out:

    bash tools/build_stackchan_game.sh --local-candidate ~/stackchan-candidate
    python3 tools/stackchan_package.py verify --out ~/stackchan-candidate

The first command builds the game and creates a private local candidate folder;
the second verifies its files offline. Neither writes to a device. This is not a
complete image or installer: the initial OTA selection is all 0xff and defaults to ota_0 under the documented ESP-IDF boot rules; a reviewed write plan is not included. See BENCH_TEST.md for the hardware acceptance checklist.

## Same-device read-only preflight
After obtaining the original factory archive, connect the same unit in
download mode and use a new directory for the current snapshot:

    python3 tools/stackchan_preflight.py capture --factory ~/k151-factory-backup --current ~/k151-current-check --port /dev/cu.usbmodemXXXX

This verifies the original before accessing serial, then repeats the full
two-read backup and compares MAC, security flags/crypt count, validated
partition maps and changed 4 KiB sectors per original partition. It never
writes flash/eFuses, and may leave the unit in download mode. Normal factory
operation can change NVS sectors. Differences are not proof of corruption.
Use a new output directory every time; retain the original unchanged.

    python3 tools/stackchan_preflight.py compare --factory ~/k151-factory-backup --current ~/k151-current-check

The second command is offline and compares historical snapshots, not live
state. Reports omit MAC and raw data but should still remain private. A
matching MAC is not cryptographic attestation or proof of K151 hardware.
Both commands always report flash_authorized=false and restore_authorized=false.
Do not use them as a flashing or recovery authorization.

## Read-only servo bus diagnostic
The pinned FTServo_Arduino driver is compiled into the K151 game. After START,
BODY SERVO PROBE requests a one-shot read-only diagnostic of yaw ID 1 and pitch
ID 2 using official UART1 TX6 RX7 at 1 Mbps. Requires the board to be awake,
not in a menu/ceremony, battery 25-100%, motion preview off, UART1 unclaimed,
and successful PY32 reads indicating VM EN is already configured as an output
and its latch is high. The latch is not a physical voltage measurement.
If the rail is off, the request is blocked; this firmware does not enable it.
Only Ping/FeedBack/readByte are used, with no torque, position, EEPROM,
calibration, mode or power writes. UART is closed after the probe. Five-second
rate limit; any transport or invalid-feedback fault latches until reboot.
No periodic probing and no real game motor movement. Raw position, voltage,
temperature, movement and torque are reported, not calibrated measurements.
Requires supervised hardware validation; do not enable external power merely
to bypass a blocked probe. All existing motion preview behavior is retained.

## Servo coordinate preview and register-limit review
The preview now converts tenths of a degree into raw position using BSP 1.1.0
(center + angle * 16 / 50, truncation toward zero). The factory centers are
read only; the entire +/-10 degree yaw and 0..10 degree pitch envelope must
fit the BSP raw range 0..1000 with eight raw units of margin. Out-of-range
requests are rejected rather than clamped. BODY SERVO PROBE additionally reads
the two angle-limit registers from each servo and reports whether the full
software envelope fits those limits and whether current feedback is inside it.
Zero-width/PWM or invalid register limits are blocked for envelope purposes.
A matching register range is not a measured mechanical stop or a motion permit.
The preview uses only BSP bounds, not an authorization from the probe. Neither
command writes position, torque, mode, calibration or power. Actual movement
remains disabled until device-specific mechanical testing and power validation.

## Compile-only actuator execution backend
The new ServoExecutor and ScsOutput classes implement a future supervised
position-write backend. They are compile-checked but **not instantiated or
reachable from the game or serial commands**. No change to existing Preview.
The executor requires a separately verified bench permit, rail, UART ownership,
fresh feedback (250 ms), fixed calibration/register limits, stationary axes
and already enabled torque. It never enables rail/torque or switches mode.
Position writes require unicast ACK; arrival additionally requires fresh
post-command feedback within two raw units and stationary axes, within 1.5 s.
The provisional time-mode command is 1000 ms; it is not a validated speed or
travel guarantee. Failure, changed limits, stale feedback, or revoked guard
attempts torque release on both axes, even after a partial write. The concrete
adapter verifies the torque register after each release. Unconfirmed stop and
fault are latched in the executor; no automatic retry. Acknowledged torque
release does not guarantee physical stop or prevent gravity-induced motion.
Host tests use a fake transport and cover partial writes, stop failure, stale
feedback, timeout, range change and timer rollover. No actual hardware output
is enabled until a separately reviewed interlock, power/torque sequence and
mechanical validation exist.

## Compile-only motor power session
ServoPowerSession and ScsPowerIO are compile-checked, with no game or serial
caller. A future supervised fixture must independently establish exclusive
hardware ownership, actual mechanical safety, physical emergency stop and a
bench permit. The session refuses an unknown or already-on VM EN latch, opens
UART1, rechecks the latch, requests rail on and waits at least 250 ms. It
requires fresh stationary feedback, torque off, valid angle-limit registers,
and existing goal positions exactly matching measured positions before enabling
torque. Both axes are then rechecked. It never writes a new goal or changes
servo mode, GPIO mode, pull settings, EEPROM or NVS. The adapter preserves other
GPIO output bits and verifies readback; latch readback is not proof of voltage.
Fault/stop attempts both torque releases if activation was attempted, then
rail off and UART close; failure latches ShutdownUnconfirmed. The physical
emergency stop remains essential. Host fake-I/O tests cover partial activation,
failed shutdown, stale samples, unsafe initial goal, existing rail ownership,
voltage-latch request failure and timer rollover. Actual power/torque sequence
and mechanical behavior remain unverified, and normal firmware cannot invoke it.

## K151 protected SD uploads
SDWRITE ON remains explicit. PUT now accepts only /mons/001..151.bin, their
s/p/ps variants, and thumbs.bin; decimal size is checked without overflow.
The existing file is not removed before receipt. A .tpk-new file is written,
closed and read back for length, basic format magic and CRC32 equality to the
received stream. Only then is the old file renamed to .tpk-old and the new
file renamed into place. If replacement fails, restoration is attempted only
when the destination is absent; ambiguous failures preserve recovery files.
This is not atomic across power failure on FAT and CRC is not authentication
or full sprite-format validation. If either recovery name exists, the next PUT
refuses to overwrite it. Inspect the SD offline with a separate backup before
renaming or deleting recovery files. No automatic recovery or format at boot.
The original PUT/OK/#/DONE protocol and Waveshare implementation are unchanged.
Host tests exercise path/size validation, CRC, replacement and rollback faults.

## One-reaction bench integration (compile only)
ServoReactionSession combines the power state machine, executor and reaction
poses using a single owned transport. ScsPowerIO exposes the same SCSCL bus
for feedback and output; no second UART owner. The simulated session ignores
pre-existing reactions during power-up, waits for a new event, confirms actual
arrival before issuing the center pose, confirms arrival again, then releases
torque and powers off. One reaction per session; no automatic re-arm. Safety
revocation, lost feedback, partial write, timeout or shutdown failure terminate
the session. No production instance, serial command or physical output is
added. Preview additionally blocks during feed selection, bath and decision/
release dialogs. Host integration tests use the same fake power/output bus.
This does not replace a physical stop, independent watchdog or device-specific
bench verification.

## Opt-in runtime performance telemetry
After START on a separately approved test installation, send PERF ON to enable
five-second windows, PERF? for an immediate report (memory only if disabled),
and PERF OFF to stop. PERF_TIME counts actual central framebuffer flush calls,
reports achieved FPS in thousandths, render-call/flush/loop-start-gap mean and
maximum microseconds, and gaps >=100 ms. Render includes its flush, so do not
add them. The sidebar is not counted as a central frame. Loop gaps include idle,
serial, storage, rendering and logging; neither loop timing nor CPU MHz is CPU
utilization. PERF_MEM reports current heap, boot minimum heap, largest internal
8-bit allocation, free/total PSRAM, largest PSRAM allocation, reset reason and
CPU MHz. Both records share a sequence number; USB CDC may drop records.
Logging is off by default, uses fixed-size counters, and does not write SD/NVS.
Screen-off/dim/game flags are snapshots at report time, not per-frame labels.
Capture a serial log for normal play and idle phases; do not interpret low FPS
while dimmed/asleep as a rendering failure. Host tests cover window resets,
rollover, zero frames, disabled mode and wide accumulators. Physical speed,
memory stability and CPU utilization remain unmeasured.

## Offline soak log analysis
Capture the USB serial text during separately approved bench use with PERF ON.
The offline analyzer needs no serial library or device connection:

    python3 tools/stackchan_perf_report.py ~/k151-soak.log --minutes 60 --out ~/k151-soak-report.json

This validates record fields, pairs TIME/MEM by sequence, identifies gaps,
truncated records, duplicate records and possible reboot/session boundaries,
and reports observed duration, phase-separated FPS, maximum timing and memory
statistics. Existing output files are not overwritten. Add --strict to return
exit status 2 when telemetry requires review. The default decline flags are
32 KiB heap / 256 KiB PSRAM drops between first and last fifth medians (minimum
10 records); these are investigation thresholds, not proven memory leaks.
Largest-free-block decline also merits review. Different workloads and cached
sprites can legitimately change allocations. Compare repeated equal workloads.
Boot markers and uptime/sequence discontinuities are evidence, not definitive
reset detection; dropped logs can hide resets. Phase labels are end-of-window
snapshots. Telemetry criteria met never implies hardware acceptance, and no
actual K151 log has been analyzed in CI. Tests use synthetic data only.

## Offline merged image review

After verifying a local candidate, create and verify a separate merged prefix:

    python3 tools/stackchan_merge.py create --candidate ~/stackchan-candidate --out ~/stackchan-merged-review
    python3 tools/stackchan_merge.py verify --candidate ~/stackchan-candidate --out ~/stackchan-merged-review

The first command creates a new directory with a sector-aligned merged binary and region/hash manifest. The second reconstructs and compares the bytes. Neither accesses hardware. This is not a full 16 MiB image, migration, or restore image. Gaps are filled with 0xff, including NVS; writing the prefix can destroy original settings and calibration. Never treat this output as an approved flash plan. CI tests synthetic inputs; real-device recovery is still unresolved.

## Offline partition impact review

    python3 tools/stackchan_impact.py --factory ~/k151-factory-backup --current ~/k151-current-check --candidate ~/stackchan-candidate --report ~/k151-impact.json

This compares two verified historical captures of the same MAC and a validated candidate. It reports estimated sector erase overlaps for separate images and the merged prefix against the current partition map, and marks changed partition layouts even when their bytes would not be erased. It never connects to a device, emits write commands, migrates NVS or establishes calibration location. A zero-overlap result is not proof of data preservation after boot. Unknown partition maps block interpretation. Keep all archives private; this report is not a flash or restore authorization.

## Deployment scope and eFuse invariant
Factory restoration, restoration testing and restoration instructions are outside project scope. Existing read-only archive tools remain optional. Historical review reports do not authorize writes. No eFuse programming, secure boot provisioning, flash encryption provisioning, eFuse anti-rollback or forced flashing is permitted. Check the actual build configuration and bootloader provenance, and compare read-only eFuse summaries before and after flashing and first boot. A passing compile or static check is not proof that hardware eFuses remain unchanged.

## Alpha 0.1.0 local USB candidate installation

The observed K151 layout reserves NVS at 0x9000 (16 KiB), OTA data at
0xd000, PHY init at 0xf000, ota_0 at 0x20000 and ota_1 at 0x510000,
assets at 0xa00000 and coredump at 0xe00000. The installer preserves the
existing partition table, requires exact matching bytes, and writes only
bootloader, OTA selection, ota_0 and the full 4 MiB TamaPoke assets image
when a build is independently approved. All original assets will be replaced;
keeping ota_1 does not guarantee original firmware functionality. The raw
TPAS-v1 archive has 22 normal/shiny animations (11 species) plus all gallery
thumbnails, and is read-only at runtime. microSD retains full sprite support.
Use ASSETINFO after START to report the internal archive header status.
Do not use old experimental-layout artifacts or merged images for installation.

See [ALPHA_INSTALL.md](ALPHA_INSTALL.md) for macOS preparation and read-only
bench preflight. CI now requests a separated candidate artifact explicitly
labeled NOT-FOR-FLASH. The build re-converts the selected SDK bootloader ELF
and records SDK/ELF/BIN hashes; this does not attest the actual bootloader
configuration. The installer has an empty audited-build allowlist and rejects
all installs before connecting to hardware. No override is supported.
