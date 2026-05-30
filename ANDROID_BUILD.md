# RETRIS — Android APK Build Guide

Complete reference for building and deploying the RETRIS Android APK.  
Two paths: **CI builds** (automated, slow) and **local builds** (manual setup, then fast).

---

## Quick reference — local build (after first-time setup)

```bash
cd /path/to/retris
~/.buildozer-env/bin/buildozer android debug
adb uninstall org.kakoritz.retris
adb install bin/retris-*.apk
```

---

## 1. CI/CD Build Pipeline (GitHub Actions)

Every push to `main` (and every merge of `development → main`) automatically builds
an Android APK and publishes it to the `apk-latest` GitHub Release.

### Workflow file
`.github/workflows/android.yml`

### What it does
1. Checks out the repo on a Ubuntu runner
2. Installs buildozer + all Android SDK/NDK deps
3. Runs `buildozer android debug`
4. Uploads the resulting APK to the `apk-latest` release tag

### Cache key
The workflow caches the entire buildozer platform directory under the key:
```
buildozer-v4-<SHA256 of custom_recipes/pygame/__init__.py>
```
The SHA256 stamp ensures the cache is invalidated whenever the custom pygame recipe
changes. Without this, a stale `surface.so` (missing the SIMD fix) can persist
across builds and cause the game to crash on Android.

### Downloading the APK
1. Go to the repo's **Releases** page → `apk-latest`
2. Download `retris-X.X.X-arm64-v8a-debug.apk`
3. Enable *Install from unknown sources* on the device if needed
4. `adb install retris-X.X.X-arm64-v8a-debug.apk`

### CI build time
~20–30 minutes (cold) / ~10–15 minutes (cache hit on pygame recipe).

---

## 2. Local Build Setup (one-time)

Local builds are fast after the first run (~2–5 min for Python-only changes).

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python 3 | 3.10+ | `python3 --version` |
| Java JDK | 17+ (21 works) | `java -version` |
| Git | any | `git --version` |
| ADB | any | `adb version` |

### First-time setup

#### Step 1 — Create a venv for buildozer

**Critical:** Do NOT use the system Python on Debian/Ubuntu 22.04+.  
Python 3.12+ has PEP 668 "externally-managed-environment" which blocks `pip install`.
Buildozer internally calls `/usr/bin/python3 -m pip install ...` and will fail.
Running buildozer from a venv bypasses this entirely.

```bash
python3 -m venv ~/.buildozer-env
~/.buildozer-env/bin/pip install buildozer
```

#### Step 2 — Fix the spaces-in-path issue

**Critical:** python-for-android (p4a) rejects any build storage path that contains
spaces. If your project lives under a path with spaces (e.g. `VS CODE/FirstGame`),
the build will fail with:
```
ValueError: storage dir path cannot contain spaces
```

Fix: add a `build_dir` in `buildozer.spec` pointing to a space-free location:

```ini
[buildozer]
build_dir = /home/<user>/.retris-build
```

Or rename the project directory to remove spaces entirely (recommended long-term).

#### Step 3 — First build (30–60 min)

```bash
cd /path/to/retris
~/.buildozer-env/bin/buildozer android debug
```

The first run downloads and caches (~3 GB total):
- Android SDK command-line tools
- Android NDK r28c (~1.5 GB)
- python-for-android (p4a)
- Python 3.14 ARM64 cross-compiled
- pygame compiled from source (the custom recipe)
- numpy compiled from source

Everything is cached in `~/.buildozer/` and `~/.retris-build/`.

#### Step 4 — Accept SDK licenses

During the first run you will be prompted:
```
Do you accept the Android SDK license? (y/n)
```
Type `y`.

---

## 3. Subsequent local builds

After the first run, builds only recompile what changed:

| What changed | Build time |
|-------------|-----------|
| Python files only | ~2–3 min |
| Python files + assets | ~3–5 min |
| Custom pygame recipe changed | ~15–20 min (recompiles pygame) |
| First run ever | 30–60 min |

```bash
cd /path/to/retris
~/.buildozer-env/bin/buildozer android debug
```

APK lands in `bin/retris-<version>-arm64-v8a-debug.apk`.

---

## 4. Installing to device

```bash
# Wake screen (avoids false negatives on screenshots)
adb shell input keyevent KEYCODE_WAKEUP

# Uninstall old version (required if signing key changed between debug builds)
adb uninstall org.kakoritz.retris

# Install new build
adb install bin/retris-*.apk

# Launch immediately
adb shell am start -n org.kakoritz.retris/org.kivy.android.PythonActivity
```

### Keeping screen awake during testing

```bash
# Keep screen on while USB connected (persists until reboot)
adb shell svc power stayon usb

# Extend screen timeout to 30 min
adb shell settings put system screen_off_timeout 1800000
```

