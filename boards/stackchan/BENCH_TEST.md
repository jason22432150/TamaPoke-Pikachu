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
  60-minute continuous telemetry and visual acceptance remain outstanding.
  Do not infer a specific cause for the maximum loop gap from aggregates.
- NOT RUN or not yet reported: detailed gameplay, all UI screens, audio,
  RTC retention, SD sprite reads, RGB visual behavior, persistence, motion preview ON,
  60-minute stability and final post-game eFuse comparison.
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
4. Record a continuous 60-minute PERF ON session, then PERF OFF; analyze the
   captured log using stackchan_perf_report.py. Record active/idle workload.
5. After testing, enter ROM download mode and capture a new independent
   eFuse snapshot; compare against the original installation before snapshot
   and pre-START after-boot snapshot. Do not overwrite existing checkpoints.
6. Review all acceptance rows and unresolved failures before tagging Alpha.

## Deferred UI work (owner selected option B)

Only after the existing Alpha acceptance, start StackChan-specific rectangular
320x240 landscape adaptation: top status bar, bottom action bar, aspect-ratio
preserving pet scene, shared touch/render geometry, followed by settings,
gallery and minigames. Keep Waveshare circular UI, existing game saves,
factory Assets and partition table, eFuse policy, physical motor/OTA restrictions.
No UI implementation or firmware reapproval is part of this acceptance record.

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
| Stability | 60-minute normal play with PERF ON; capture paired PERF_TIME/PERF_MEM records, compare active vs idle FPS, min/largest heap, PSRAM and reset reason; PERF OFF afterwards |
| eFuse | Read-only before/after summaries unchanged, including after first boot |

Stop on abnormal heat, unintended motion, power faults, resets or display corruption.
Do not deliberately discharge a lithium battery below safe limits to test shutdown.

Analyze the captured log with tools/stackchan_perf_report.py --minutes 60.
Review all data-quality and memory-decline flags; repeat an identical workload
before diagnosing a leak. A clean report cannot replace the checklist.
