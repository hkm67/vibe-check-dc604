"""Lab 2 harness — CLI / chat loop / ReAct loop.

Conceptually mirrors the chat loop in OpenAI Codex CLI, Aider, and
opencode:

- Outer `while True` for user turns (`cmd_chat`)
- Inner `while True` ReAct loop: model proposes a tool call → harness
  policy enforces → tool runs (or is refused) → result is reinjected
  into the model's context → model adapts → repeat until the model
  emits a plain message and the inner loop exits

This is a real ReAct loop with tool-result reinjection. It is what
makes the Stage 3 → Stage 4 transition demonstrable: when Stage 3
refuses a chained `cat ... ; python ...`, the refusal is fed back to
the model, which then adapts and falls back to `find ... -exec python ... +`
from the AGENTS.md instructions.

What we don't have here (deliberate workshop scope): OS sandboxing for
shell execution, context compaction, session persistence, MCP / skill
extensibility, sub-agent / parallel execution. See
`resources/harness-architecture.md` for the full comparison.
"""

from __future__ import annotations

import argparse
import json
import readline  # noqa: F401 — enables arrow-key editing and history in input()
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from .providers import ask_model, load_agent_instructions, resolve_model
from .safety import (
    CHAINING_TOKENS,
    COMMAND_DENYLIST_SUBSTRINGS,
    FIRST_TOKEN_ALLOWLIST,
    STRICT_PROGRAM_ALLOWLIST,
    command_denylist_allowed,
    contains_shell_chaining,
    first_token_allowed,
    safe_structured_action,
    strict_command_allowed,
)
from .ui import BLUE, BOLD, CYAN, GREEN, MAGENTA, RED, YELLOW, badge, banner, color, panel, rule, spinner, truncate

STAGES = (
    "yolo",
    "truncated-approval",
    "first-token-allowlist",
    "strict-shell",
    "command-denylist",
)
STAGE_ALIASES = {str(i): name for i, name in enumerate(STAGES, start=1)}
STAGE_LABELS = {
    "yolo": "Skipping Approval (YOLO Mode)",
    "truncated-approval": "Manual Approval",
    "first-token-allowlist": "Auto Approval (Allowlist)",
    "strict-shell": "Auto Approval (Allowlist, no chaining)",
    "command-denylist": "Auto Approval (Allowlist + Denylist)",
}


def stage_argtype(value: str) -> str:
    """Argparse type for --stage. Accepts the full stage name or its 1-based numeric alias."""
    if value in STAGES:
        return value
    if value in STAGE_ALIASES:
        return STAGE_ALIASES[value]
    raise argparse.ArgumentTypeError(
        f"invalid stage: {value!r} (choose 1-{len(STAGES)})"
    )


def read_context(repo: Path) -> dict[str, str]:
    context: dict[str, str] = {}
    for path in sorted(repo.iterdir()):
        if path.is_file():
            try:
                context[path.name] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    return context


