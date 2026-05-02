#!/bin/bash
# summon-egg.sh — materialize a .egg into a workspace under $RAPP_HOME/twins/.
#
# Usage:
#   bash installer/summon-egg.sh <egg-path>
#   bash installer/summon-egg.sh <egg-path> --keep-kernel
#   bash installer/summon-egg.sh <egg-path> --host /custom/host/root
#
# After summon, the workspace is at $RAPP_HOME/twins/<rappid_uuid>/.
# The brainstem is bundled in the workspace; cd in and run installer/start.sh.

set -euo pipefail

EGG_PATH=""
HOST_ROOT=""
KEEP_KERNEL=0

while [ $# -gt 0 ]; do
    case "$1" in
        --keep-kernel) KEEP_KERNEL=1; shift ;;
        --host)        HOST_ROOT="$2"; shift 2 ;;
        -h|--help)
            head -n 9 "$0" | tail -n 8
            exit 0
            ;;
        *)
            if [ -z "$EGG_PATH" ]; then
                EGG_PATH="$1"
            else
                echo "FAIL: unexpected arg: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$EGG_PATH" ]; then
    echo "FAIL: usage: bash $0 <egg-path>"
    exit 1
fi

if [ ! -f "$EGG_PATH" ]; then
    echo "FAIL: egg file not found: $EGG_PATH"
    exit 1
fi

# Locate utils/egg.py — try the cwd's repo first, then fall back to twin lookup
EGG_MODULE_DIR=""
if [ -f "utils/egg.py" ]; then
    EGG_MODULE_DIR="$(pwd)/utils"
elif [ -f "$(git rev-parse --show-toplevel 2>/dev/null)/utils/egg.py" ]; then
    EGG_MODULE_DIR="$(git rev-parse --show-toplevel)/utils"
else
    echo "FAIL: cannot find utils/egg.py — run from inside a variant repo"
    exit 1
fi

python3 - "$EGG_PATH" "$EGG_MODULE_DIR" "$HOST_ROOT" "$KEEP_KERNEL" <<'PYEOF'
import os
import sys

egg_path, module_dir, host_root, keep_kernel = sys.argv[1:5]
sys.path.insert(0, module_dir)
import egg

if not host_root:
    rapp_home = os.environ.get("RAPP_HOME") or os.path.join(os.path.expanduser("~"), ".rapp")
    host_root = os.path.join(rapp_home, "twins")
os.makedirs(host_root, exist_ok=True)

with open(egg_path, "rb") as f:
    blob = f.read()

ws = egg.summon_twin_egg(blob, host_root, keep_existing_kernel=(keep_kernel == "1"))
print(f"summoned: {ws}")
print(f"  next:   cd '{ws}' && bash installer/start.sh")
PYEOF
