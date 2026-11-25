#include "hal/nvs_guard.h"
#include <cassert>

int main() {
  const int noPages=0x110d, newVersion=0x1110, fail=-1;
  assert(stackchanNvsStartupResult(0,noPages,newVersion,fail)==0);
  assert(stackchanNvsStartupResult(noPages,noPages,newVersion,fail)==fail);
  assert(stackchanNvsStartupResult(newVersion,noPages,newVersion,fail)==fail);
  assert(stackchanNvsStartupResult(0x1101,noPages,newVersion,fail)==0x1101);
}
