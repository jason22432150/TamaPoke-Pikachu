# K151 bench acceptance checklist (not a flash guide)

Status: NOT RUN on hardware. A green CI is not hardware acceptance.

## Before any write
- Record K151 hardware revision, factory firmware version, USB port and power source.
- Capture and verify two full factory reads using stackchan_backup.py. Store privately.
- Review security, actual partition table and same-device recovery feasibility.
- Independently confirm original calibration values and available recovery method.
- Verify the candidate manifest, commit, toolchain pins and all hashes.
- Do not proceed if secure boot/encryption or layout are unresolved.
- Candidate is incomplete for flashing: it lacks OTA selection data and an approved write plan.
- No experimental write is authorized by this checklist.

## After a separately reviewed installation
Record commit/hash, test timestamp and PASS/FAIL/NOT RUN for every row.
Do not include credentials, MAC or private flash images in public issues.

| Area | Acceptance |
| --- | --- |
| Boot | Correct board, 16 MiB flash, 8 MiB PSRAM, 320x240; no reset loop |
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
| Motion | Preview only; no physical motion, calibration unchanged |
| Persistence | Game state and language survive reboot; original calibration unchanged |
| Stability | 60-minute normal play; heap and reset reasons recorded |
| Recovery | Separately reviewed same-device restoration and factory boot verification |

Stop on abnormal heat, unintended motion, power faults, resets or display corruption.
Do not deliberately discharge a lithium battery below safe limits to test shutdown.
