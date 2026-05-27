import json
from pathlib import Path

_FILE = Path(__file__).parent / "config.json"

_DEFAULTS = {"scale": 1.5}

VALID_SCALES = [1.0, 1.5, 2.0, 2.5]


def load() -> dict:
    if not _FILE.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_FILE.read_text())
        # Clamp scale to a valid value
        s = data.get("scale", _DEFAULTS["scale"])
        if s not in VALID_SCALES:
            s = min(VALID_SCALES, key=lambda v: abs(v - s))
        data["scale"] = s
        return data
    except Exception:
        return dict(_DEFAULTS)


def save(data: dict) -> None:
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
