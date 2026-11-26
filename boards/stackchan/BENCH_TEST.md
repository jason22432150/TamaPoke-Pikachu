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
| START | No game namespace creation until explicit START |
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
