#!/usr/bin/env bash
# Reset Lab 1 assessment-1 between rounds.
# Idempotent — safe to run multiple times.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$HERE/assessment-1"

echo "[cleanup] killing any candidate-portal Express server on :3000"
# `node server.js` from assessment-1 holds port 3000; kill it so the
# next `npm start` doesn't hit EADDRINUSE.
pkill -f "node server.js" 2>/dev/null || true
# Belt-and-suspenders: also free port 3000 if anything else is bound to it.
fuser -k 3000/tcp 2>/dev/null || true

echo "[cleanup] removing node_modules from $REPO"
rm -rf "$REPO/node_modules" 2>/dev/null || true
rm -f "$REPO/package-lock.json" 2>/dev/null || true

echo "[cleanup] done"
