# Alpha 0.1.0 macOS local USB bench instructions

StackChan installation is local only. Do not use the upstream Waveshare web
installer, Chrome/Edge Web Serial, or any browser-based flashing workflow.

**Status: one exact archived candidate is eligible for supervised ROM-only Flash installation.**
Do not boot it until the operator has completed Flash readback and reviewed the
before/after-write eFuse comparison. All other candidates remain NOT FOR FLASH.
Do not bypass the installer approval gate, run a manual flash command or use force. No factory restoration
or NVS migration is provided. Physical motors and online OTA stay disabled.

## Prepare the Mac

Install Python 3.11+ and Git using their official distribution. In Terminal:

    git clone --branch stackchan --single-branch https://github.com/jason22432150/TamaPoke-Pikachu.git
    cd TamaPoke-Pikachu
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install esptool==5.1.0

This downloads the experimental branch and isolates the exact serial tool
version from your system Python. It does not connect to the device.

For the supervised installation use only the archived source-bootloader
paired candidate from run 45554127667, artifact 14995636144, source commit
bb5234ef25ca5903309028b76afcbc29dc414011. Extract it into a separate
private directory. Its original NOT-FOR-FLASH label and manifest flags are
retained as historical build evidence. The newer installer allowlist is
the only installation gate; a new green build is not automatically approved.
Do not use the Arduino-prebuilt-bootloader candidate or any Assets-replacement
candidate. Never substitute a new rebuild.

    python tools/stackchan_package.py verify --out ~/stackchan-alpha-0.1.0

This validates the manifest and each binary, without touching the device.

## Read-only bench preflight

Disconnect other ESP boards, remove the SD card, stop serial monitors,
use a reliable data cable and support the robot on a stable surface.
Use the official K151 download-mode procedure. Do not enable movement.

    ls /dev/cu.*

This lists serial devices on macOS. Replace the example port below with the
actual K151 port. Manually enter ROM download mode before invoking probe,
install or after-boot. The installer now requests --before no-reset and
--after no-reset for esptool and --before no-reset for espefuse. The installer now also passes --no-stub to esptool, so it uses the ROM
loader rather than launching a RAM flasher. This avoids the normal stub
exit soft reset; ROM flash readback is slower (64 bytes per request).
The write launcher pins esptool 5.1.0 and disables its automatic write
reconnect, which otherwise calls connect() with the default reset mode.
Serial open/close and USB behavior still require physical validation.
Stop if the port changes or normal firmware starts. Do not retry a failed
write automatically. The read-only probe is safe to test with the current
factory firmware in manual download mode; it does not authorize installation.

    python tools/stackchan_flash.py probe --candidate ~/stackchan-alpha-0.1.0 --port /dev/cu.usbmodemXXXX --out ~/k151-alpha-preflight

Probe only reads chip identity, eFuse summary, security, flash capacity and
the partition table. It requires a new private directory and will fail if
the current layout differs from the observed K151 layout. Do not erase or
repartition to bypass it. The previous b9b13c0 candidate had a different
layout; use a new matching-commit candidate after CI passes.
If the chip and security checks pass, layout-report.json records both
partition tables and their match status, even when they differ. It also
reports whether the candidate-length table bytes match exactly. This report
omits MAC and eFuse values and can be provided for layout review. If the
probe fails earlier, report only the error message. Do not share the private
before/ snapshot, raw eFuse summary, or MAC addresses publicly.

### Flash encryption count parsing

Espefuse 5.1.0 uses the display string "Disable" for raw SPI_BOOT_CRYPT_CNT
values 0 and 3. The installer requires raw count 0 from get-security-info
and verifies that it agrees with the summary; a disabled encryption status
alone is not sufficient. New eFuse snapshots include the raw counter in
their evidence (schema 2). Capture fresh snapshots; schema 1 snapshots
cannot establish the raw counter and are not interchangeable.
If the probe fails, share only the line beginning
SPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): from security.txt, not the
full security report or eFuse snapshot. Never modify the counter.

### First hardware boot failure and DMA fix candidate

