# Declare the 'next' release config for TWRP Android 14 build.
# twrp-14 minimal manifest lacks vendor/google, so no release config is declared
# and Android 14's <product>-<release>-<variant> lunch format fails.
# Use build/release/build_config/ap2a.scl (the 'next' release) which ships with AOSP.
$(call declare-release-config, next, build/release/build_config/ap2a.scl)
