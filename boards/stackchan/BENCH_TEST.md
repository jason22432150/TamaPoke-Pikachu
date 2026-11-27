# K151 bench acceptance checklist (not a flash guide)

Status: PARTIAL HARDWARE ACCEPTANCE. A green CI is not hardware acceptance.

## Recorded owner reports (2026-11-25)

Exact installed candidate: 871e6d8851c6b7348bbf5a0d71a80affa10e1e32,
build run 45581224571, paired artifact 15007091688.
Installer approval commit 111ee286ab7350821f7ce8062d673c243c1416d3.

- PASS: ROM-only Flash write and readback; original partition table byte match.
- PASS (owner report): GDMA fix, basic boot to START screen, PSRAM check and
  board/display/touch initialization. Full LCD and touch functional tests remain.
- PASS (owner report): pre-write, post-write and pre-START boot eFuse named
  observable fields unchanged; zero unreadable named fields. Reserved bits are
  not proved unchanged.
- PASS (owner report): BODY CALIBRATION, START, BODY CHECK returned expected
  results. Actual raw calibration values were not supplied, and comparison
  against independent factory reference is NOT RUN.
- PASS (owner report): calibration read yaw=460 pitch=620, present-unverified,
  motor=disabled; independent factory reference comparison remains NOT RUN.
- PASS (read only): TIME returned rtc=1795602941 (2026-11-25 10:35:41 UTC).
  Clock accuracy, set and reboot retention remain unverified.
- Single PERF? sample: uptime 2120771 ms, heap 296688, minimum 296028,
  largest internal block 253940, free PSRAM 7943376 / 8388608,
  largest PSRAM block 7864308, CPU 240 MHz, reset 11 (ESP_RST_USB).
  This is not a continuous stability or leak test.
- PASS (owner report): TeamGroup 16 GB FAT32 microSD installed and normal
  boot confirmed. Initial no-boot report was withdrawn by owner as an
  operator mistake, not a reproduced firmware defect. SDINFO returned
  total=15921446912 used=8192; LS returned DONE without entries.
  Mount/capacity read passed; empty or absent /mons directory is expected
  on an unprovisioned card. Actual file reads and sprite loading remain
  NOT RUN. No format or firmware update needed.
- RGB ON request accepted, BODY CHECK rgb=1. Visible LED output, transitions
  and RGB OFF remain unverified.
- Motion preview OFF acknowledged, prior BODY CHECK preview=0 active=0
  hardware=disabled. Preview ON and reaction behavior remain NOT RUN.
- Preliminary telemetry (owner report, 2026-11-26): 73 paired windows,
  coverage 368640 ms, one boot marker, no malformed, missing, duplicate
  or unmatched records; reset reason 11 (ESP_RST_USB). Heap median
  drop 4 bytes, PSRAM and largest-block median drops zero. No memory
  decline review flags. Active/game/dim FPS 7.20/11.61/2.00; active
  maximum loop gap 601026 us, 1632 gaps >=100 ms; game 29, dim 30.
  Active max render 133853 us includes flush (max 32127 us).
  No off-screen windows. Report is review-required solely for duration;
  60-minute continuous telemetry is explicitly waived by the owner (not PASS);
  visual acceptance remains outstanding.
  Do not infer a specific cause for the maximum loop gap from aggregates.
- NOT RUN or not yet reported: detailed gameplay, all UI screens, audio,
  RTC retention, SD sprite reads, RGB visual behavior, persistence, motion preview ON,
  final post-game eFuse comparison. The owner explicitly waived the 60-minute
  stability requirement for this Alpha; long-duration stability remains unverified.
  Physical motors remain disabled.

Preserve this exact installed firmware while testing. A fresh CI artifact is
not automatically approved.

## Next acceptance sequence

1. Exercise the current no-SD game, touch targets, LCD, language, sound and
   normal battery/charging indications. Record failures without enabling motors.
2. Check TIME (read only), save state and normal reboot/START; compare game
   state and calibration. Check SD using a suitable card and SDINFO; no format.
3. Explicitly test BODY RGB ON/OFF. Motion preview is optional until the
   pet is awake and calibrated; BODY MOTION PREVIEW ON/OFF and BODY CHECK
   must keep hardware=disabled. Do not enable motor power or a servo probe.
