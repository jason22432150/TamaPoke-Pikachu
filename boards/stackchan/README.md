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
The full game is not yet integrated; original Waveshare sources remain untouched.