The owner reported a successful bb5234e Flash write/readback and unchanged
observable eFuse summaries (no unreadable named fields), then repeated
GDMA/SPI initialization failures and LoadProhibited before START.
The first-boot eFuse checkpoint is still required. No motor activity was
observed. M5GFX 0.2.26 fills spi_bus_config_t with 0xff, leaving the new
IDF 6.1 dma_burst_size member at UINT32_MAX. The K151-only build patch
sets it to zero (SDK default 32 bytes) and stops the SPI initialization
path on bus/device setup errors instead of continuing with invalid handles.
Local K151 builds must apply the pinned patch after installing M5GFX:
    
    python3 tools/patch_stackchan_m5gfx.py "$(arduino-cli config get directories.user)/libraries/M5GFX"

This modifies only the pinned M5GFX library source; use a dedicated Arduino
library directory if also building other boards locally. CI checks the patch
and leaves Waveshare builds unchanged. New firmware still needs exact
artifact safety review and approval; do not reuse the old candidate for
another write. If boot fails, enter ROM download mode and run after-boot
using the original installation directory before further tests.

## Source bootloader reference (build only)

The Arduino 4.0.0 candidate continues to use its existing precompiled
bootloader. Arduino 4.0.0 is based on ESP-IDF v6.1.1; older applications must not be paired with newer bootloaders (see the official Bootloader Compatibility guide). A separate CI job now builds an independent ESP-IDF v6.1.1 reference
from commit 051e4c4eb20346e043cdd47bc388fde75ff8af63 with explicit defaults and
checks both resolved sdkconfig and the bootloader's generated header.
It uses DIO, 80 MHz, 16 MiB, partition table offset 0x8000; secure boot,
flash encryption, anti-rollback and virtual eFuse modes must remain disabled.
After installing/activating exactly that ESP-IDF version locally:

    bash tools/build_stackchan_bootloader.sh ~/stackchan-source-bootloader

This only compiles and exports the reference bootloader, ELF, configuration
and manifest. It does not connect to StackChan or write any flash/eFuse.
Alternatively download stackchan-source-bootloader-NOT-FOR-FLASH from CI.
CI also assembles stackchan-alpha-0.1.0-source-bootloader-NOT-FOR-FLASH
from both same-commit artifacts, with the application descriptor, image
headers and hashes checked. The first paired build passed at 124963d
(run 45443822957); its application reports v6.1.1-dirty, not proof of
an unmodified ESP-IDF source tree. Use the paired candidate for offline
review only. Compile evidence now inventories linked eFuse programming
symbol names and distinguishes absolute ROM symbols. This is not a
reachability analysis and does not prove absence of inlined or direct
register writes. Runtime compatibility, complete eFuse write-path review,
device partition layout and hardware behavior are not established.

### First-boot NVS safeguard

The observed K151 map has a 16 KiB default NVS partition. Arduino ESP32
4.0.0 initArduino() normally erases the entire default NVS partition when
nvs_flash_init() returns ESP_ERR_NVS_NO_FREE_PAGES or
ESP_ERR_NVS_NEW_VERSION_FOUND. The game candidate now wraps nvs_flash_init
at link time to suppress that specific automatic format path and stops
game startup if NVS initialization fails. CI checks the startup reference,
and paired packaging rejects missing or false guard evidence.
This does not make NVS read-only: normal SDK recovery/compaction and game
preferences can still change Flash. Diagnostic artifacts and older game
candidates do not have this safeguard and remain NOT FOR FLASH.

A read-only probe must report both layout_matches and table_bytes_match
as true; a logically equivalent but byte-different table is not accepted.
Do not repartition or edit the table to bypass this check.

### Exact candidate review status

CI run 45552457156 (commit 5d08fb245f082e0b5e5aba9bc7a06a73c3227511)
passed all six jobs. The owner reported a successful ROM-only read-only
probe against the earlier d811939 candidate: 16 MiB, secure boot and flash
encryption disabled, raw crypt count zero, layout and table bytes equal.
This is evidence of read-only compatibility on that unit, not of a write
or first boot, and does not establish that USB stayed in download mode
after the last command.

