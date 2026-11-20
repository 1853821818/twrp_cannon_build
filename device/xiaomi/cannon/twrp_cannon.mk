# Copyright (C) 2022 The Android Open Source Project
# Copyright (C) 2022 SebaUbuntu's TWRP device tree generator
# SPDX-License-Identifier: Apache-2.0

PRODUCT_DEVICE := cannon
PRODUCT_NAME := twrp_$(PRODUCT_DEVICE)
PRODUCT_BRAND := redmi
PRODUCT_MODEL := Redmi Note 9 5G
PRODUCT_MANUFACTURER := xiaomi
PRODUCT_RELEASE_NAME := $(PRODUCT_DEVICE)


# Inherit from the Device Tree itself.
$(call inherit-product, device/xiaomi/cannon/cannon-device.mk)

# Inherit from Prebuilt Products.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
# gsi_keys.mk是AOSP独有，TeamWin的build/make(android-14)不含。TWRP recovery不需要，用if-exists避免报错
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/gsi_keys.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)

# Inherit from TWRP-common Stuff, if building TWRP.
$(call inherit-product-if-exists, vendor/twrp/config/common.mk)

# Inherit from PBRP-common Stuff, if building PBRP.
$(call inherit-product-if-exists, vendor/pb/config/common.mk)

# Inherit from OMNI-common Stuff, if building from below Android 10.
$(call inherit-product-if-exists, vendor/omni/config/common.mk)

# TeamWin 的 twrp-14 manifest 不含完整 sepolicy；显式把 Soong 的
# precompiled_sepolicy 和兼容模块 sepolicy 加入产品，避免 ninja 报
# "precompiled_sepolicy missing and no known rule"。
# 只有 system/sepolicy/Android.bp 存在时才加，避免 manifest 没同步到时
# Soong 直接报 "module precompiled_sepolicy not found"。
ifneq ($(wildcard system/sepolicy/Android.bp),)
PRODUCT_PACKAGES += \
    precompiled_sepolicy \
    sepolicy

# system/sepolicy 的 file_contexts.bin 规则依赖 host 工具 checkfc/fc_sort/
# sefcontext_compile，但 TeamWin 的精简构建不会自动编译这些 Soong host 模块。
# fc_sort 已在 workflow 用官方 tests/fc_sort.py 补齐；这里把另外两个加入
# PRODUCT_HOST_PACKAGES，让 Soong 生成 out/host/linux-x86/bin 下的可执行文件。
PRODUCT_HOST_PACKAGES += \
    checkfc \
    sefcontext_compile
endif

PRODUCT_GMS_CLIENTID_BASE := android-$(PRODUCT_MANUFCATURER)

# 本机 vendor keymaster 是 4.1；TW_FORCE_KEYMASTER_VER 依赖该 prop
PRODUCT_PROPERTY_OVERRIDES += keymaster_ver=4.1

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="cannon-user 12 SP1A.210812.016 V14.0.6.0.SJECNXM release-keys"

BUILD_FINGERPRINT := redmi/cannon/cannon:12/SP1A.210812.016/V14.0.6.0.SJECNXM:user/release-keys
