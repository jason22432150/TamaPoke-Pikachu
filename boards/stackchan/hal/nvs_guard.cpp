#include "nvs_guard.h"
#include <nvs_flash.h>

static esp_err_t lastInitResult = ESP_ERR_INVALID_STATE;

extern "C" esp_err_t __real_nvs_flash_init(void);
extern "C" esp_err_t __wrap_nvs_flash_init(void) {
  lastInitResult = __real_nvs_flash_init();
  return stackchanNvsStartupResult(lastInitResult, ESP_ERR_NVS_NO_FREE_PAGES,
                                  ESP_ERR_NVS_NEW_VERSION_FOUND, ESP_FAIL);
}

bool stackchanNvsReady() {
  return lastInitResult == ESP_OK;
}