4. SKIPPED BY OWNER: continuous 60-minute PERF ON session. Retain the
   preliminary 368640 ms report; do not lower the report threshold or label
   it a full soak pass. Continue other acceptance checks.
5. After testing, enter ROM download mode and capture a new independent
   eFuse snapshot; compare against the original installation before snapshot
   and pre-START after-boot snapshot. Do not overwrite existing checkpoints.
6. Review all acceptance rows and unresolved failures before tagging Alpha.

## UI work (owner selected option B; explicitly started before remaining Alpha acceptance)

The owner requested starting UI work now. Outstanding Alpha tests remain
unverified; the currently installed candidate is unchanged. Start StackChan-specific rectangular
320x240 landscape adaptation: top status bar, bottom action bar, aspect-ratio
preserving pet scene, shared touch/render geometry, followed by settings,
gallery and minigames. Keep Waveshare circular UI, existing game saves,
factory Assets and partition table, eFuse policy, physical motor/OTA restrictions.
B1-B6 CI passed. B6 exact candidate 01266e011f68e7e4c78c093efb0d4f882b70ee45,
build 45675596329, paired artifact 15051602699 (NOT-FOR-FLASH metadata retained).
Audit 45726785560, artifact 15074463917: 11 fixed hashes verified; seven boot
and ten app known MMIO load sites, 10/34 extracted symbol ranges. Review
of known direct base references found chip/version/encryption/calibration
reads; rtc_init stores target RTC/system/SPI registers or RAM, and calls
the RTC calibration helpers. Named read helpers read registers and fill RAM.
No known linked writer symbol or direct/literal ROM writer reference was
reported. SDK config hashes match previously reviewed settings. This is
bounded evidence, not proof of all computed/indirect paths or reserved bits.
Exact tuple is added to the installer gate for supervised ROM-only installation.
Do not install a new build from the audit or approval commit. Old approved
DMA-fix tuple remains available for supervised recovery. Hardware acceptance
of B6 is partial: owner reported successful ROM-only write/readback on
2026-11-26, named eFuse comparison unchanged, zero unreadable named fields
before and after write. Owner subsequently supplied the after-boot report
(status observable-summary-unchanged, after_write and after_boot both
changed_fields=[], unreadable_before=0, unreadable_after=0). Named eFuse
checkpoint comparison PASS (owner report, 2026-11-26); the tool cannot establish
boot ordering independently.
Owner serial evidence after START (2026-11-26, candidate 01266e0):
- Game startup PASS; saved species 4, level 15, bond 51, medals 0x8;
  406 minutes of offline progression reported. Save retention across a new
  controlled reboot and RTC correctness still need independent verification.
- SD mounted, total 15921446912 bytes, used 43073536 bytes; 151 thumbnails
  loaded (165 KB), PMD /mons/p004.bin loaded (110 KB). SD asset read PASS.
  HEALTH mon=1 while STATS mon=0 is consistent with the former reporting
  pmd.loaded || mon.loaded and the latter legacy fallback mon.loaded only.
- LCD cache=1 dirty=1 frames=175 unchanged=0 rects=1564 pixels=703360
  full_pixels=8960000: 92.15% fewer viewport pixels versus full refresh,
  not an elapsed-time or FPS measurement; visual fidelity remains unverified.
- Owner FULL/DIRTY telemetry (2026-11-26, same candidate):
  FULL LCD frames=363 unchanged=0 rects=7260 pixels=18585600
  full_pixels=18585600 (51200 pixels/frame).
  DIRTY LCD frames=180 unchanged=105 rects=502 pixels=182272
  full_pixels=9216000 (1012.62 pixels/frame; 98.0222% fewer viewport
  pixels relative to full refresh, 58.33% no-transfer logical frames).
  The counters represent each reset-to-LCD? interval, not synchronized
  with PERF windows. PERF FULL seq 1-10: 47163 ms, 364 frames, off=0
  dim=0 game=0, frame-weighted flush mean 23589.7 us, mean of window
  render means 34133.8 us. First 3 windows 15001 ms/150 frames
  (9.999 FPS). Subsequent idle/calm windows reduced scheduled rate.
  DIRTY seq 11-19: 44569 ms, 177 frames, off=0 dim=1 game=0,
  frame-weighted flush mean 10920.6 us, mean of window render means
  21899.3 us. Observed flush reduction 53.7%, render reduction 35.8%,
  but no causal speedup/FPS claim: power states and animation workloads
  differ. FULL two slow loop gaps (max 1321061 us); DIRTY one
  (216060 us). The incomplete/invalid PERF?' input coincided with
  a long gap; blocking readStringUntil is a plausible contributor,
  not established by aggregate timing. Free heap constant within
  each mode (294452/295316), PSRAM constant 7862504 throughout.
  PASS for observed transfer savings and basic dirty-mode counters;
  matched awake A/B and visual fidelity still NOT RUN.
  Repeat with real touch to reset idle before each short test, compare
  off=0 dim=0 game=0 and the first 15 seconds, same pet and screen.
  Do not disable safety/power behavior or repeat the waived soak.
