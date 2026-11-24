/*
 * Copyright (C) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef _TWRP_FSCRYPT_POLICY_COMPAT_H_
#define _TWRP_FSCRYPT_POLICY_COMPAT_H_

/*
 * TeamWin android-14 的 partitions.hpp / twrpTar.cpp / libtar 仍包含旧版
 * system/vold/fscrypt_policy.h。AOSP 14 已把该文件移除，策略辅助函数也不再
 * 由 libvold 导出。这里提供一份自包含的兼容实现：
 *   - fscrypt_policy 联合体与内核 uapi 的 v1/v2 布局一致；
 *   - 用 ioctl 直接读写目录的 fscrypt policy，供 TWRP 备份/恢复保存策略；
 *   - lookup_ref_key/lookup_ref_tar 依赖 vold 的运行时 user-key 映射，recovery
 *     不启动 vold，无法可靠恢复映射，这里返回 false，让 TWRP 按原有逻辑
 *     跳过策略元数据而不是中断编译或链接；
 *   - fscrypt_set_mode 只被 twrpTar 初始化调用，不做实际解密，返回 true。
 */

#include <errno.h>
#include <fcntl.h>
#include <linux/fscrypt.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

/*
 * TeamWin libtar/append.c 仍使用旧 system/vold/fscrypt_policy.h 中的
 * 策略类型后缀，用于拼接 "1CE" / "1DE" / "1DK" 形式的描述符。
 * AOSP 14 已删除该头文件，这里按 Android 12.1 原值补齐。
 */
#define USER_CE_FSCRYPT_POLICY   "CE"
#define USER_DE_FSCRYPT_POLICY   "DE"
#define SYSTEM_DE_FSCRYPT_POLICY "DK"

#ifdef __cplusplus
extern "C" {
#endif

#define FS_KEY_DESCRIPTOR_SIZE_HEX (2 * FS_KEY_DESCRIPTOR_SIZE + 1)
#define FSCRYPT_KEY_IDENTIFIER_SIZE_HEX ((2 * FSCRYPT_KEY_IDENTIFIER_SIZE) + 1)

#undef fscrypt_policy
typedef union fscrypt_policy {
    uint8_t version;
    struct fscrypt_policy_v1 v1;
    struct fscrypt_policy_v2 v2;
} fscrypt_policy;

static inline void *get_policy(const fscrypt_policy *fep) {
    if (!fep)
        return NULL;
    switch (fep->version) {
        case FSCRYPT_POLICY_V1:
            return (void *)&fep->v1;
        case FSCRYPT_POLICY_V2:
            return (void *)&fep->v2;
        default:
            return NULL;
    }
}

static inline uint8_t *get_policy_descriptor(fscrypt_policy *fep) {
    if (!fep)
        return NULL;
    switch (fep->version) {
        case FSCRYPT_POLICY_V1:
            return fep->v1.master_key_descriptor;
        case FSCRYPT_POLICY_V2:
            return fep->v2.master_key_identifier;
        default:
            return NULL;
    }
}

static inline uint8_t get_policy_size(fscrypt_policy *fep, bool hex) {
    if (!fep)
        return 0;
    switch (fep->version) {
        case FSCRYPT_POLICY_V1:
            return hex ? FS_KEY_DESCRIPTOR_SIZE_HEX : FSCRYPT_KEY_DESCRIPTOR_SIZE;
        case FSCRYPT_POLICY_V2:
            return hex ? FSCRYPT_KEY_IDENTIFIER_SIZE_HEX : FSCRYPT_KEY_IDENTIFIER_SIZE;
        default:
            return 0;
    }
}

static inline int fscrypt_policy_size(const fscrypt_policy *fep) {
    if (!fep)
        return 0;
    switch (fep->version) {
        case FSCRYPT_POLICY_V1:
            return sizeof(fep->v1);
        case FSCRYPT_POLICY_V2:
            return sizeof(fep->v2);
        default:
            return 0;
    }
}

static inline bool fscrypt_policy_get_struct(const char *directory, fscrypt_policy *fep) {
    int fd;
    struct fscrypt_get_policy_ex_arg ex_policy;

    if (!directory || !fep)
        return false;

    fd = open(directory, O_DIRECTORY | O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd == -1)
        return false;

    memset(fep, 0, sizeof(*fep));
    memset(&ex_policy, 0, sizeof(ex_policy));
    ex_policy.policy_size = sizeof(ex_policy.policy);

    if (ioctl(fd, FS_IOC_GET_ENCRYPTION_POLICY_EX, &ex_policy) != 0) {
        /* 老内核没有 GET_POLICY_EX，退回 v1 ioctl。 */
        if (ioctl(fd, FS_IOC_GET_ENCRYPTION_POLICY, &fep->v1) != 0) {
            close(fd);
            return false;
        }
    } else {
        memcpy(fep, &ex_policy.policy, sizeof(ex_policy.policy));
    }

    close(fd);
    return true;
}

static inline bool fscrypt_policy_set_struct(const char *directory, fscrypt_policy *fep) {
    int fd;
    void *policy;

    if (!directory || !fep)
        return false;

    policy = get_policy(fep);
    if (!policy)
        return false;

    fd = open(directory, O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd == -1)
        return false;

    if (ioctl(fd, FS_IOC_SET_ENCRYPTION_POLICY, policy) != 0) {
        close(fd);
        return false;
    }

    close(fd);
    return true;
}

static inline void bytes_to_hex(const uint8_t *bytes, size_t num_bytes, char *hex) {
    size_t i;

    if (!bytes || !hex)
        return;

    for (i = 0; i < num_bytes; i++)
        sprintf(&hex[2 * i], "%02x", bytes[i]);
    hex[2 * num_bytes] = '\0';
}

static inline void get_policy_content(fscrypt_policy *fep, char *content) {
    uint8_t *descriptor;
    char hex[FSCRYPT_KEY_IDENTIFIER_SIZE_HEX];

    if (!fep || !content)
        return;

    descriptor = get_policy_descriptor(fep);
    bytes_to_hex(descriptor, get_policy_size(fep, false), hex);

    if (fep->version == FSCRYPT_POLICY_V1) {
        snprintf(content, 50, "%i %i %i %i %s", (int)fep->v1.version,
                 (int)fep->v1.contents_encryption_mode,
                 (int)fep->v1.filenames_encryption_mode,
                 (int)fep->v1.flags, hex);
    } else if (fep->version == FSCRYPT_POLICY_V2) {
        snprintf(content, 50, "%i %i %i %i %s", (int)fep->v2.version,
                 (int)fep->v2.contents_encryption_mode,
                 (int)fep->v2.filenames_encryption_mode,
                 (int)fep->v2.flags, hex);
    } else {
        content[0] = '\0';
    }
}

/*
 * vold 的 user-key 映射只在正常启动的 vold 进程内维护，recovery 没有该映射，
 * 无法把策略描述符还原成 CE/DE key ref。保留接口，交由调用方跳过策略元数据。
 */
static inline bool lookup_ref_key(fscrypt_policy *fep, uint8_t *policy_type) {
    (void)fep;
    (void)policy_type;
    return false;
}

static inline bool lookup_ref_tar(fscrypt_policy *fep, uint8_t *policy) {
    (void)fep;
    (void)policy;
    return false;
}

static inline bool fscrypt_set_mode(void) {
    return true;
}

#ifdef __cplusplus
}
#endif

#endif /* _TWRP_FSCRYPT_POLICY_COMPAT_H_ */
