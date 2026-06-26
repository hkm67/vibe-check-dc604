# lab2 — agent harness

A tiny, self-contained AI coding-agent harness — the kind of control loop
that wraps a model in tools (read files, run shell, fetch URLs) the way Codex
CLI / Aider / opencode do — plus the set of repos under `repos/` it operates
on. Used in Lab 2 of the talk to make the agent's trust boundaries concrete.

- `harness/` — the harness: provider layer, the ReAct chat loop, the approval
  policy, and the terminal UI.
- `repos/` — `assessment-0` … `assessment-5`, the repos you point the harness
  at. Each looks like an ordinary "review this code" task.

## Run it

Needs Python 3.10+ and an LLM API key (OpenRouter or Gemini).

```bash
pip install -e .
export OPENROUTER_API_KEY=...        # or: export GEMINI_API_KEY=... --provider gemini
harness chat --repo repos/assessment-0 --stage 1
```

`--stage` (1–5) selects how strict the harness's approval policy is. Point it
at each repo, at each stage, and read what the harness proposes, what it shows
you, and what it actually does. `harness --help` lists the rest.

> ⚠️ The harness executes shell commands a model proposes. Run it only in a
> sandbox (VM/container), never on your host — and read the repos before you
> point it at them.
