#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
arduino-cli compile --warnings all --fqbn 'esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=qspi' --output-dir "$ROOT/build/stackchan-smoke" "$ROOT/boards/stackchan/StackChanSmoke"
