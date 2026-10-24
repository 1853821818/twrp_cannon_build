# Declare release configs for TWRP Android 14 build.
# twrp-14 minimal manifest lacks vendor/google, so no release config is declared
# and Android 14's <product>-<release>-<variant> lunch format fails.
# ap2a.scl defines the Android 14 ('next') release and ships with AOSP build/release.
$(call declare-release-config, next, build/release/build_config/ap2a.scl)
$(call declare-release-config, ap2a, build/release/build_config/ap2a.scl, next)