- Second owner A/B run, candidate 01266e0, matched awake power flags
  (off=0 dim=0 game=0), same nominal 100 ms frame interval:
  FULL seq 20-22: 15001 ms / 150 frames, average render 34084.33 us,
  flush 23523.33 us, loop 1733 us. DIRTY seq 24-26: 15001 ms /
  150 frames, average render 21633 us, flush 10914 us, loop 1415 us
  (arithmetic means of three 5-second windows, 50 frames each;
  loop mean is an unweighted mean of window loop means). Render
  36.53% lower, flush 53.60% lower, loop mean 18.35% lower; both
  approximately 10 FPS, zero slow loops, including tail windows 23/27.
  Maximum loop gap FULL 36262 us, DIRTY 42367 us (initial full
  invalidation is a possible contributor, not independently traced).
  FULL LCD frames=182 unchanged=0 rects=3640 pixels=9318400
  full_pixels=9318400. DIRTY frames=170 unchanged=118 rects=334
  pixels=159488 full_pixels=8704000: 98.1676% fewer viewport pixels
  per frame versus full refresh, 69.41% zero-transfer frames.
  LCD intervals differ from PERF windows; animation sequence not
  controlled exactly. PASS matched power-state short A/B telemetry;
  no visual fidelity or general worst-case speedup claim.
  Free heap 294164/295028 and PSRAM 7813352 stable within the
  respective windows; PSRAM is 49152 bytes below previous sample
  after ~24 minutes and intervening workload; not evidence of a leak.
  Existing 60-minute soak waiver remains; physical UI acceptance pending.

- PERF_MEM at 48927 ms: heap 295316, minimum 290784, largest 249844;
  PSRAM 7862504/8388608 free, largest 7733236; reset 11, CPU 240 MHz.
  Single sample, not leak or stability evidence.
- TIME rtc=1795597402. Existing game clock uses local wall time encoded
  as an epoch; this decodes to 2026-11-25 09:03:22 on that convention,
  apparently one day behind the owner's 2026-11-26 morning session.
  Confirm actual host/RTC wall time before changing clock; no correction
  performed or inferred from offline progression alone.
- BODY CALIBRATION yaw=460 pitch=620 valid=1 envelope=1; BODY CHECK
  rgb=0 calibration=present-unverified motor=disabled, preview=0 active=0
  hardware=disabled. Matches previous reported values; independent factory
  calibration comparison still outstanding.
Physical display, touch, detailed gameplay, persistence after reboot and
post-game eFuse comparison remain unverified. Original owner waiver of
60-minute soak stands.
After installation compare named eFuse fields before, after write, and after
first boot; validate all landscape screens and LCD FULL/DIRTY counters.
No motor, partition or NVS schema changes are authorized.

