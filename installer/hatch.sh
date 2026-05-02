#!/bin/bash
# hatch.sh — egg-based kernel update for the current twin repo.
#
# The flow:
#   1. Lay an egg (backup the twin's identity + state + mutations)
#   2. Replace brainstem.py with the new kernel from <new-kernel-source>
#   3. Summon the egg back, keeping the new kernel
#
# Result: kernel upgraded, twin's identity + memory + mutations preserved.
# No git merge, no conflicts.
#
# Usage:
#   bash installer/hatch.sh <path-to-new-brainstem.py-file>
#   bash installer/hatch.sh <path-to-rapp-checkout>      # picks up rapp_brainstem/brainstem.py
#
# Examples:
#   git clone https://github.com/kody-w/RAPP /tmp/rapp-fresh
#   bash installer/hatch.sh /tmp/rapp-fresh
#
#   # Or from a frozen species archive snapshot:
#   bash installer/hatch.sh /tmp/rapp-fresh/rapp_kernel/v/0.13.0/brainstem.py

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

if [ ! -f "rappid.json" ]; then
    echo "FAIL: not a variant repo (no rappid.json at $(pwd))"
    exit 1
fi

if [ $# -lt 1 ]; then
    echo "FAIL: usage: bash $0 <path-to-new-brainstem.py-or-rapp-checkout>"
    exit 1
fi

SRC="$1"
NEW_KERNEL=""
if [ -f "$SRC" ] && [[ "$SRC" == *brainstem.py ]]; then
    NEW_KERNEL="$SRC"
elif [ -d "$SRC" ] && [ -f "$SRC/rapp_brainstem/brainstem.py" ]; then
    NEW_KERNEL="$SRC/rapp_brainstem/brainstem.py"
elif [ -d "$SRC" ] && [ -f "$SRC/brainstem.py" ]; then
    NEW_KERNEL="$SRC/brainstem.py"
else
    echo "FAIL: cannot locate brainstem.py from $SRC"
    exit 1
fi

echo "[hatch] new kernel:  $NEW_KERNEL"

# Step 1: lay an egg
echo "[hatch] step 1: laying egg…"
bash installer/lay-egg.sh

# Find the most recent egg for THIS twin
EGG_PATH="$(python3 - <<'PYEOF'
import json
import os
import glob

with open("rappid.json") as f:
    rj = json.load(f)
rappid = rj["rappid"]
rapp_home = os.environ.get("RAPP_HOME") or os.path.join(os.path.expanduser("~"), ".rapp")
eggs_dir = os.path.join(rapp_home, "eggs", rappid)
eggs = sorted(glob.glob(os.path.join(eggs_dir, "*.egg")))
print(eggs[-1] if eggs else "")
PYEOF
)"

if [ -z "$EGG_PATH" ]; then
    echo "FAIL: could not find egg after lay-egg"
    exit 1
fi

# Step 2: replace the kernel in place
echo "[hatch] step 2: swapping kernel…"
cp "$NEW_KERNEL" brainstem.py
echo "[hatch]   brainstem.py replaced"

# Step 3: re-summon the egg into THIS workspace, keeping the new kernel
echo "[hatch] step 3: summoning egg with --keep-kernel…"
WORKSPACE_PARENT="$(dirname "$(pwd)")"
WORKSPACE_BASE="$(basename "$(pwd)")"

python3 - "$EGG_PATH" "$(pwd)/utils" "$WORKSPACE_PARENT" "$WORKSPACE_BASE" <<'PYEOF'
import json
import os
import sys

egg_path, module_dir, parent_dir, expected_basename = sys.argv[1:5]
sys.path.insert(0, module_dir)
import egg

with open(egg_path, "rb") as f:
    blob = f.read()

# We summon back into the existing workspace by host_root = parent_dir
# (egg.summon_twin_egg always lands at <host>/<rappid>). For an in-place
# hatch, the existing workspace dir IS <parent>/<rappid>, so this puts
# everything back where it was — with the new kernel preserved.
ws = egg.summon_twin_egg(blob, parent_dir, keep_existing_kernel=True)
print(f"[hatch]   summoned: {ws}")
PYEOF

echo ""
echo "[hatch] DONE."
echo "[hatch]   egg backup:  $EGG_PATH"
echo "[hatch]   new kernel:  active in $(pwd)/brainstem.py"
echo "[hatch]   identity + mutations preserved via egg roundtrip"
