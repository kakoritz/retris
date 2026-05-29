[app]
title           = RETRIS
package.name    = retris
package.domain  = org.kakoritz
source.dir      = .
source.include_exts = py,json
source.exclude_dirs = tests, .git, .claude, __pycache__, .venv, custom_recipes

version         = 1.10.3

# pygame_ce = p4a recipe name; publishes official Android ARM64 wheels on PyPI
# imports as `import pygame` — zero code changes needed
requirements    = python3,pygame_ce,numpy

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

# Custom p4a recipe: forces ARM64 pygame_ce wheel download (p4a's default
# pip fallback runs on x86_64 host and grabs the wrong architecture wheel)
p4a.local_recipes = ./custom_recipes

[buildozer]
log_level = 2
warn_on_root = 1