## B8 interaction candidate (supervised hardware acceptance pending)
Exact source a3e4428e7f82ed450450a45c8550dc701de4e48b, build 45824080265
(all six jobs passed), paired artifact 15119962441 (NOT-FOR-FLASH metadata
retained). Fixed ELF audit 45826383469, artifact 15119928548: all 11
pinned hashes passed, 7/10 known boot/app MMIO reference sites located,
10/34 extracted symbol ranges. No known linked writer symbol or known
direct/literal ROM writer reference. Compared emitted function listings
to B6 audit 45726785560: boot instruction listings match after address
normalization; app function sets and read paths retained. rtc_init
instruction operands and resolved peripheral targets match after
literal-pool address relocation normalization; calibration helper
differences reflect literal relocation and logging strings. The long
range labeled esp_efuse_is_flash_encryption_enabled-0xe60 is a
pre-function data/literal region interpreted as instructions, not a
verified executable function. Bounded evidence only, no proof of
all indirect paths or protected/reserved bits. Exact tuple authorized
for supervised ROM-only installation, not any rebuild. B6 and DMA-fix
tuples retained. New I2C head sensor and RGB behavior, parser latency
and visual behavior remain physically unverified. No new servo output
or eFuse programming is intended. Require after-write and first-boot
named eFuse comparisons before START; then test SERIAL?, fragmented
PERF?, HEAD? / HEAD OFF / HEAD ON, BODY RGB TEST / AUTO / OFF,
and combined PERF telemetry. Existing blocking SD PUT handler is not
part of non-blocking parser acceptance. No change to NVS schema or
partition layout; RTC issue not yet fixed.

Owner-reported installation and checkpoint evidence (2026-11-26): exact B8
candidate installed with the allowlisted installer; write-verified.json reports
observable-summary-unchanged, changed_fields=[], unreadable_before=0 and
unreadable_after=0. The after-boot command reports the same for both
comparisons and overall observable-summary-unchanged. Named eFuse checkpoint
comparison PASS (owner report); protected/reserved bits and boot ordering
are not independently established. B8 START, gameplay, head touch and RGB optical output subsequently reported
normal by owner (2026-11-26); owner reports all B8 interactive checks normal.
Raw counters and combined performance logs were not supplied, and fragmented
serial input is not explicitly confirmed. Detailed UI, RTC retention and final
post-game eFuse checks remain outstanding. Preserve installed candidate for
these tests.

B8 owner telemetry (2026-11-26): TIME values 1795643880 and 1795643936
advance 56 seconds, encoding 2026-11-25 21:58:00 and 21:58:56 as local
wall time. Suspected calendar offset persists; host time at sampling not
provided, hardware versus software RTC source and retention unverified.
PERF seq 56–66, dim=1/off=0/game=0: 11 windows around 5 seconds, 20 frames
per window (~3.99 FPS), zero slow loops; heap 294840, min 290312, PSRAM
7813352 and largest PSRAM 7733236 unchanged. Short sample only. Next check
explicit local-wall-time correction via TIME (rebases saved game clock
without offline progression), then compare RTC after controlled reboot.
No firmware change or new Flash installation required for this check.
Owner subsequently reported RTC correction/reboot test passed (2026-11-26);
raw clock comparison not supplied. Owner reported repeated head touch events,
then reported follow-up tests passed and issue no longer present. Cause not
established; no head sensor policy change. Reopen if reproduced.

## B10 adjustable render cap (candidate, hardware pending)
K151-only FPS? and FPS 5/10/15/20/30 commands, RAM-only default 10.
Power-saving limits and 85 ms mini-game cadence retained. Verify active
PERF windows, wake and dim behavior, gameplay and invalid command handling.
Actual FPS depends on rendering cost; 30 is a requested cap, not a guarantee.
Exact candidate 54d9a27d2e735ba8b051aaa44aed9de79096a97b, build run
45838322365 (six jobs passed), paired artifact 15127363086. Fixed ELF audit
45839829181, artifact 15128210548, passed all 11 pinned file hashes and
located all 7 boot / 10 app known reference sites in 10 / 34 extracted
ranges. No known linked eFuse writer or explicit ROM writer reference.
Compared full emitted reference ranges against B8 audit 45826383469:
boot listings identical after address normalization; app range names match.
Apart from the pre-function data/literal region disassembled as instructions,
changed executable listings retain instruction count and differ only in l32r
literal-pool relocation or resolved log/assert string addresses. Named
read helpers, callback targets, eFuse register targets and init paths retained.
SDK configs, partition and OTA-data hashes unchanged. This is bounded static
evidence, not a proof of all indirect/computed paths, ROM behavior or protected
bits. Exact tuple only added to installer allowlist for supervised ROM-only
installation; no rebuild authorized. B8 retained for recovery. Require all
three eFuse checkpoints and verify FPS, wake, gameplay, LCD visual behavior
and invalid-command handling on hardware. Do not enable motor or OTA.

