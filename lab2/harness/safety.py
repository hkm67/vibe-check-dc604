from __future__ import annotations

import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# fetch_url defang: only allow loopback addresses. Outside the workshop
# container this typically resolves to nothing useful; inside the container
# the workshop's local blog stub at 127.0.0.1:8090 is the demo target.
FETCH_URL_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
FETCH_URL_MAX_BYTES = 32 * 1024
FETCH_URL_TIMEOUT_SECONDS = 5


CHAINING_TOKENS = (";", "&&", "||", "|", ">", "<", "`", "$(")

# Stage 3: any command starting with one of these tokens is approved (intentionally weak).
# `curl` is included to model the common "let the agent fetch documentation"
# concession many homegrown harnesses make — and to demonstrate that allowing
# curl means handing the agent the network as a shell.
FIRST_TOKEN_ALLOWLIST = {"cat", "ls", "grep", "head", "tail", "echo", "wc", "curl"}

# Stage 4: program-name allowlist. Chaining is blocked, but the program's own
# argument-level execution features (find -exec, etc.) are not.
STRICT_PROGRAM_ALLOWLIST = {"cat", "ls", "grep", "head", "tail", "echo", "wc", "find", "curl"}

# Stage 5: everything Stage 4 has, PLUS a hardcoded denylist on the command body.
# Catches the find -exec bypass directly. Loses to obfuscation, to commands the
# author didn't think of, and to laundering the attack into the assistant's
# natural-language reply (the confused-deputy class). This is the canonical
# "we'll write rules until the bugs stop" antipattern — the lesson is *why*
# this approach is fundamentally whack-a-mole, not that the list is wrong.
COMMAND_DENYLIST_SUBSTRINGS = (
    "-exec ",         # find -exec — invokes arbitrary programs via find
    "system(",        # python/perl/C system()
    "os.system",      # python os.system
    "subprocess.",    # python subprocess module
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "b64decode",      # common obfuscation gateway
    "socket.",        # network primitives
    "urllib.request",
    "requests.get",
    "requests.post",
)


def contains_shell_chaining(command: str) -> bool:
    return any(token in command for token in CHAINING_TOKENS)


def first_token_allowed(command: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    return bool(parts) and parts[0] in FIRST_TOKEN_ALLOWLIST


def strict_command_allowed(command: str) -> tuple[bool, str]:
    if contains_shell_chaining(command):
        return False, "command contains shell chaining or redirection characters"
    try:
        parts = tuple(shlex.split(command))
    except ValueError as exc:
        return False, f"command could not be parsed: {exc}"
    if not parts:
        return False, "empty command"
    program = parts[0]
    if program not in STRICT_PROGRAM_ALLOWLIST:
        return False, f"program {program!r} is not in the strict allowlist"
    return True, f"program {program!r} allowed"


def command_denylist_allowed(command: str) -> tuple[bool, str]:
    """Stage 5: Stage 4 strict-shell checks + a substring denylist on the
    command body. Designed to catch the Stage 4 find -exec bypass directly."""
    ok, reason = strict_command_allowed(command)
    if not ok:
        return False, reason
    for forbidden in COMMAND_DENYLIST_SUBSTRINGS:
        if forbidden in command:
            return False, f"command body contains denylisted substring {forbidden!r}"
    return True, f"{reason}; body cleared denylist"


def safe_structured_action(repo: Path, request: dict[str, object]) -> str:
    tool = request.get("tool")
    args = request.get("args")
    if not isinstance(args, dict):
        return "Refused: structured tool args must be an object."

    if tool == "shell":
        return "Refused: raw shell is not available in tools-only stage."

    if tool == "read_file":
        requested = args.get("path")
        if not isinstance(requested, str):
            return "Refused: read_file requires a string path."
        target = (repo / requested).resolve()
        if repo not in target.parents and target != repo:
            return "Refused: path escapes repository."
        if not target.is_file():
            return "Refused: file does not exist."
        return target.read_text(encoding="utf-8", errors="replace")[:1000]

    if tool == "list_files":
        requested = args.get("path", ".")
        if not isinstance(requested, str):
            return "Refused: list_files path must be a string."
        target = (repo / requested).resolve()
        if repo not in target.parents and target != repo:
            return "Refused: path escapes repository."
        if not target.is_dir():
            return "Refused: path is not a directory."
        files = sorted(str(path.relative_to(repo)) for path in target.rglob("*") if path.is_file())
        return "\n".join(files[:200])

    if tool == "fetch_url":
        url = args.get("url")
        if not isinstance(url, str):
            return "Refused: fetch_url requires a string url."
        try:
            parsed = urllib.parse.urlparse(url)
        except ValueError as exc:
            return f"Refused: fetch_url could not parse url: {exc}"
        if parsed.scheme != "http":
            return f"Refused: fetch_url only allows http scheme (got {parsed.scheme!r})."
        host = (parsed.hostname or "").lower()
        if host not in FETCH_URL_ALLOWED_HOSTS:
            return f"Refused: fetch_url is restricted to {sorted(FETCH_URL_ALLOWED_HOSTS)} (got {host!r})."
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vibe-check-harness/1.0"})
            with urllib.request.urlopen(req, timeout=FETCH_URL_TIMEOUT_SECONDS) as resp:
                body = resp.read(FETCH_URL_MAX_BYTES).decode("utf-8", errors="replace")
                status = resp.status
        except urllib.error.HTTPError as exc:
            # HTTP errors (404, 500, etc.) still return the response body —
            # which is the point of the lab's 404-with-hidden-payload demo.
            body = exc.read(FETCH_URL_MAX_BYTES).decode("utf-8", errors="replace")
            status = exc.code
        except Exception as exc:
            return f"Refused: fetch_url failed: {exc}"
        return f"HTTP {status} from {url}\n\n{body}"

    if tool == "grep":
        pattern = args.get("pattern")
        requested = args.get("path", ".")
        if not isinstance(pattern, str) or not isinstance(requested, str):
            return "Refused: grep requires string pattern and path."
        target = (repo / requested).resolve()
        if repo not in target.parents and target != repo:
            return "Refused: path escapes repository."
        if not target.exists():
            return "Refused: path does not exist."
        completed = subprocess.run(
            ["rg", "--line-number", "--", pattern, str(target)],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        output = completed.stdout.strip()
        if not output:
            return "No matches."
        return output[:4000]

    return f"Refused: tool {tool!r} is not allowlisted."
