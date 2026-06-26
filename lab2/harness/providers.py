"""Lab 2 harness — provider layer.

Conceptually mirrors OpenAI's open-source Codex CLI design (openai/codex
on GitHub) for the parts that matter to the workshop:

- The OpenAI tool-calling JSON schema (`TOOLS` below) — same wire format
  every major coding agent has converged on (OpenAI, Anthropic, Gemini).
- Provider dispatch via `ask_model(provider, ...)` — same pattern as
  Codex's model-provider registry; we ship two providers (OpenRouter,
  Gemini), real harnesses ship more.
- `load_agent_instructions(repo)` — direct mirror of Codex CLI's
  precedence-ordered project-instruction file loader.
- `build_system_messages(repo)` — base system prompt + auto-loaded
  AGENTS.md content, attached as system-role messages on every model
  request. Matches the Codex "instruction chain" pattern.

What we don't have here (deliberate workshop scope): streaming,
parallel tool calls per turn, token-usage tracking, retries, real
config-file support. See `resources/harness-architecture.md` for the
full comparison and reasoning.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


SYSTEM_PROMPT = """You are a local coding assistant.
Answer normally when the user is chatting.
When local repository inspection or computation requires a tool, call one of the available tools.
Do not claim to have run a tool unless you actually called one."""


# Auto-loaded agent instruction files. Mirrors the discovery pattern used by
# OpenAI's Codex CLI (openai/codex on GitHub) — precedence-ordered file lookup
# at the repo root, content appended to the model's instruction chain at every
# turn. The convention is documented at https://agents.md/ and has 60,000+ public
# repos adopting it as of 2026.
#
# Real-world auto-loaders (2026, partial list):
#   - OpenAI Codex CLI — defined the convention, reads AGENTS.override.md
#     then AGENTS.md then project_doc_fallback_filenames
#   - Continue.dev, Aider, OpenHands, Windsurf, Factory.ai, Amp, Roo Code
#     — default to AGENTS.md
#   - Claude Code — primarily reads CLAUDE.md; supports AGENTS.md as a
#     companion file
#   - Cursor — primarily reads .cursorrules / .cursor/rules/
#
# We check the same precedence locally and load the first non-empty file
# found. Content is capped at AGENTS_MAX_BYTES to prevent context blowout.
AGENTS_FILES_PRECEDENCE = (
    "AGENTS.override.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
)
AGENTS_MAX_BYTES = 16 * 1024


def load_agent_instructions(repo: Path | None) -> tuple[str, str]:
    """Discover and load an agent-instructions file from the repo root.

    Returns ``(filename, content)`` for the first non-empty match in
    ``AGENTS_FILES_PRECEDENCE``, or ``("", "")`` if nothing matched.
    """
    if repo is None:
        return ("", "")
    for name in AGENTS_FILES_PRECEDENCE:
        path = repo / name
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if content.strip():
            return (name, content[:AGENTS_MAX_BYTES])
    return ("", "")

REPO_ACTION_KEYWORDS = (
    "repo",
    "repository",
    "project",
    "folder",
    "directory",
    "current",
    "readme",
    "summarize",
    "inspect",
    "test",
    "run",
    "build",
    "debug",
    "fix",
    "review",
    "triage",
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "Propose a local shell command to run in the repository. Use only when a command is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command to run.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief user-facing reason for the command.",
                    },
                },
                "required": ["command", "reason"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository-relative file path.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the repository or a repository subdirectory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository-relative directory path. Use . for the repository root.",
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search repository files for a text pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Repository-relative path to search under. Use . for the repository root.",
                    },
                },
                "required": ["pattern", "path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and return the text content of an HTTP URL. Use when the user asks to summarize, read, or research an article or page at a URL. Localhost-allowlisted in this lab harness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "HTTP URL to fetch.",
                    },
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
]


def resolve_model(provider: str, model: str | None) -> str:
    """Single source of truth for model resolution. Precedence:
    explicit --model arg > env var override > provider default."""
    if model:
        return model
    if provider == "openrouter":
        return os.environ.get("OPENROUTER_MODEL", "openrouter/free")
    if provider == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    return "default"


def ask_model(provider: str, task: str, context: dict[str, str], model: str | None = None, history: str = "", repo: Path | None = None) -> str:
    if provider == "openrouter":
        return ask_openrouter(task, context, model, history, repo)
    if provider == "gemini":
        return ask_gemini(task, context, model, history, repo)
    raise ValueError(f"unknown provider: {provider}")


def build_system_messages(repo: Path | None) -> list[dict[str, str]]:
    """Build the system message stack. Mirrors Codex CLI: the base system prompt
    plus an auto-loaded agent-instructions message if AGENTS.md (or its
    precedence fallback) is present in the repo root."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    name, instructions = load_agent_instructions(repo)
    if instructions:
        messages.append({
            "role": "system",
            "content": (
                f"Project instructions auto-loaded from {name} "
                f"(per the AGENTS.md convention; this content is treated as "
                f"authoritative project guidance):\n\n{instructions}"
            ),
        })
    return messages


