[app]
title           = RETRIS
package.name    = retris
package.domain  = org.kakoritz
source.dir      = .
source.include_exts = py,json
source.exclude_dirs = tests, .git, .claude, __pycache__, .venv, custom_recipes

version         = 1.10.3

# Use p4a's compiled 'pygame' recipe (builds from source against Android SDL2).
# pygame_ce has no p4a recipe — its pip fallback grabs a manylinux wheel that
# bundles its own SDL2 with a hashed soname the Android linker cannot resolve.
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

# Pin p4a to the last commit that used Python 3.11 (before 3.14 became the
# default in e1bd2497). Pygame 2.1.0 includes longintrepr.h which was removed
# in Python 3.13, so it cannot build against Python 3.14.
p4a.branch = master
p4a.commit = 3762c88c

[buildozer]
log_level = 2
warn_on_root = 1