Owner-reported B10 installation checkpoints (2026-11-26): write-verified.json
and after-boot overall status observable-summary-unchanged; both comparisons
changed_fields=[], unreadable_before=0, unreadable_after=0. Named observable
checkpoint comparison PASS (owner report). One malformed duplicate command
was rejected by argparse; subsequent after-boot succeeded. Boot ordering and
protected/reserved bits are not independently proven. FPS behavior, dim/wake,
minigames, reboot default and post-game checkpoint remain pending.

Owner B10 FPS serial telemetry: 23 windows, 115093 ms total, zero slow
loops (>=100 ms), heap 294840/min 290312/largest 249844 and PSRAM
7813352/largest 7733236 unchanged across windows. Stable-window aggregate
(target, seq, frames, ms, actual FPS, frame-weighted render/flush ms):
- 5: 1-5, 125, 25002, 5.000, 22.083/11.035.
- 10: 6-11, 299, 30040, 9.953, 22.341/11.231.
- 15: 12-15, 299, 20038, 14.922, 22.269/11.183.
- 20: 16-17, 198, 10001, 19.798, 21.946/10.925.
- 30: 21-23, 432, 15004, 28.792, 21.619/10.679.
Seq 18-20 excluded from stable comparison: 20 target transitions to 10.797,
30 target reports idle interval 150 ms and 6.598 FPS, then 17.578 and
28.776 after interaction; consistent with calm-stage/wake policy (dim=0).
No proof of actual LCD panel refresh cadence; PERF counts central flush calls.
LCD RESET confirmed but final LCD counters not supplied. Explicit invalid
FPS value/preserved setting, 90s dim, screen off, visual/touch acceptance,
minigames, reboot default and final eFuse checkpoints still pending.
Head/RGB disable acknowledged. Keep 10 FPS default pending broader tests;
20 FPS is a practical responsiveness candidate, 30 experimental. Short
telemetry does not establish battery life, thermal or long-duration stability.
Owner subsequently reported all seven remaining B10 interactive acceptance
checks PASS: no flicker/corruption and normal touch at 30 FPS, 90s dim ~4 FPS,
central rendering stops with screen off, minigames normal, reboot default 10,
and FPS 60 rejected without changing selection. No additional raw logs supplied.
B10 feature acceptance complete; final post-game eFuse checkpoint remains pending.

## B11a touch FPS settings (candidate)
Add a fourth setting pill alongside VOL/BRI/LANG in Clock settings. Tap
cycles 10 -> 15 -> 20 -> 30 -> 5 -> 10, applies immediately, RAM-only.
Shared rectangles and host tests cover all ten controls, physical mapping,
non-overlap and gaps. Static-screen cache key includes target FPS so Serial
and touch selections remain synchronized. OK applies clock as before; X
closes without applying clock edits, but does not undo live FPS settings.
No new NVS keys, display transfer changes or motor output. Exact binary
review and hardware acceptance required before installation.
B11a CI 45848141028: all six jobs PASS.

## B11b precise active cadence (candidate)
K151 awake/non-idle/non-low-battery main rendering uses microsecond cadence
(ceil 1000000/fps) with at most 2 ms polling jitter compensation. A long stall
rebases the schedule; no catch-up batch. Legacy game, sleep, idle, low battery
and Waveshare paths retain millisecond policy. FPS? adds interval_us and
precise=0/1, cap_milli reports selected nominal cap in precise mode. Unit tests
cover jitter, long stalls, wrap and mode transitions. Actual FPS, touch and
LCD behavior require new candidate review and hardware verification.
B11b CI 45851088154: PASS.

## B11c dirty-strip work reduction (candidate)
Preserve exact B10 dirty span and synchronous strip transfer semantics.
Compare equal 64-pixel edge groups before the original 16-pixel tile walk;
keep whole-strip equality fast path. Pack full-width strips contiguously;
update the shadow only for the transmitted span, from internal RAM staging.
No new allocation or DMA, no changed rectangle count or geometry intended.
Host regression compares against legacy spans across 11 widths and all 8
strip heights, randomized sequences, forced full frames and buffer guards.
Actual PSRAM/cache and flush savings are not measured yet; benchmark on K151
with identical scene, FPS, dirty/full settings. Exact binary review required.
B11c CI 45853402747: PASS.