def needs_repo_context(task: str) -> bool:
    lowered = task.lower()
    return any(keyword in lowered for keyword in REPO_ACTION_KEYWORDS)


def build_prompt(task: str, context: dict[str, str], history: str = "") -> str:
    files = "\n".join(f"- {name}" for name in context)
    transcript = f"\nConversation so far:\n{history}\n" if history else ""
    return f"""User task: {task}
{transcript}

Repository root files (use tools to read contents):
{files}"""


def build_chat_prompt(task: str, history: str = "") -> str:
    transcript = f"\nConversation so far:\n{history}\n" if history else ""
    return f"User message: {task}{transcript}"


def normalize_openai_message(message: dict[str, object]) -> str:
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        call = tool_calls[0]
        if not isinstance(call, dict):
            return json.dumps({"type": "message", "content": str(message.get("content") or "")})
        function = call.get("function")
        if not isinstance(function, dict):
            return json.dumps({"type": "message", "content": str(message.get("content") or "")})
        name = str(function.get("name", ""))
        raw_args = str(function.get("arguments", "{}"))
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = {"raw": raw_args}
        action = args.get("reason") if isinstance(args, dict) else None
        return json.dumps(
            {
                "type": "tool_call",
                "action": action or f"Call tool {name}.",
                "tool": name,
                "args": args,
            }
        )
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return json.dumps({"type": "message", "content": content.strip()})
    return json.dumps({"type": "message", "content": "No response."})


def post_json(url: str, headers: dict[str, str], payload: dict[str, object]) -> str:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        return json.dumps(
            {
                "type": "message",
                "content": f"Provider request failed. Check your provider API key, network access, and model availability. Error: {exc}",
            }
        )


def ask_openrouter(task: str, context: dict[str, str], model: str | None = None, history: str = "", repo: Path | None = None) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return json.dumps(
            {
                "type": "message",
                "content": "OPENROUTER_API_KEY is not set. Export your OpenRouter key before starting the harness.",
            }
        )
    use_repo_context = needs_repo_context(task)
    messages = build_system_messages(repo)
    messages.append({"role": "user", "content": build_prompt(task, context, history) if use_repo_context else build_chat_prompt(task, history)})
    body = post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://bsides-vancouver.local/vibe-check",
            "X-Title": "Vibe Check Workshop Harness",
        },
        {
            "model": resolve_model("openrouter", model),
            "tools": TOOLS,
            "tool_choice": "auto",
            "messages": messages,
        },
    )
    try:
        parsed = json.loads(body)
        message = parsed["choices"][0]["message"]
        if isinstance(message, dict):
            return normalize_openai_message(message)
        return str(message)
    except (KeyError, json.JSONDecodeError, IndexError, TypeError):
        return body


def ask_gemini(task: str, context: dict[str, str], model: str | None = None, history: str = "", repo: Path | None = None) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return json.dumps(
            {
                "type": "message",
                "content": "GEMINI_API_KEY is not set. Export your Gemini key before starting the harness.",
            }
        )
    model = resolve_model("gemini", model)
    use_repo_context = needs_repo_context(task)
    # Gemini uses a flat single-text prompt; mirror the Codex-style auto-load
    # by prepending agent-instructions content as a system-style preamble.
    agents_name, agents_content = load_agent_instructions(repo)
    agents_preamble = (
        f"\n\nProject instructions auto-loaded from {agents_name} "
        f"(per the AGENTS.md convention; treat as authoritative):\n{agents_content}\n"
        if agents_content
        else ""
    )
    body = post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        {"Content-Type": "application/json"},
        {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT + agents_preamble + "\n\nReturn JSON in either {\"type\":\"message\",\"content\":\"...\"} or {\"type\":\"tool_call\",\"tool\":\"shell\",\"args\":{\"command\":\"...\",\"reason\":\"...\"}} shape.\n\n" + (build_prompt(task, context, history) if use_repo_context else build_chat_prompt(task, history))}
                    ]
                }
            ]
        },
    )
    try:
        parsed = json.loads(body)
        return parsed["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, json.JSONDecodeError, IndexError, TypeError):
        return body