The 5d08fb2 candidate has no matched linked eFuse writer symbols or explicit
ROM write references. The bounded instruction evidence for three eFuse base
address literals (one bootloader, two application) contains reads of the
ESP32-S3 readback registers at offsets 0x34, 0x3c, 0x40, 0x50, 0x54, 0x58
and 0x6c. This does not resolve all subsequent control flow or computed
addresses. The Arduino application still reports v6.1.1-dirty.

The existing game compile-evidence artifact now retains the exact
application ELF, linker map and SDK configuration, with their SHA-256
checked in the paired job. Review these against the matching bootloader
ELF and candidate, not a later rebuild. A review is not a hardware test.
The bounded review of the exact bb5234e artifacts was completed using
run 45562883467, artifact 14998318439. The known 7 bootloader and 10 app
base-address loads were traced in complete functions to eFuse reads.
Three additional explicit app references (0x6000704c/0x60007050) are
reads for OPI configuration and startup logging. An aligned scan of the
loaded image segments found 1 bootloader and 27 app words in the eFuse
address page: the app also contains the 22 words of range_read_addr_blocks,
which are used by esp_efuse_utility_read_reg, and one incidental word
inside u8g2_font_unifont_t_japanese3. The indirect utility callback's
observed call site uses esp_efuse_utility_fill_buff (reads and copies data
to RAM). The application init_efuse function returns ESP_OK directly.
No direct references or literal addresses were found for ROM program,
write_key, set_timing, clear_program_registers or public-key revocation.
Secure boot, encryption, anti-rollback and nondefault ROM log modes are
disabled. This is a bounded static review, not a formal proof of all
computed addresses, ROM behavior or runtime paths. The application SDK
reports v6.1.1-dirty; first boot remains untested.
Only the exact reviewed tuple is allowed for supervised ROM-only Flash
installation. All other builds remain denied.

### Factory CSV spelling

The partition CSV follows the owner's supplied ESP-IDF table, including
blank offsets for ota_1 and coredump and 4M for assets. These resolve to
0x510000, 0xe00000 and 0x400000 respectively. The expected 3072-byte
partition image SHA-256 remains
48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b.
The installer still preserves the physical partition table and assets.

## Supervised first installation (exact archived candidate only)

The installer requires the exact source commit and all four image digests, explicit
acknowledgement of download mode, same-device identity and compatible layout.
It will require exact existing table bytes before writing and will not rewrite
the partition table. Only bootloader (0x0), OTA selection (0xd000) and ota_0
application (0x20000) are written; the OTA selection is reset to erased bytes.
NVS, PHY init, ota_1, assets and coredump are not directly erased by these
writes. First boot can still change data in Flash. The installer reads back
all four image regions and compares eFuse summaries before proceeding. No automatic hard
reset is requested. A hardware-specific download-mode/USB reset procedure
must be validated to ensure that the application cannot boot prematurely.
For the initial write, run install with --acknowledge-download-mode only
while the device is held in ROM download mode. Keep it there after the
command completes. Share only write-verified.json (not raw snapshots),
and review it before any normal boot. If any step fails, stop; do not retry
or reset into normal firmware. This process cannot guarantee an unchanged
unreadable eFuse field or prevent a physical USB/power fault.
After an explicitly supervised first boot, manually re-enter ROM download mode;
the after-boot command captures
a third snapshot and compares the observed fields. No such command proves
that protected or reserved bits are unchanged.

Use BENCH_TEST.md to record PASS/FAIL/NOT RUN, starting with boot, display,
touch, START, audio, RTC, persistence, SD and RGB. Keep motor output and OTA
disabled. Stop at any unexpected movement, reset, heat, or power fault.

## Official references

- https://docs.m5stack.com/en/StackChan/
- https://docs.espressif.com/projects/esptool/en/latest/esp32s3/
- https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/bootloader.html
- https://github.com/espressif/arduino-esp32/blob/4.0.0/platform.txt
