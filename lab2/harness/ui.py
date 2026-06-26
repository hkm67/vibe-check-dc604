from __future__ import annotations

import re
import shutil
import sys
import threading
import time
import textwrap
from contextlib import contextmanager


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"


def color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def width() -> int:
    return min(shutil.get_terminal_size((100, 24)).columns, 110)


def _strip_ansi(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _pad(s: str, w: int) -> str:
    """ljust that ignores ANSI escape codes when measuring length."""
    visible = len(_strip_ansi(s))
    return s + " " * max(0, w - visible)


def rule(title: str = "") -> None:
    cols = width()
    if title:
        label = f" {title} "
        line = label.center(cols, "=")
    else:
        line = "=" * cols
    print(color(line, DIM))


def panel(title: str, body: str, tone: str = BLUE) -> None:
    cols = width()
    inner = cols - 4
    print(color("+" + "-" * (cols - 2) + "+", tone))
    print(color("|", tone) + " " + color(title[:inner].ljust(inner), BOLD) + " " + color("|", tone))
    print(color("+" + "-" * (cols - 2) + "+", tone))
    for paragraph in body.splitlines() or [""]:
        if not paragraph:
            print(color("|", tone) + " " * (cols - 2) + color("|", tone))
            continue
        for line in textwrap.wrap(paragraph, width=inner, replace_whitespace=False) or [""]:
            print(color("|", tone) + " " + line.ljust(inner) + " " + color("|", tone))
    print(color("+" + "-" * (cols - 2) + "+", tone))


def banner(repo_path: str, mode: str, provider: str, model_name: str) -> None:
    cols = width()
    left_w = 48
    right_w = cols - left_w - 3  # 3 = │ + │ + │ borders
    if right_w < 28:
        # terminal too narrow — fall back to simple rule
        rule("Vibe Code")
        return

    title = " Vibe Code "
    inner = cols - 2
    top = color("╭" + "─" * 3 + title + "─" * (inner - 3 - len(title)) + "╮", DIM)
    bot = color("╰" + "─" * inner + "╯", DIM)
    sep = color("│", DIM)

    def row(left: str = "", right: str = "") -> None:
        print(sep + _pad(left, left_w) + sep + _pad(right, right_w) + sep)

    prefix_len = len("  ❉  repo      ")
    max_path = left_w - prefix_len - 1
    rp = repo_path if len(repo_path) <= max_path else "…" + repo_path[-(max_path - 1):]

    # Truncate model name with a leading ellipsis if it would overflow the
    # left column. Visible prefix is "  ❉  provider  <provider>  ·  ".
    model_prefix_len = len(f"  ❉  provider  {provider}  ·  ")
    max_model = left_w - model_prefix_len - 1
    if max_model < 4:
        max_model = 4
    mn = model_name if len(model_name) <= max_model else "…" + model_name[-(max_model - 1):]

    stage_colors = {
        "yolo": RED,
        "truncated-approval": RED,
        "first-token-allowlist": YELLOW,
        "strict-shell": YELLOW,
        "command-denylist": GREEN,
    }
    stage_numbers = {
        "yolo": 1,
        "truncated-approval": 2,
        "first-token-allowlist": 3,
        "strict-shell": 4,
        "command-denylist": 5,
    }
    stage_n = stage_numbers.get(mode, "?")
    stage_str = color(f"{stage_n}", stage_colors.get(mode, RESET))

    mascot_plain = "( ▀_▀ )"
    arms_plain = " ╲     ╱ "
    laptop_top = "╭█─────█╮"
    laptop_screen = "│rm -rf │"
    laptop_base = "╰═══════╯"
    wordmark_plain = "v · i · b · e   c · o · d · e"
    tagline_plain = "homegrown harness · vibes only"
    spark = color("❉", YELLOW)
    left_lines: list[str] = [
        "",
        color(mascot_plain.center(left_w), YELLOW),
        color(arms_plain.center(left_w), YELLOW),
        color(laptop_top.center(left_w), YELLOW),
        color(laptop_screen.center(left_w), YELLOW),
        color(laptop_base.center(left_w), YELLOW),
        color(wordmark_plain.center(left_w), BOLD + YELLOW),
        color(tagline_plain.center(left_w), DIM),
        color(("─" * len(wordmark_plain)).center(left_w), DIM),
        "",
        f"  {spark}  stage     " + stage_str,
        f"  {spark}  provider  {provider}  ·  {mn}",
        f"  {spark}  repo      {rp}",
        "",
    ]

    div = "  " + "─" * (right_w - 3)
    right_lines: list[str] = [
        "",
        color("  Commands", BOLD),
        div,
        "  /stage <n>     switch hardening stage (1..5)",
        "  /scan          list repo files",
        "  /log           recent audit events",
        "  /raw           last model response",
        "  /quit          exit",
        "",
        color("  /help", DIM) + color(" for the full list", DIM),
        "",
    ]

    n = max(len(left_lines), len(right_lines))
    left_lines += [""] * (n - len(left_lines))
    right_lines += [""] * (n - len(right_lines))

    print(top)
    for l, r in zip(left_lines, right_lines):
        row(l, r)
    print(bot)


def badge(label: str, tone: str) -> str:
    return color(f"[{label}]", tone)


def truncate(text: str, limit: int = 76) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


@contextmanager
def spinner(message: str):
    done = threading.Event()
    frames = [
        "( ◐_◐ )",
        "( ◉_◉ )",
        "( ◑_◑ )",
        "( ◉_◉ )",
        "( -_- )",
        "( ◉_◉ )",
    ]
    frame_width = max(len(f) for f in frames)
    max_dots = 3
    base_message = message.rstrip(".")

    def animate() -> None:
        index = 0
        while not done.is_set():
            frame = frames[index % len(frames)]
            dots = "." * (index % (max_dots + 1))
            line = color(frame, YELLOW) + " " + base_message + dots
            pad = " " * (max_dots - len(dots))
            sys.stdout.write("\r" + line + pad)
            sys.stdout.flush()
            index += 1
            time.sleep(0.18)
        sys.stdout.write("\r" + " " * (len(base_message) + frame_width + max_dots + 2) + "\r")
        sys.stdout.flush()

    thread = threading.Thread(target=animate, daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join()
