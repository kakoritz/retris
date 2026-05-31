"""
config.py — persistent user settings (config.json).

Settings are read fresh from disk on every get_* call so that changes made by
one part of the game are immediately visible to another without restart.
Missing or corrupt config.json silently falls back to _DEFAULTS.
"""
import json
import os
from pathlib import Path


def _data_dir() -> Path:
    import sys
    if sys.platform == "emscripten":
        return Path("/tmp")
    p = os.environ.get('ANDROID_PRIVATE')
    return Path(p) if p else Path(__file__).parent.parent


_FILE = _data_dir() / "config.json"

_DEFAULTS = {
    "scale":        1.5,
    "ghost_opacity": 15,
    "das_preset":   "normal",
    "music_vol":    40,
    "sfx_vol":      100,
    "game_speed":   "fast",   # mobile default set separately in main.py
}

VALID_SCALES = [1.0, 1.5, 2.0, 2.5]

VALID_DAS_PRESETS = ["slow", "normal", "fast", "instant"]
DAS_SETTINGS = {
    "slow":    (250, 100),
    "normal":  (170,  50),
    "fast":    (120,  30),
    "instant": (100,   0),
}

VALID_GAME_SPEEDS = ["slow", "medium", "fast"]
# Multiplier applied to fall_speed() result (>1 = slower)
GAME_SPEED_MULT = {
    "slow":   2.0,    # 0.5× speed — mobile default
    "medium": 1.33,   # 0.75× speed
    "fast":   1.0,    # 1.0× speed — PC default
}


def load() -> dict:
    """Read config.json; return defaults on missing file or parse error."""
    if not _FILE.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_FILE.read_text())
        s = data.get("scale", _DEFAULTS["scale"])
        if s not in VALID_SCALES:
            s = min(VALID_SCALES, key=lambda v: abs(v - s))
        data["scale"]        = s
        data["ghost_opacity"] = max(0, min(200, int(
            data.get("ghost_opacity", _DEFAULTS["ghost_opacity"]))))
        data["music_vol"]    = max(0, min(100, int(
            data.get("music_vol", _DEFAULTS["music_vol"]))))
        data["sfx_vol"]      = max(0, min(100, int(
            data.get("sfx_vol", _DEFAULTS["sfx_vol"]))))
        gs = data.get("game_speed", _DEFAULTS["game_speed"])
        data["game_speed"]   = gs if gs in VALID_GAME_SPEEDS else "fast"
        return data
    except Exception:
        return dict(_DEFAULTS)


def save(data: dict) -> None:
    """Write config dict to disk; silently no-ops on permission errors."""
    try:
        _FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def _update(key, value):
    data = load(); data[key] = value; save(data)


def get_scale() -> float:
    return load()["scale"]

def set_scale(s: float) -> None:
    _update("scale", s)

def get_ghost_opacity() -> int:
    return load()["ghost_opacity"]

def set_ghost_opacity(pct: int) -> None:
    _update("ghost_opacity", max(0, min(200, int(pct))))

def get_das_preset() -> str:
    return load().get("das_preset", "normal")

def set_das_preset(preset: str) -> None:
    _update("das_preset", preset if preset in VALID_DAS_PRESETS else "normal")

def get_music_vol() -> int:
    return load().get("music_vol", _DEFAULTS["music_vol"])

def set_music_vol(pct: int) -> None:
    _update("music_vol", max(0, min(100, int(pct))))

def get_sfx_vol() -> int:
    return load().get("sfx_vol", _DEFAULTS["sfx_vol"])

def set_sfx_vol(pct: int) -> None:
    _update("sfx_vol", max(0, min(100, int(pct))))

def get_game_speed() -> str:
    return load().get("game_speed", "fast")

def set_game_speed(speed: str) -> None:
    _update("game_speed", speed if speed in VALID_GAME_SPEEDS else "fast")