def log_event(repo: Path, event: dict[str, object]) -> None:
    log_dir = repo / ".lab-logs"
    log_dir.mkdir(exist_ok=True)
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    with (log_dir / "harness-events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def cmd_scan(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    context = read_context(repo)
    print(f"Scanned {repo}")
    for name, body in context.items():
        print(f"- {name}: {len(body)} bytes")
    if not context:
        print("No files found at repo root.")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    context = read_context(repo)
    response = ask_model(args.provider, args.task, context, args.model, repo=repo)
    log_event(repo, {"type": "ask", "provider": args.provider, "model": args.model, "task": args.task, "response": response})
    print(response)
    return 0


def preview_command(command: str, show_full: bool) -> str:
    if show_full or len(command) <= 72:
        return command
    return command[:72] + "..."


def approve(prompt: str) -> bool:
    answer = input(prompt).strip().lower()
    return answer in {"", "y", "yes"}


def strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def execute_command(repo: Path, command: str) -> tuple[int, str, str]:
    completed = subprocess.run(command, cwd=repo, shell=True, check=False, capture_output=True, text=True)
    if completed.stdout:
        panel("Tool Output", completed.stdout.rstrip(), GREEN)
    if completed.stderr:
        panel("Tool Alert", strip_ansi(completed.stderr).rstrip(), RED)
    return completed.returncode, completed.stdout, completed.stderr


def stage_index(stage: str) -> int:
    return STAGES.index(stage) + 1


def render_stage(stage: str) -> None:
    idx = stage_index(stage)
    label = STAGE_LABELS.get(stage, "")
    title = f"Stage {idx} · {label}" if label else f"Stage {idx}"
    body_lines = ["active"]
    if stage == "first-token-allowlist":
        allowlist = ", ".join(sorted(FIRST_TOKEN_ALLOWLIST))
        body_lines += ["", f"Allowed first tokens: {allowlist}"]
    elif stage == "strict-shell":
        progs = ", ".join(sorted(STRICT_PROGRAM_ALLOWLIST))
        chains = " ".join(CHAINING_TOKENS)
        body_lines += [
            "",
            f"Allowed programs: {progs}",
            f"Blocked chaining tokens: {chains}",
        ]
    elif stage == "command-denylist":
        progs = ", ".join(sorted(STRICT_PROGRAM_ALLOWLIST))
        chains = " ".join(CHAINING_TOKENS)
        deny = ", ".join(COMMAND_DENYLIST_SUBSTRINGS)
        body_lines += [
            "",
            f"Allowed programs: {progs}",
            f"Blocked chaining tokens: {chains}",
            f"Denied substrings in command body: {deny}",
        ]
    panel(title, "\n".join(body_lines), MAGENTA)


def resolve_stage(token: str) -> str | None:
    token = token.strip()
    if token in STAGES:
        return token
    if token in STAGE_ALIASES:
        return STAGE_ALIASES[token]
    return None


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and start < end:
        return stripped[start : end + 1]
    return stripped


def parse_model_output(repo: Path, provider: str, model: str | None, task: str, history: str = "") -> tuple[dict[str, object] | None, str]:
    context = read_context(repo)
    with spinner("vibing..."):
        model_output = ask_model(provider, task, context, model, history, repo=repo)
    try:
        parsed = json.loads(extract_json_object(model_output))
    except json.JSONDecodeError:
        panel("Model Error", "Model did not return JSON. Refusing to run.", RED)
        log_event(repo, {"type": "refuse", "reason": "invalid_json", "model_output": model_output})
        return None, model_output
    return parsed, model_output


def enforce_stage(repo: Path, parsed: dict[str, object], stage: str) -> tuple[bool, str]:
    command = command_from_tool_call(parsed)
    tool = str(parsed.get("tool", ""))
    if tool != "shell":
        return True, f"structured tool {tool!r} allowed"
    if stage in {"yolo", "truncated-approval"}:
        return True, "no command policy at this stage"
    if stage == "first-token-allowlist":
        if first_token_allowed(command):
            return True, "first token allowed"
        return False, "first command token is not allowlisted"
    if stage == "strict-shell":
        return strict_command_allowed(command)
    if stage == "command-denylist":
        return command_denylist_allowed(command)
    return False, f"unknown stage: {stage}"


FULL_PREVIEW_STAGES = {"strict-shell", "command-denylist"}
NO_APPROVAL_STAGES = {"yolo", "first-token-allowlist", "strict-shell", "command-denylist"}


def render_proposal(parsed: dict[str, object], stage: str) -> None:
    if parsed.get("type") == "message":
        panel("Assistant", str(parsed.get("content", "")), CYAN)
        return

    action = str(parsed.get("action", "No action summary supplied."))
    command = command_from_tool_call(parsed)
    tool = str(parsed.get("tool", ""))
    args = parsed.get("args", {})

    panel("Assistant", action, CYAN)
    if stage == "tools-only" or tool != "shell":
        panel("Structured Tool Proposal", f"tool: {tool}\nargs: {json.dumps(args, sort_keys=True)}", BLUE)
        return

    preview = command if stage in FULL_PREVIEW_STAGES else truncate(command)
    title = "Shell Tool Call" if stage in NO_APPROVAL_STAGES else "Tool Call Approval Preview"
    panel(title, preview, YELLOW)


def execute_or_tool(repo: Path, parsed: dict[str, object], stage: str, dry_run: bool) -> dict[str, object]:
    tool = str(parsed.get("tool", ""))
    if tool != "shell":
        result = safe_structured_action(repo, parsed)
        panel("Tool Result", result, GREEN)
        log_event(repo, {"type": "safe_tool", "request": parsed, "result": result})
        return {"tool": tool, "ok": not result.startswith("Refused:"), "result": result}

    command = command_from_tool_call(parsed)
    if dry_run:
        panel("Dry Run", "Command approved, but dry-run mode prevented execution.", YELLOW)
        return {"tool": "shell", "ok": True, "result": "Dry run: command not executed.", "returncode": 0}
    rc, stdout, stderr = execute_command(repo, command)
    log_event(repo, {"type": "execute", "returncode": rc, "command": command, "stage": stage})
    print(color(f"Command exited with {rc}", GREEN if rc == 0 else RED))
    return {"tool": "shell", "ok": rc == 0, "result": stdout.strip(), "returncode": rc}


def command_from_tool_call(parsed: dict[str, object]) -> str:
    args = parsed.get("args", {})
    if isinstance(args, dict):
        return str(args.get("command", parsed.get("command", "")))
    return str(parsed.get("command", ""))


def print_chat_help() -> None:
    print(
        textwrap.dedent(
            """
            Commands:
              /help                  show this help
              /stage                 show current stage
              /stage <n>             switch stage (1..5); clears chat history
              /clear                 clear chat history (keeps stage and repo)
              /repo                  show current repo
              /repo <n>              switch to assessment-<n> in same parent dir
              /repo <path>           switch to a specific repo path
              /model                 show current provider/model
              /model <name>          switch to a different model (e.g. anthropic/claude-sonnet-4-5)
              /scan                  show files the harness reads
              /log                   show recent audit events
              /raw                   show the last raw model response
              Ctrl+O                 show the last raw model response
              /quit                  exit

            Stages:
              1   2   3   4   5
            """
        ).strip()
    )


def show_recent_log(repo: Path) -> None:
    log_path = repo / ".lab-logs" / "harness-events.jsonl"
    if not log_path.is_file():
        panel("Audit Log", "No audit events yet.", BLUE)
        return
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]
    panel("Recent Audit Log", "\n".join(lines), BLUE)


