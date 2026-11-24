# Copyright (C) 2022 The Android Open Source Project
# Copyright (C) 2022 SebaUbuntu's TWRP device tree generator
# SPDX-License-Identifier: Apache-2.0

DEVICE_PATH := device/xiaomi/cannon

# For building with minimal manifest
ALLOW_MISSING_DEPENDENCIES := true

# Architecture
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 := 
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a55

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a55

# Bootloader
# SELinux
# 精简 TWRP manifest 没有 product 级 BOARD_SEPOLICY_VERS，
# system/sepolicy 的 plat_mapping_file 会生成 "-n  -o ..." 空版本参数，
# version_policy 直接报 Unknown arguments supplied。按 AOSP 14 平台策略版本补上。
BOARD_SEPOLICY_VERS := 34.0

TARGET_NO_BOOTLOADER := true
PRODUCT_PLATFORM := mt6853
TARGET_BOARD_PLATFORM := $(PRODUCT_PLATFORM)

# File System
BOARD_HAS_LARGE_FILESYSTEM := true
BOARD_SYSTEMIMAGE_PARTITION_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := f2fs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := ext4

# Userimage
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
TARGET_USES_MKE2FS := true

# Workaround in case of copy error
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_PRODUCT := product

# Block Size
BOARD_FLASH_BLOCK_SIZE := 131072

# Kernel（按 OriginOS4.0-24810 原包 recovery.img 头修正）
BOARD_BOOTIMG_HEADER_VERSION := 2
BOARD_KERNEL_CMDLINE := bootopt=64S3,32N2,64N2 buildvariant=user
BOARD_KERNEL_BASE := 0x40080000
BOARD_KERNEL_PAGESIZE := 2048
BOARD_RAMDISK_OFFSET := 0x07c00000
BOARD_KERNEL_TAGS_OFFSET := 0x0bc00000
BOARD_KERNEL_IMAGE_NAME := Image.gz

# Kernel Source
TARGET_KERNEL_CONFIG := cannon_defconfig
TARGET_KERNEL_SOURCE := kernel/xiaomi/cannon
TARGET_KERNEL_CLANG_COMPILE := true
LC_ALL="C"

# Kernel Prebuilt
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/$(BOARD_KERNEL_IMAGE_NAME)
TARGET_PREBUILT_DTB := $(DEVICE_PATH)/prebuilt/dtb.img
BOARD_INCLUDE_RECOVERY_DTBO := true
BOARD_PREBUILT_DTBOIMAGE := $(DEVICE_PATH)/prebuilt/dtbo.img

# Args
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOTIMG_HEADER_VERSION)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --dtb $(TARGET_PREBUILT_DTB)

# Verified Boot
BOARD_AVB_ENABLE := true
BOARD_AVB_ROLLBACK_INDEX := $(PLATFORM_SECURITY_PATCH_TIMESTAMP)
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --set_hashtree_disabled_flag
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 2
BOARD_AVB_RECOVERY_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_RECOVERY_ALGORITHM := SHA256_RSA4096
BOARD_AVB_RECOVERY_ROLLBACK_INDEX := 1
BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION := 1

# Partitions
BOARD_USES_METADATA_PARTITION := true
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 134217728
BOARD_SUPER_PARTITION_SIZE := 9126805504
BOARD_SUPER_PARTITION_SYSTEM_DEVICE_SIZE := 3087618048
BOARD_SUPER_PARTITION_GROUPS := main
BOARD_MAIN_PARTITION_LIST := system vendor product
BOARD_MAIN_SIZE := 9122611200
BOARD_ROOT_EXTRA_FOLDERS := bluetooth dsp firmware persist

# Recovery
RECOVERY_SDCARD_ON_DATA := true
BOARD_SUPPRESS_SECURE_ERASE := true
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/root/system/etc/recovery.fstab
TARGET_SYSTEM_PROP := $(DEVICE_PATH)/props/system.prop
TARGET_VENDOR_PROP := $(DEVICE_PATH)/props/vendor.prop

# Recovery Device Modules
TARGET_RECOVERY_DEVICE_MODULES += \
    libkeymaster4 \
    libpuresoftkeymasterdevice \
    ashmemd_aidl_interface-cpp \
    libashmemd_client

# Hack: prevent anti rollback
PLATFORM_SECURITY_PATCH := 2099-12-31
VENDOR_SECURITY_PATCH := $(PLATFORM_SECURITY_PATCH)
BOOT_SECURITY_PATCH := $(PLATFORM_SECURITY_PATCH)
PLATFORM_VERSION := 99.87.36
PLATFORM_VERSION_LAST_STABLE := $(PLATFORM_VERSION)

# TWRP recovery不编译vendor/system，无需VNDK。禁用避免board_config要求VNDK 34 prebuilt
BOARD_VNDK_VERSION :=
KEEP_VNDK := false

# Debugging Configs
TARGET_USES_LOGD := true

# TWRP Configuration
include $(DEVICE_PATH)/config/TWRPConfig.mk

# SHRP Configuration
include $(DEVICE_PATH)/config/SHRPConfig.mk

# TWRP Soong variable export（必须；否则 TW_THEME/TW_BRIGHTNESS_PATH 不会传给 Soong，
# 会出现 "Could not find ui.xml for TW_THEME: not set" 并导致 build.ninja 生成失败）
ifneq ($(wildcard vendor/twrp/config/BoardConfigSoong.mk),)
include vendor/twrp/config/BoardConfigSoong.mk
endif

# 兜底：即使 vendor/twrp/config/BoardConfigSoong.mk 没被同步/没被包含，
# 也直接向 Soong 的 twrpVarsPlugin 注册主题和亮度变量，避免 TW_THEME 为空。
ifeq ($(SOONG_CONFIG_twrpVarsPlugin_TW_THEME),)
SOONG_CONFIG_NAMESPACES += twrpVarsPlugin
SOONG_CONFIG_twrpVarsPlugin += TW_THEME TARGET_SCREEN_WIDTH TARGET_SCREEN_HEIGHT TW_BRIGHTNESS_PATH TW_MAX_BRIGHTNESS
SOONG_CONFIG_twrpVarsPlugin_TW_THEME := $(TW_THEME)
SOONG_CONFIG_twrpVarsPlugin_TARGET_SCREEN_WIDTH := $(TARGET_SCREEN_WIDTH)
SOONG_CONFIG_twrpVarsPlugin_TARGET_SCREEN_HEIGHT := $(TARGET_SCREEN_HEIGHT)
SOONG_CONFIG_twrpVarsPlugin_TW_BRIGHTNESS_PATH := $(subst ",, $(TW_BRIGHTNESS_PATH))
SOONG_CONFIG_twrpVarsPlugin_TW_MAX_BRIGHTNESS := $(TW_MAX_BRIGHTNESS)
endif