## B11d opt-in LCD phase timing (candidate)
PERF DETAIL ON/OFF/? enables phase instrumentation separately from PERF ON.
Changing detail mode resets the active sampling window. PERF_LCD reports
per-central-flush average/max compare, pack, transfer (including transaction
open/close), shadow, residual average, pixels, rectangles, shadow bytes and
unchanged/full counts. Zero-work stages are included in averages; no extra
per-strip timer reads when detail is off. Transfer is time inside driver
calls, not a measurement of wire activity; instrumentation adds overhead.
Sidebar transfers are outside these counts. Compare ordinary PERF and detail
runs on identical scenes. Host tests cover reset, disabled mode, empty/full
flushes, phase accounting and residual saturation. Exact audit pending.
B11d CI 45855869906: PASS.

## B11e adaptive cached touch routing (candidate)
Active awake UI at target 20/30 FPS routes M5 cached samples every 10 ms
instead of 20 ms. Other UI states and minigames retain 20/10 ms respectively.
M5.update remains once per loop; no parallel I2C, extra sensor reads or
changes to gesture thresholds, touch ownership or stale-page guards.
PERF DETAIL adds PERF_TOUCH with sampled route gaps, pressed samples,
observed press/release edges and stale-page sample count. Initial sample
establishes baseline; intervals across windows counted in following window.
Not sensor interrupt latency or end-to-end response. Synchronous render can
still block routing; hardware latency comparison and exact audit pending.
B11e CI 45858977841: PASS.

## B11f bounded cooperative idle yield (candidate)
K151 battery-only calm (>60s) loops yield at most 4ms, screen-off at most 5ms;
cap by time remaining to next legacy render. Active, game, USB, charging,
held cached touch, audio and pending/discarding serial remain on 1ms path.
No MCU sleep, clock change, I2C update duplication or power/save policy
change. Tests cover input/activity overrides and frame deadline. Validate
battery-mode wake, dim, RGB/head interaction, audio and power button. USB
telemetry does not measure battery-only yield savings; external measurement
needed for power claims. Exact combined candidate audit pending.
B11f integrated CI 45861451180: all six jobs PASS.

## B11 integrated fixed candidate audit and supervised install gate
Exact source 0bb39e5292d712007612b248ac005dac1bfc558b, build 45861451180,
paired artifact 15139620479 (ZIP sha256 728b34a56896d5e1dd3eeb284b101d8a84fb0a39e0830449f9986b874df2ceb2).
Audit 45864574356, artifact 15140705649, ZIP sha256
2321ccbe7c9eb61ee795854513521207e2aefc9f400a62f65defd1fbec5ad34e.
All 11 pinned hashes verified, known MMIO reference sites 7 boot/10 app,
extracted ranges 10/34, matching B10 audit 45839829181. No known linked
writer or explicit ROM writer references. Compared complete emitted ranges:
boot instructions match after location normalization; all 34 app range names
match. One pre-function literal/data range differs (1486 vs 1481 decoded
lines); remaining 33 executable listings have matching instruction counts.
Differences are location/literal-pool relocation, including 43 resolved
relocated RAM/flash addresses for named helpers, data and log/assert strings;
resolved MMIO addresses and non-address immediates in compared functions
match. The pre-function region is not fully interpreted. SDK config, partition
and OTA data hashes match B10. Source comparison limited to UI, cadence,
dirty strips, telemetry, touch, cooperative yield, tests and docs/tool gates;
no eFuse configuration changes. This bounded review cannot exclude all
indirect/computed paths, ROM behavior or protected/reserved bit changes.
Only the exact B11 tuple is added to the supervised ROM-only install allowlist;
retain B10. No rebuild, force, motor, OTA, partition or assets writes.
Require whitelist CI success before install; pre/write/first boot observable
checkpoints and B11 interactive acceptance remain pending. Do not claim
B10 final post-game eFuse comparison was performed; it remains unrecorded.

Owner-reported hardware checkpoints (2026-11-27): B11 read-only probe
passed, partition table read completed; B10 before versus B11 preflight
before comparison reports observable-summary-unchanged, changed_fields=[],
unreadable_before=0, unreadable_after=0. B10 final observable checkpoint
PASS (owner report). B11 write-verified.json and after-boot overall and
individual comparisons report observable-summary-unchanged, no changed
fields and zero unreadable fields before/after. B11 supervised install and
first-boot observable checkpoints PASS (owner report). Whitelist CI
45869023259 all six jobs passed. Snapshot ordering and physical boot history
remain operator evidence; no claim about protected/reserved bits. B11k
performance, UI, battery wake, save/RTC and final post-game checkpoints
remain pending. No new firmware required for these tests.

