"""
updater.py — background GitHub release checker.

Spawns a daemon thread on construction; safe to call from any state.
Read `.status` and `.release_notes` from the main thread at any time.
"""
import json
import re
import threading
import urllib.request

REPO         = "kakoritz/retris"
DOWNLOAD_URL = f"https://github.com/{REPO}/releases/tag/apk-latest"
_API         = f"https://api.github.com/repos/{REPO}/releases?per_page=20"


def _parse_ver(tag: str) -> tuple:
    try:
        return tuple(int(x) for x in tag.lstrip("v").split("."))
    except (ValueError, AttributeError):
        return (0,)


def _strip_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`",        r"\1", text)
    text = re.sub(r"^#{1,6}\s*",    "",   text, flags=re.M)
    text = re.sub(r"^[-*]\s+",      "• ", text, flags=re.M)
    return text.strip()


class UpdateChecker:
    """
    Attributes (thread-safe reads; only the worker thread writes after init):
      status          "checking" | "up_to_date" | "available" | "offline" | "error"
      current_version str  e.g. "1.11.0"
      latest_version  str | None
      release_notes   list[(version_str, body_str)]  newest-first
    """

    def __init__(self, current_version: str) -> None:
        self.current_version: str        = current_version
        self.status:          str        = "checking"
        self.latest_version:  str | None = None
        self.release_notes:   list       = []
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            req = urllib.request.Request(
                _API, headers={"User-Agent": "RETRIS-updater/1.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                releases = json.loads(resp.read().decode())

            cur    = _parse_ver(self.current_version)
            newer  = []
            for rel in releases:
                tag = rel.get("tag_name", "")
                if tag in ("apk-latest", ""):
                    continue
                if _parse_ver(tag) > cur:
                    newer.append((tag.lstrip("v"), _strip_md(rel.get("body", ""))))

            newer.sort(key=lambda x: _parse_ver(x[0]), reverse=True)

            if newer:
                self.latest_version = newer[0][0]
                self.release_notes  = newer
                self.status         = "available"
            else:
                self.status = "up_to_date"

        except OSError:
            self.status = "offline"
        except Exception:
            self.status = "error"
