# K151 bench acceptance checklist (not a flash guide)

Status: NOT RUN on hardware. A green CI is not hardware acceptance.

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
| Assets | ASSETINFO, no-SD starter evolution lines and Pikachu/Raichu normal/shiny, all gallery thumbnails, SD precedence and embedded fallback |
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
