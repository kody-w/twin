#!/bin/bash
# lay-egg.sh — pack the current twin repo into a local backup egg.
#
# Default save path: $RAPP_HOME/eggs/<rappid_uuid>/<timestamp>.egg
#                    (RAPP_HOME defaults to ~/.rapp/)
#
# Works offline, no brainstem required — talks directly to utils/egg.py.
#
# Usage:
#   bash installer/lay-egg.sh              # pack the current repo
#   bash installer/lay-egg.sh /path/to/another-twin
#
# The egg is non-destructive: it only reads the repo, never modifies it.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

REPO_PATH="${1:-$(pwd)}"
REPO_PATH="$(cd "$REPO_PATH" && pwd)"

if [ ! -f "$REPO_PATH/rappid.json" ]; then
    echo "FAIL: $REPO_PATH has no rappid.json — not a variant repo"
    exit 1
fi

python3 - "$REPO_PATH" <<'PYEOF'
import json
import os
import sys
import time

repo = sys.argv[1]
sys.path.insert(0, os.path.join(repo, "utils"))
import egg

with open(os.path.join(repo, "rappid.json")) as f:
    rj = json.load(f)
rappid_uuid = rj["rappid"]

rapp_home = os.environ.get("RAPP_HOME") or os.path.join(os.path.expanduser("~"), ".rapp")
out_dir = os.path.join(rapp_home, "eggs", rappid_uuid)
os.makedirs(out_dir, exist_ok=True)
ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
out_path = os.path.join(out_dir, f"{ts}.egg")

blob = egg.pack_twin_from_repo(repo)
with open(out_path, "wb") as f:
    f.write(blob)

print(f"laid egg: {out_path}")
print(f"  rappid_uuid: {rappid_uuid}")
print(f"  name:        {rj.get('name')}")
print(f"  size:        {len(blob)/1024:.1f} KB")
PYEOF
