[app]
title           = RETRIS
package.name    = retris
package.domain  = org.kakoritz
source.dir      = .
source.include_exts = py,json
source.exclude_dirs = tests, .git, .claude, __pycache__, .venv

version         = 1.10.3

# pygame-ce + numpy — all sound/graphics generated at runtime, no asset files
requirements    = python3,pygame-ce,numpy

orientation     = portrait
fullscreen      = 1

# Android SDK/NDK
android.minapi  = 21
android.targetapi = 34
android.ndk     = 25b

# Target 64-bit ARM (all phones since ~2019)
android.archs   = arm64-v8a

# Accept SDK licences non-interactively (required for CI)
android.accept_sdk_license = True

# Use latest python-for-android for pygame-ce recipe support
p4a.branch = master

# No special permissions needed (no network, no external storage)
android.permissions =

# Smaller mixer buffer for lower Android audio latency
android.meta_data = audio.buffer_size:1024

# Icon — generated at runtime; placeholder satisfies the build system
# Replace with a real 512×512 PNG if desired
# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
