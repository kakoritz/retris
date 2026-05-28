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
    p = os.environ.get('ANDROID_PRIVATE')
    return Path(p) if p else Path(__file__).parent.parent


_FILE = _data_dir() / "config.json"

_DEFAULTS = {"scale": 1.5, "ghost_opacity": 15, "das_preset": "normal"}

VALID_SCALES = [1.0, 1.5, 2.0, 2.5]

VALID_DAS_PRESETS = ["slow", "normal", "fast", "instant"]
# (delay_ms, repeat_ms) per preset
DAS_SETTINGS = {
    "slow":    (250, 100),
    "normal":  (170,  50),
    "fast":    (120,  30),
    "instant": (100,   0),
}


def load() -> dict:
    """Read config.json; return defaults on missing file or parse error."""
    if not _FILE.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_FILE.read_text())
        # Snap scale to the nearest valid value in case the file was hand-edited.
        s = data.get("scale", _DEFAULTS["scale"])
        if s not in VALID_SCALES:
            s = min(VALID_SCALES, key=lambda v: abs(v - s))
        data["scale"] = s
        data["ghost_opacity"] = max(0, min(100, int(
            data.get("ghost_opacity", _DEFAULTS["ghost_opacity"]))))
        return data
    except Exception:
        return dict(_DEFAULTS)


def save(data: dict) -> None:
    """Write config dict to disk; silently no-ops on permission errors."""
    try:
        _FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def get_scale() -> float:
    return load()["scale"]


def set_scale(s: float) -> None:
    data = load()
    data["scale"] = s
    save(data)


def get_ghost_opacity() -> int:
    return load()["ghost_opacity"]


def set_ghost_opacity(pct: int) -> None:
    data = load()
    data["ghost_opacity"] = max(0, min(100, int(pct)))
    save(data)


def get_das_preset() -> str:
    return load().get("das_preset", "normal")


def set_das_preset(preset: str) -> None:
    data = load()
    data["das_preset"] = preset if preset in VALID_DAS_PRESETS else "normal"
    save(data)
