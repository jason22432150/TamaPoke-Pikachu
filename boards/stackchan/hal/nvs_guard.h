#pragma once

// Arduino ESP32 4.0.0 initArduino() erases the whole default NVS partition
// on NO_FREE_PAGES or NEW_VERSION_FOUND. Map only these recovery-triggering
// failures to a generic failure; keep the original result for the game gate.
constexpr int stackchanNvsStartupResult(int result, int noFreePages,
                                       int newVersionFound, int genericFailure) {
  return (result == noFreePages || result == newVersionFound)
      ? genericFailure : result;
}

bool stackchanNvsReady();
