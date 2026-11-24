#pragma once
// Application SDK configuration guard. This does not attest a prebuilt bootloader.
#include <sdkconfig.h>
#if defined(CONFIG_SECURE_BOOT) && CONFIG_SECURE_BOOT
#error "StackChan forbids secure boot provisioning"
#endif
#if defined(CONFIG_SECURE_BOOT_V2_ENABLED) && CONFIG_SECURE_BOOT_V2_ENABLED
#error "StackChan forbids secure boot V2"
#endif
#if defined(CONFIG_SECURE_FLASH_ENC_ENABLED) && CONFIG_SECURE_FLASH_ENC_ENABLED
#error "StackChan forbids flash encryption provisioning"
#endif
#if defined(CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK) && CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK
#error "StackChan forbids eFuse anti-rollback"
#endif
#if defined(CONFIG_SECURE_DISABLE_ROM_DL_MODE) && CONFIG_SECURE_DISABLE_ROM_DL_MODE
#error "StackChan forbids permanent ROM download mode disable"
#endif
#if defined(CONFIG_SECURE_ENABLE_SECURE_ROM_DL_MODE) && CONFIG_SECURE_ENABLE_SECURE_ROM_DL_MODE
#error "StackChan forbids secure ROM download mode provisioning"
#endif