def format_history(history: list[str]) -> str:
    return "\n".join(history[-8:])


def tool_result_prompt(original_user_text: str, tool_result: dict[str, object]) -> str:
    return (
        f"Original user request: {original_user_text}\n"
        f"Tool result from {tool_result.get('tool')}:\n{tool_result.get('result', '')}\n\n"
        "Continue from this tool result. If you have enough information, answer the user normally. "
        "If another tool is needed, call exactly one tool."
    )


def cmd_chat(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    stage = args.stage
    dry_run = args.dry_run
    model = resolve_model(args.provider, args.model)
    last_raw_response = ""
    history: list[str] = []

    banner(str(repo), stage, args.provider, model)

    # Codex-style auto-load: announce any agent-instruction file the harness
    # will auto-attach to every model request this session. See providers.py
    # AGENTS_FILES_PRECEDENCE for the lookup order.
    agents_name, agents_content = load_agent_instructions(repo)
    if agents_name:
        size = len(agents_content.encode("utf-8"))
        panel(
            f"Auto-loaded: {agents_name}",
            f"The harness will attach this file's contents as a system message "
            f"on every model call this session ({size} bytes). This mirrors "
            f"how Codex CLI / Continue / Aider / Windsurf / OpenHands / Roo "
            f"Code / Factory.ai handle AGENTS.md. The agent does not need to "
            f"discover the file with a tool call — it is already in context.",
            YELLOW,
        )

    while True:
        try:
            user_text = input(color("\n user > ", BOLD)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not user_text:
            continue
        if user_text == "/quit":
            return 0
        if user_text == "/help":
            print_chat_help()
            continue
        if user_text == "/stage":
            render_stage(stage)
            continue
        if user_text.startswith("/stage "):
            requested = user_text.split(maxsplit=1)[1].strip()
            resolved = resolve_stage(requested)
            if resolved is None:
                panel("Invalid Stage", f"Choose 1..{len(STAGES)}", RED)
                continue
            stage = resolved
            history.clear()
            last_raw_response = ""
            render_stage(stage)
            continue
        if user_text == "/clear":
            history.clear()
            last_raw_response = ""
            panel("History Cleared", "fresh conversation", BLUE)
            continue
        if user_text == "/repo":
            panel("Repo", str(repo), BLUE)
            continue
        if user_text.startswith("/repo "):
            requested = user_text.split(maxsplit=1)[1].strip()
            if requested.isdigit():
                candidate = repo.parent / f"assessment-{requested}"
            else:
                candidate = Path(requested).expanduser()
                if not candidate.is_absolute():
                    candidate = repo.parent / candidate
            candidate = candidate.resolve()
            if not candidate.is_dir():
                panel("Invalid Repo", f"Not a directory: {candidate}", RED)
                continue
            repo = candidate
            history.clear()
            last_raw_response = ""
            panel("Repo Switched", str(repo), GREEN)
            agents_name, agents_content = load_agent_instructions(repo)
            if agents_name:
                size = len(agents_content.encode("utf-8"))
                panel(
                    f"Auto-loaded: {agents_name}",
                    f"The harness will attach this file's contents as a system "
                    f"message on every model call ({size} bytes).",
                    YELLOW,
                )
            continue
        if user_text == "/model":
            panel("Model", f"{args.provider}  ·  {model}", BLUE)
            continue
        if user_text.startswith("/model "):
            requested = user_text.split(maxsplit=1)[1].strip()
            if not requested:
                panel("Invalid Model", "Provide a model name, e.g. /model anthropic/claude-sonnet-4-5", RED)
                continue
            model = requested
            panel("Model Switched", f"{args.provider}  ·  {model}", GREEN)
            continue
        if user_text == "/scan":
            cmd_scan(argparse.Namespace(repo=str(repo)))
            continue
        if user_text == "/log":
            show_recent_log(repo)
            continue
        if user_text in {"/raw", "\x0f"}:
            if last_raw_response:
                panel("Raw Model Response", last_raw_response, BLUE)
            else:
                panel("Raw Model Response", "No model response yet.", BLUE)
            continue

        history.append(f"user: {user_text}")
        prompt = user_text
        first_round = True

        while True:
            parsed, raw_response = parse_model_output(repo, args.provider, model, prompt, format_history(history))
            last_raw_response = raw_response
            if parsed is None:
                break

            render_proposal(parsed, stage)
            if parsed.get("type") == "message":
                history.append(f"assistant: {parsed.get('content', '')}")
                log_event(repo, {"type": "message", "response": parsed})
                break

            allowed, reason = enforce_stage(repo, parsed, stage)
            tone = GREEN if allowed else RED
            print(f"{badge('policy', tone)} {reason}")
            log_event(repo, {"type": "proposal", "stage": stage, "allowed": allowed, "reason": reason, "request": parsed})
            if not allowed:
                refusal = {"tool": str(parsed.get("tool", "")), "ok": False, "result": f"Refused by harness policy: {reason}"}
                history.append(f"assistant_tool_call: {json.dumps(parsed, sort_keys=True)}")
                history.append(f"tool_result: {json.dumps(refusal, sort_keys=True)}")
                prompt = tool_result_prompt(user_text, refusal)
                first_round = False
                continue

            if stage in NO_APPROVAL_STAGES:
                print(color(f"[auto] {reason} — no approval prompt.", RED))
                log_event(repo, {"type": "approval", "stage": stage, "approved": True, "auto": True, "request": parsed})
            else:
                approval_label = "Approve this action? [Y/n] " if first_round else "Approve this follow-up action? [Y/n] "
                approved = approve(approval_label)
                log_event(repo, {"type": "approval", "stage": stage, "approved": approved, "request": parsed})
                if not approved:
                    print("Not approved. Nothing executed.")
                    break

            tool_result = execute_or_tool(repo, parsed, stage, dry_run)
            history.append(f"assistant_tool_call: {json.dumps(parsed, sort_keys=True)}")
            history.append(f"tool_result: {json.dumps(tool_result, sort_keys=True)}")
            prompt = tool_result_prompt(user_text, tool_result)
            first_round = False


def cmd_run(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    context = read_context(repo)
    model_output = ask_model(args.provider, args.task, context, args.model, repo=repo)

    try:
        parsed = json.loads(extract_json_object(model_output))
    except json.JSONDecodeError:
        print("Model did not return JSON. Refusing to run.")
        log_event(repo, {"type": "refuse", "reason": "invalid_json", "model_output": model_output})
        return 2

    command = str(parsed.get("command", ""))
    action = str(parsed.get("action", ""))

    if args.safe_tools_only:
        result = safe_structured_action(repo, parsed)
        print(result)
        log_event(repo, {"type": "safe_tool", "request": parsed, "result": result})
        return 0

    if not command:
        print("No command proposed.")
        return 2

    if args.block_chaining and contains_shell_chaining(command):
        print("Blocked: command contains shell chaining or redirection characters.")
        log_event(repo, {"type": "blocked", "reason": "shell_chaining", "command": command})
        return 3

    print("Proposed action:")
    print(textwrap.fill(action or "No action summary supplied.", width=88))
    print()
    print("Command preview:")
    print(preview_command(command, args.show_full_command))
    print()

    approved = approve("Approve command? [Y/n] ")
    log_event(repo, {"type": "approval", "approved": approved, "command": command, "preview": preview_command(command, args.show_full_command)})

    if not approved:
        print("Not approved. Nothing executed.")
        return 1

    if args.dry_run:
        print("Dry run enabled. Nothing executed.")
        return 0

    rc, _stdout, _stderr = execute_command(repo, command)
    log_event(repo, {"type": "execute", "returncode": rc, "command": command})
    print(f"Command exited with {rc}")
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Defanged workshop AI harness.")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    scan = subparsers.add_parser("scan", help="List repo files the harness will read.")
    scan.add_argument("repo")
    scan.set_defaults(func=cmd_scan)

    ask = subparsers.add_parser("ask", help="Ask the configured provider for an action.")
    ask.add_argument("task")
    ask.add_argument("--repo", required=True)
    ask.add_argument("--provider", choices=("openrouter", "gemini"), default="openrouter")
    ask.add_argument("--model", help="Provider model name, such as openrouter/free.")
    ask.set_defaults(func=cmd_ask)

    run = subparsers.add_parser("run", help="Ask for and optionally run a proposed command.")
    run.add_argument("--repo", required=True)
    run.add_argument("--task", default="Inspect the repo and propose one useful command.")
    run.add_argument("--provider", choices=("openrouter", "gemini"), default="openrouter")
    run.add_argument("--model", help="Provider model name, such as openrouter/free.")
    run.add_argument("--show-full-command", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--block-chaining", action="store_true")
    run.add_argument("--safe-tools-only", action="store_true")
    run.set_defaults(func=cmd_run)

    chat = subparsers.add_parser("chat", help="Start an interactive Codex-style harness.")
    chat.add_argument("--repo", required=True)
    chat.add_argument("--provider", choices=("openrouter", "gemini"), default="openrouter")
    chat.add_argument("--model", help="Provider model name, such as openrouter/free.")
    chat.add_argument("--stage", type=stage_argtype, default="yolo", help="Hardening stage. Use the name or its number (1..5).")
    chat.add_argument("--dry-run", action="store_true")
    chat.set_defaults(func=cmd_chat)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