### Pulling crash logs

```bash
# Pull the boot crash log (written before pygame is available)
adb pull /data/data/org.kakoritz.retris/files/crash_latest.log

# Stream live Python output
adb logcat -v time | grep -i "python\|RETRIS" | grep -v "nativeloader\|extracting"
```

---

## 5. Custom pygame recipe — the SIMD fix

**This is the single most important piece of the Android build.**

### The problem

pygame 2.6.1's ARM64 Android build is missing two C source files from the surface
module compilation list:
- `src_c/simd_blitters_sse2.c`
- `src_c/simd_blitters_avx2.c`

Without them, the linker produces a `surface.so` that exports:
- `alphablit_alpha_sse2_argb_surf_alpha` (from sse2.c) — called by the blit path
- `pg_has_avx2` (from avx2.c) — referenced by the module init

When the game launches, Python loads `surface.so` and immediately crashes:
```
cannot locate symbol "alphablit_alpha_sse2_argb_surf_alpha"
```

### The fix

`custom_recipes/pygame/__init__.py` overrides p4a's built-in pygame recipe.
In `prebuild_arch()`, it patches the `Setup` file before compilation to inject
both missing files into the surface module source list for `arm64-v8a`:

```python
def prebuild_arch(self, arch):
    super().prebuild_arch(arch)
    if arch.arch == 'arm64-v8a':
        # patch Setup file to include SIMD sources
        ...
        surface_line = surface_line.replace(
            'src_c/surface.c',
            'src_c/surface.c src_c/simd_blitters_sse2.c src_c/simd_blitters_avx2.c'
        )
```

### Why the CI cache matters

If the cache serves a pre-fix `surface.so`, every subsequent build will use the
broken binary even if the recipe has been corrected. The SHA256 cache key in the
GitHub Actions workflow ensures any change to the recipe file busts the cache.

### Location
`custom_recipes/pygame/__init__.py`

Referenced in `buildozer.spec`:
```ini
p4a.local_recipes = ./custom_recipes
requirements = python3,pygame,numpy
```

---

## 6. buildozer.spec key settings

```ini
[app]
version         = 2.2.0
android.archs   = arm64-v8a      # 64-bit only (all phones since 2019)
orientation     = portrait
fullscreen      = 1

requirements    = python3,pygame,numpy
p4a.local_recipes = ./custom_recipes   # the SIMD fix
android.ndk     = 28c
android.api     = 33

[buildozer]
build_dir = /home/kakoritz/.retris-build   # must be a path with NO spaces
log_level = 2
```

---

## 7. Troubleshooting

### "cannot locate symbol" crash on launch
→ The SIMD fix didn't take effect.  
→ Check: does `custom_recipes/pygame/__init__.py` exist?  
→ Check: `p4a.local_recipes = ./custom_recipes` in buildozer.spec  
→ For CI: the cache may be stale — change the `buildozer-v4-` prefix in the workflow  
→ For local: delete `~/.retris-build/` and rebuild from scratch

### "storage dir path cannot contain spaces"
→ Your project path or build_dir contains a space  
→ Fix: set `build_dir = /home/<user>/<no-spaces-path>` in `[buildozer]`

### "externally-managed-environment" pip error
→ You're running buildozer with the system Python on Debian/Ubuntu 22.04+  
→ Fix: create a venv and run `~/.buildozer-env/bin/buildozer` instead

### APK installs but game is black screen
→ Device screen was locked; run `adb shell input keyevent KEYCODE_WAKEUP` first  
→ Or pull crash_latest.log for the real error

### Signature mismatch on reinstall
→ Debug keystores are regenerated per CI run  
→ Fix: always `adb uninstall org.kakoritz.retris` before installing a new debug APK

### Build hangs during first run
→ Downloading NDK (~1.5 GB) — this is normal, wait it out  
→ Check `/tmp/buildozer_local.log` for download progress

---

## 8. Carrying this to a new project

To replicate this entire setup for a new Python/pygame Android project:

1. Create `custom_recipes/pygame/__init__.py` with the SIMD patch (copy from this repo)
2. Set `p4a.local_recipes = ./custom_recipes` in buildozer.spec
3. Set `requirements = python3,pygame,numpy`
4. Set `android.archs = arm64-v8a` and `android.ndk = 28c`
5. Set `build_dir = /some/path/without/spaces` in `[buildozer]`
6. Run from `~/.buildozer-env/bin/buildozer` (not system buildozer)
7. For CI: copy `.github/workflows/android.yml` and update the cache key prefix

The custom recipe and the venv + spaces fix are the two things nobody documents well.
Everything else is standard buildozer.