## B11l standalone startup (candidate)
Owner reported B11 cannot start after a battery-only power cycle without a
Serial host. B11l adds a 3-second auto-start menu, touch START GAME and
DIAGNOSTIC MODE; any contact pauses auto-start, held-at-entry and drag-out
contacts cannot start. Serial START retained; DIAG/BODY CALIBRATION pauses.
No game NVS/SD access while paused; existing hardware and NVS guard checks
unchanged. No new NVS key, motor/OTA/eFuse write or partition change. Unit
policy tests cover countdown, wrap, held touch, drag-out, serial and deadline
priority. For the next supervised first boot, select diagnostic within the
countdown, confirm paused, then reenter ROM. If missed, record game startup
rather than claiming pre-game evidence. Battery-only cold boot, manual start,
paused diagnosis, retained save, SD and exact binary review pending. B11k
performance evidence may be collected on the new audited candidate; record
source version explicitly.

B11l CI 45931554248: all six jobs PASS. Exact source
e21c476b278544793f9ecd56ff770c0f30cae1f8, paired artifact 15168714645,
ZIP SHA256 22e962128a0fb46c376cf164d62cbc9a69e9fecb71aad995080663fa3bff98df.
Fixed ELF audit 45933053881 PASS, artifact 15169552021, ZIP SHA256
5ea7dd51cd0deb6ff5c364aed94f467b041ea4bd71e5cb8ee63e40888107ff89.
All 11 pinned hashes pass; known references 7 boot / 10 app; extracted
ranges 10 / 34. No known linked writer or explicit ROM writer reference.
Compared emitted listings to B11 audit 45864574356: boot instruction
listings match after location normalization; all 34 app range names match.
33 executable ranges have matching instruction counts, with no unexpected
instruction/operand differences after relocation normalization. 40 resolved
RAM/flash literal relocations, including named helpers, data and log strings;
MMIO targets and non-address immediates match in compared functions. One
pre-function data/literal range differs (1481 vs 1483 decoded lines), not
fully interpreted. SDK config, partition and OTA data hashes match B11.
Bounded static comparison cannot prove all indirect paths, ROM behavior or
protected/reserved bits. Only exact standalone tuple added to supervised
ROM-only install allowlist; retain B11. Require whitelist CI PASS before
installation. First boot explicitly pause countdown with DIAGNOSTIC MODE,
verify paused before returning to ROM; if missed record game initialization.
Do not claim pre-game checkpoint unless observed. B11 final post-game
checkpoint still pending; compare B11 before to B11l preflight before write.

## Before any write
- Record K151 hardware revision, factory firmware version, USB port and power source.
- Optional: capture and verify two full factory reads using stackchan_backup.py. Store privately. Factory restoration is outside project scope.
- Review current security and partition layout. If optional archives exist, use stackchan_preflight.py to compare them.
- Independently confirm original calibration values before enabling motion.
- Verify the candidate manifest, commit, toolchain pins and all hashes.
- Do not proceed if secure boot/encryption or layout are unresolved.
- Candidate includes an erased initial OTA selection image; deployment still requires a reviewed write plan.
- Never program eFuses, enable secure boot, flash encryption or eFuse anti-rollback. Compare read-only eFuse summaries before and after installation and first boot.
- No experimental write is authorized by this checklist.

## After a separately reviewed installation
Record commit/hash, test timestamp and PASS/FAIL/NOT RUN for every row.
Do not include credentials, MAC or private flash images in public issues.

