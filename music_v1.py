"""
RetroTetris chiptune v1 — original 4-bar A-minor loop.
Preserved so it can be selected as an alternate track.
"""
import os
import wave
import tempfile
import pygame

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

_RATE     = 44100
_tmp_path = None


def _note(freq, ms, vol, decay=0.7):
    if freq == 0:
        return np.zeros(int(_RATE * ms / 1000))
    n    = int(_RATE * ms / 1000)
    t    = np.linspace(0, ms / 1000, n, endpoint=False)
    w    = np.sign(np.sin(2 * np.pi * freq * t)) * vol * np.exp(-decay * t)
    fade = min(int(_RATE * 0.010), n // 4)
    if fade > 0:
        r = 0.5 * (1 - np.cos(np.pi * np.arange(fade) / fade))
        w[:fade] *= r
        w[-fade:] *= r[::-1]
    return w


def _build() -> np.ndarray:
    BPM   = 162
    Q     = int(60000 / BPM)
    H     = Q * 2
    WHOLE = Q * 4

    melody = [
        (659, Q), (587, Q), (523, Q), (494, Q),
        (440, Q), (523, Q), (659, Q), (880, Q),
        (784, Q), (659, Q), (587, Q), (523, Q),
        (494, Q), (440, Q), (440, H),
    ]
    bass = [(110, WHOLE), (110, WHOLE), (131, WHOLE), (82, WHOLE)]

    mel   = np.concatenate([_note(f, ms, 0.030, 0.8)  for f, ms in melody])
    bas   = np.concatenate([_note(f, ms, 0.014, 0.35) for f, ms in bass])

    n   = len(mel)
    bas = bas[:n] if len(bas) >= n else np.pad(bas, (0, n - len(bas)))

    mixed = mel + bas
    peak  = np.max(np.abs(mixed))
    if peak > 0:
        mixed = mixed / peak * 0.18

    pcm    = (mixed * 32767).astype(np.int16)
    return np.ascontiguousarray(np.column_stack([pcm, pcm]))


def _write_wav(data, path):
    with wave.open(path, 'w') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(_RATE)
        f.writeframes(data.tobytes())


def load_and_play(vol: float = 0.40) -> None:
    """Build (once) and stream this track via pygame.mixer.music."""
    global _tmp_path
    if not _HAS_NP:
        return
    try:
        if _tmp_path is None:
            _tmp_path = os.path.join(tempfile.gettempdir(), "nes_tetris_music_v1.wav")
            _write_wav(_build(), _tmp_path)
        pygame.mixer.music.load(_tmp_path)
        pygame.mixer.music.set_volume(vol)
        pygame.mixer.music.play(loops=-1)
    except Exception:
        pass
