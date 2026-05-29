[app]
title           = RETRIS
package.name    = retris
package.domain  = org.kakoritz
source.dir      = .
source.include_exts = py,json
source.exclude_dirs = tests, .git, .claude, __pycache__, .venv, custom_recipes

version         = 1.11.3

# Use compiled pygame recipe (builds from source against Android SDL2).
# custom_recipes/pygame overrides p4a's 2.1.0 with 2.6.1 (Python 3.14 support).
requirements    = python3,pygame,numpy

orientation     = portrait
fullscreen      = 1

# Android SDK/NDK
android.minapi  = 24
android.targetapi = 34
android.ndk     = 28c

# Target 64-bit ARM (all phones since ~2019)
android.archs   = arm64-v8a

# Accept SDK licences non-interactively (required for CI)
android.accept_sdk_license = True

android.permissions = INTERNET

# Smaller mixer buffer for lower Android audio latency
android.meta_data = audio.buffer_size=1024

icon.filename = %(source.dir)s/icon.png

# Custom recipes directory: overrides p4a's pygame recipe with 2.6.1 which
# supports Python 3.13/3.14 (longintrepr.h was removed from pygame in 2.5.0).
p4a.local_recipes = ./custom_recipes

[buildozer]
log_level = 2
warn_on_root = 1