| Area | Acceptance |
| --- | --- |
| Boot | Correct board, 16 MiB flash, 8 MiB PSRAM, 320x240; no reset loop |
| Calibration | Before START, BODY CALIBRATION reports signed NVS centers without writes or motor output; compare with independently recorded factory values; missing values block motion |
| START | B11 and earlier: explicit Serial START; B11l: standalone auto/touch/Serial start after guard checks, diagnostic pause before game namespace and SD access |
| LCD | Correct red/green/blue, orientation and full viewport, no tearing |
| Touch | All four center corners; all five side buttons; crossing cancels; wake-only |
| Game | Starter, egg, feed, bath, light, play, strength, evolution, farewell |
| Assets | Pikachu/Raichu normal and shiny fallback; SD sprites when present |
| Languages | All nine; TW names, menus, medals, no missing glyph or clipped text |
| Audio | All cues, volume, mute, sleeping and wake |
| RTC | Time read, time set, reboot persistence and offline progression |
| SD | Read without format; opt-in write only; safe removal and recovery |
| Power | Battery percent, charging, dim, wake, controlled low-battery behavior |
| RGB | Explicit ON/OFF; pet transitions, sleep and low battery clear |
| Motion | Preview only; no physical motion, calibration unchanged; BODY SERVO PROBE blocks if rail off and reports read-only feedback only if preconditions hold |
| Persistence | Game state and language survive reboot; original calibration unchanged |
| Stability (waived by owner; not PASS) | 60-minute normal play with PERF ON; capture paired PERF_TIME/PERF_MEM records, compare active vs idle FPS, min/largest heap, PSRAM and reset reason; PERF OFF afterwards |
| eFuse | Read-only before/after summaries unchanged, including after first boot |

Stop on abnormal heat, unintended motion, power faults, resets or display corruption.
Do not deliberately discharge a lithium battery below safe limits to test shutdown.

Analyze the captured log with tools/stackchan_perf_report.py --minutes 60.
Review all data-quality and memory-decline flags; repeat an identical workload
before diagnosing a leak. A clean report cannot replace the checklist.


## B11m battery-only cold-start blocker (owner report, 2026-11-27)
USB cold start succeeds; unplugging USB after entering the game permits normal
battery play; battery-only cold start produces a brief white backlight flash
and no UI; displayed battery 80–100%. Treat as release blocker. Installed
source commit and exact B11l installation checkpoints not supplied with this
report. No evidence yet of actual failing boot stage or voltage transient.
The application's BatMonitor requires >=30s boot grace, >=30s sustained low
voltage and >=3 readings; immediate failure is inconsistent with that path.
Pinned M5Unified 0.2.20 Power_Class.cpp:332–337 unconditionally asserts
AW9523 P1_7 BOOST_EN during CoreS3/SE/StackChan Power.begin; M5Unified::_begin
then calls setExtOutput(cfg.output_power), default true. Pinned M5GFX 0.2.26
M5GFX.cpp:1500–1505 can assert BOOST_EN even earlier during board detection
when SPI pullups are absent. Official StackChan reference commit
28b9f0c8bd6acd81cb3c70f1a93c3e373b39d400 stackchan.cc:218–229 also asserts it
in the AW9523 initializer. Independent analogous K151 report:
https://zenn.dev/maruhana/articles/stackchan-battery-boot-debug
reports success with boost precharge, not measurement on owner's unit.
M5Unified 0.2.22 output-switch fixes do not remove unconditional startup
BOOST_EN, so a dependency upgrade or output_power=false alone is insufficient
as a verified solution. Investigate both earliest assertion sites and safe
rail sequencing, preserve unrelated expander bits and hardware protections,
no servo/charging/eFuse/partition changes, no NVS diagnostic writes. Prefer
small pinned dependency patch over full upgrade; exact artifact audit and
battery cold-start/USB/unplug/SD/audio/head/RGB regression required. No power
initialization code changed by this documentation update.

### B11m bounded boost precharge candidate
Patch exact M5GFX 0.2.26 and M5Unified 0.2.20 source blobs only, gated by
BOARD_STACKCHAN in the full game compile. Clear high latch only when P1_7
is still input before M5GFX direction setup; preserve all other output bits
and never interrupt an already high driven rail. If original detection needs
boost, precharge there; otherwise at Power.begin. Twenty bounded pulses with
recovery intervals, then continuous high, modeled on reported K151 workaround.
No retry or direct enable fallback on detected I2C failure; halt initialization.
Existing downstream bus output/PMIC/charging policy unchanged. Not measured
or certified on hardware: actual pulses depend on bus latency, and failing
first pulse can still cut power. Require exact ELF audit and supervised cold
boot checks, including no external accessories and normal battery protection.
No new NVS diagnostic writes, no motor output, no partition or eFuse changes.
