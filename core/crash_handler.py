# crash_handler.py — unhandled-exception logger and crash window
#
# Usage (bottom of main.py):
#   if __name__ == "__main__":
#       from crash_handler import run_with_crash_handler
#       run_with_crash_handler(main)
#
# On an unhandled exception this module:
#   1. Prints the traceback to stderr (so the terminal still shows it)
#   2. Writes crash_YYYYMMDD_HHMMSS.log next to main.py
#   3. Also writes crash_latest.log (overwritten each crash — easy to find)
#   4. Attempts to show a pygame crash window with the error + log path
#   5. Exits with code 1

import sys
import os
import traceback
import datetime

import pygame

_HERE = os.environ.get('ANDROID_PRIVATE') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_W, _H  = 640, 420
_BG     = (10,  10,  20)
_RED    = (255, 60,  60)
_ORANGE = (255, 160, 40)
_WHITE  = (215, 215, 225)
_GRAY   = (130, 130, 155)
_DIM    = (55,  55,  80)


def _write_logs(tb_text: str) -> str:
    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    stamp    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header   = (
        f"RETRIS Crash Report\n"
        f"{'=' * 72}\n"
        f"Time   : {stamp}\n"
        f"Python : {sys.version}\n"
        f"{'=' * 72}\n\n"
        f"{tb_text}"
    )
    named = os.path.join(_HERE, f"crash_{ts}.log")
    latest = os.path.join(_HERE, "crash_latest.log")
    for path in (named, latest):
        try:
            with open(path, "w") as f:
                f.write(header)
        except OSError:
            pass
    return named


def _show_crash_window(tb_text: str, log_path: str) -> None:
    try:
        # Reset display in case the game left it in a bad state
        try:
            pygame.display.quit()
        except Exception:
            pass
        if not pygame.get_init():
            pygame.init()
        pygame.display.init()

        screen = pygame.display.set_mode((_W, _H))
        pygame.display.set_caption("RETRIS — Unexpected Error")

        font_title  = pygame.font.SysFont("monospace", 19, bold=True)
        font_sub    = pygame.font.SysFont("monospace", 13)
        font_body   = pygame.font.SysFont("monospace", 12)
        font_footer = pygame.font.SysFont("monospace", 11)

        # Show only the last portion of the traceback that fits on screen
        tb_lines = tb_text.strip().splitlines()
        max_body_lines = 18
        if len(tb_lines) > max_body_lines:
            tb_lines = ["... (truncated)", ""] + tb_lines[-max_body_lines:]

        clock   = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    running = False

            screen.fill(_BG)

            # ── title bar ─────────────────────────────────────────────────
            t = font_title.render("RETRIS crashed unexpectedly", True, _RED)
            screen.blit(t, (20, 18))

            t = font_sub.render("A crash log has been saved to:", True, _WHITE)
            screen.blit(t, (20, 50))

            # Log path — truncate from the left if too long
            log_display = log_path
            max_chars   = 80
            if len(log_display) > max_chars:
                log_display = "…" + log_display[-(max_chars - 1):]
            t = font_footer.render(log_display, True, _ORANGE)
            screen.blit(t, (20, 68))

            pygame.draw.line(screen, _DIM, (20, 90), (_W - 20, 90), 1)

            # ── traceback body ────────────────────────────────────────────
            y = 100
            for line in tb_lines:
                if y > _H - 44:
                    break
                stripped = line.strip()
                if stripped.startswith("Traceback") or stripped.startswith("File "):
                    col = _GRAY
                elif stripped.startswith(("Error", "Exception", "TypeError",
                                          "ValueError", "AttributeError",
                                          "NameError", "KeyError")):
                    col = _RED
                elif stripped.startswith("During handling"):
                    col = _ORANGE
                else:
                    col = _WHITE

                # Hard-wrap lines that are too wide
                display_line = line[:100]
                t = font_body.render(display_line, True, col)
                screen.blit(t, (20, y))
                y += 16

            pygame.draw.line(screen, _DIM, (20, _H - 34), (_W - 20, _H - 34), 1)

            t = font_footer.render(
                "Press any key or close this window to exit", True, _DIM)
            screen.blit(t, (20, _H - 22))

            pygame.display.flip()
            clock.tick(30)

    except Exception:
        pass
    finally:
        try:
            pygame.quit()
        except Exception:
            pass


def run_with_crash_handler(fn) -> None:
    """Run fn(). On any unhandled exception: log it, show crash window, exit 1."""
    try:
        fn()
    except (SystemExit, KeyboardInterrupt):
        # Normal exit paths — don't intercept
        raise
    except Exception:
        tb_text = traceback.format_exc()
        print(tb_text, file=sys.stderr)
        log_path = _write_logs(tb_text)
        print(f"\nCrash log written to: {log_path}", file=sys.stderr)
        _show_crash_window(tb_text, log_path)
        sys.exit(1)
