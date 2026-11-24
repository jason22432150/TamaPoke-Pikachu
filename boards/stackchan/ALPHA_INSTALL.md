# Alpha 0.1.0 macOS local USB bench instructions

StackChan installation is local only. Do not use the upstream Waveshare web
installer, Chrome/Edge Web Serial, or any browser-based flashing workflow.

**Status: NOT FOR FLASH. No independently approved bootloader/application tuple exists.**
All instructions currently stop at read-only checks. Do not bypass the installer
approval gate, run a manual flash command or use force. No factory restoration
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

Download the candidate named stackchan-alpha-0.1.0-NOT-FOR-FLASH from the
matching Actions run after the build passes, and extract it into a private
directory. Match the checkout commit to manifest.json. Never treat an
artifact label, an integrity hash or green CI as installation approval.

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
--after no-reset for esptool and --before no-reset for espefuse. This avoids
intentional auto-reset but does not prove serial open/close or USB behavior
cannot reset the device. Stop if the port changes or normal firmware starts.

    python tools/stackchan_flash.py probe --candidate ~/stackchan-alpha-0.1.0 --port /dev/cu.usbmodemXXXX --out ~/k151-alpha-preflight

Probe only reads chip identity, eFuse summary, security, flash capacity and
the partition table. It requires a new private directory and will fail if
the current layout differs from the experimental one. That is expected
for some factory devices; do not erase or repartition to bypass it.
Do not share private snapshot data or MAC addresses publicly.

## Future approved installation (not yet authorized)

Once a separately reviewed build is approved by maintainers, the installer
will require the exact source commit and all four image digests, explicit
acknowledgement of download mode, same-device identity and compatible layout.
It will write separated images, read back exact byte ranges and compare the
eFuse summary before permitting the operator to proceed. No automatic hard
reset is requested. A hardware-specific download-mode/USB reset procedure
must be validated to ensure that the application cannot boot prematurely.
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
- https://github.com/espressif/arduino-esp32/blob/3.3.0/platform.txt
