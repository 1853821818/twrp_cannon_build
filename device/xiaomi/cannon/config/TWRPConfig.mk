# Include to BoardConfig.mk
TW_THEME := portrait_hdpi
TARGET_SCREEN_WIDTH := 1080
TARGET_SCREEN_HEIGHT := 2340
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
# OriginOS4.0-24810 包的 vendor fstab 是 fileencryption=...:v1，TWRP 必须同步用 policy 1
TW_USE_FSCRYPT_POLICY := 1
TW_INCLUDE_FBE_METADATA_DECRYPT := true
# 固定使用本机 vendor keymaster 4.1，避免 TWRP 自动探测到错误版本
TW_FORCE_KEYMASTER_VER := true
# OPPO/Realme/部分 MTK 移植包需要提前准备 /data/media
TW_PREPARE_DATA_MEDIA_EARLY := true
TW_EXCLUDE_DEFAULT_USB_INIT := true
TW_EXTRA_LANGUAGES := true
TW_DEFAULT_LANGUAGE := zh_CN
TW_INCLUDE_NTFS_3G := true
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 900
TW_SCREEN_BLANK_ON_BOOT := true
TW_INCLUDE_FUSE_EXFAT := true
# 精简 manifest 下 external/nano / external/libncurses 未同步，nano 仅为可选编辑器，排除
TW_EXCLUDE_NANO := true
# 精简 manifest 下 tzdata 未生成，时区数据仅影响显示，排除
TW_EXCLUDE_TZDATA := true
# lpdump/lptools 仅用于动态分区诊断，不是 /data 解密必需；
# 精简树里 lpdump 的 init_rc 没有 install 规则，排除以避免无谓依赖。
TW_EXCLUDE_LPDUMP := true
TW_EXCLUDE_LPTOOLS := true

# For debugging Purposes
TWRP_INCLUDE_LOGCAT := true

# System Override Props
TW_OVERRIDE_SYSTEM_PROPS := \
    "ro.build.date.utc;ro.bootimage.build.date.utc=ro.build.date.utc;ro.odm.build.date.utc=ro.build.date.utc;ro.product.build.date.utc=ro.build.date.utc;ro.system.build.date.utc=ro.build.date.utc;ro.system_ext.build.date.utc=ro.build.date.utc;ro.vendor.build.date.utc=ro.build.date.utc;ro.build.product;ro.build.fingerprint=ro.system.build.fingerprint;ro.build.version.incremental;ro.product.device=ro.product.system.device;ro.product.model=ro.product.system.model;ro.product.name=ro.product.system.name"

# Shared Recovery Modules Libraries
RECOVERY_LIBRARY_SOURCE_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libpuresoftkeymasterdevice.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/ashmemd_aidl_interface-cpp.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libashmemd_client.so

# Maintainer/Version
TW_DEVICE_VERSION := cd-Spidey