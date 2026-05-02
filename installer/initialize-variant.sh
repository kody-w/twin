#!/usr/bin/env bash
# initialize-variant.sh — one-step scaffold for a new variant created from
# this template via GitHub's "Use this template" flow.
#
# Run from inside the freshly-created repository's working tree.
#
# Single-parent rule (Constitution Article XXXIV): a variant's parent is
# the repo whose code it inherited — no exceptions. This script ALWAYS
# sets parent_rappid to wildhaven's rappid, because if you got here, you
# templated from wildhaven. To be a direct child of rapp, template from
# kody-w/RAPP instead.
#
# What it does:
#   1. Verifies this is an uninitialized template clone (via lineage_check)
#   2. Generates a fresh rappid (UUIDv4)
#   3. Updates ONLY the lineage fields of rappid.json (rappid,
#      parent_rappid, parent_repo, parent_commit, born_at, name)
#   4. Prints the summon URL for your new variant
#
# What it does NOT do (rule: never overwrite local data):
#   - Does not rewrite soul.md, MANIFEST.md, README.md, LICENSE, or any
#     other content files. Once the twin has hatched, its local state is
#     sovereign — edit those files manually to make the variant yours.
#   - Does not delete the inherited private_companion block (you may
#     want to repoint it; we won't decide for you).
#   - Does not change role/kind/description in rappid.json — those are
#     inherited starting points you can edit.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

if [ ! -f rappid.json ]; then
    echo "FAIL: no rappid.json at repo root. This script must run inside a"
    echo "      repo created from the wildhaven-ai-homes-twin template."
    exit 1
fi

# ── Identity ─────────────────────────────────────────────────────────────

# This template's hardcoded identity (single-parent rule: every variant
# created from this script has wildhaven as its parent_rappid).
PARENT_RAPPID="37ad22f5-ed6d-48b1-b8b4-61019f58a42b"
PARENT_REPO="https://github.com/kody-w/wildhaven-ai-homes-twin.git"

# ── Freshness check via lineage_check.py ─────────────────────────────────
# The lineage checker is the source of truth for whether this is an
# uninitialized clone. We honor whatever it says.

LINEAGE_STATUS="$(python3 - <<'PYEOF'
import json, sys
sys.path.insert(0, "utils")
try:
    from lineage_check import check_lineage
    info = check_lineage()
    print(info["status"])
except Exception as e:
    print(f"error:{e}")
PYEOF
)"

case "$LINEAGE_STATUS" in
    variant_uninitialized)
        : # Expected — proceed to initialize
        ;;
    self)
        echo "FAIL: this IS the wildhaven template repo itself. Refusing to"
        echo "      reinitialize the template root. If you meant to create a"
        echo "      variant, click 'Use this template' on GitHub first, then"
        echo "      run this script inside the new repo."
        exit 1
        ;;
    variant_initialized)
        echo "WARNING: this variant is already initialized. Re-running will"
        echo "         overwrite its rappid with a fresh one — descendants"
        echo "         that point at the current rappid will lose their link."
        read -p "Continue? [y/N] " confirm
        case "$confirm" in
            y|Y|yes|Yes) ;;
            *) echo "aborted."; exit 1 ;;
        esac
        ;;
    lineage_mismatch|no_rappid|error:*)
        echo "FAIL: lineage check returned: $LINEAGE_STATUS"
        echo "      Run: python3 utils/lineage_check.py for details."
        exit 1
        ;;
    *)
        echo "FAIL: unexpected lineage status: $LINEAGE_STATUS"
        exit 1
        ;;
esac

# ── Variant name ─────────────────────────────────────────────────────────

DEFAULT_NAME="$(basename "$(git rev-parse --show-toplevel)")"
read -p "Variant name (default: $DEFAULT_NAME): " VARIANT_NAME
VARIANT_NAME="${VARIANT_NAME:-$DEFAULT_NAME}"

# ── Generate rappid ──────────────────────────────────────────────────────

NEW_RAPPID="$(python3 -c "import uuid; print(uuid.uuid4())")"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Try to record the parent's commit at the moment of initialization
PARENT_COMMIT=""
PARENT_COMMIT="$(curl -fsSL "https://api.github.com/repos/$(echo "$PARENT_REPO" | sed 's|https://github.com/||;s|\.git$||')/commits/main" 2>/dev/null \
    | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null || echo "")"

# ── Update rappid.json (lineage fields only — preserve everything else) ──

python3 - "$NEW_RAPPID" "$PARENT_RAPPID" "$PARENT_REPO" "$PARENT_COMMIT" "$NOW" "$VARIANT_NAME" <<'PYEOF'
import json
import os
import sys

(rappid, parent_rappid, parent_repo, parent_commit, born_at, name) = sys.argv[1:7]

with open("rappid.json") as f:
    data = json.load(f)

# Update ONLY lineage fields. Preserve kind, description, private_companion,
# attestation, brainstem, and any other inherited or locally-added content.
data["rappid"] = rappid
data["parent_rappid"] = parent_rappid
data["parent_repo"] = parent_repo
data["parent_commit"] = parent_commit or None
data["born_at"] = born_at
data["name"] = name
data["role"] = "variant"
data.setdefault("schema", "rapp-rappid/1.1")
# attestation resets because the new rappid hasn't been attested yet.
data["attestation"] = None

# Record the bundled brainstem pin if a VERSION file ships in installer/.
# Never overwrites an existing brainstem block — that would clobber a
# deliberate manual sync the operator may have done.
_version_path = os.path.join("installer", "VERSION")
if "brainstem" not in data and os.path.exists(_version_path):
    with open(_version_path) as vf:
        bs_version = vf.read().strip()
    data["brainstem"] = {
        "version": bs_version,
        "source_repo": "https://github.com/kody-w/RAPP.git",
        "source_path": "rapp_brainstem/",
        "source_commit": None,
        "bundled_at": born_at,
        "_note": (
            "Bundled kernel for local-first operation — `bash start.sh` "
            "runs without a separate ~/.brainstem install. Re-running "
            "the installer never re-syncs this; pull upstream kernel "
            "updates via a deliberate manual sync."
        ),
    }

with open("rappid.json", "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF

echo ""
echo "✓ rappid.json updated:"
echo "    rappid:         $NEW_RAPPID"
echo "    parent_rappid:  $PARENT_RAPPID"
echo "    parent_repo:    $PARENT_REPO"
echo "    parent_commit:  ${PARENT_COMMIT:-(could not resolve from network)}"
echo "    born_at:        $NOW"
echo "    name:           $VARIANT_NAME"

# ── Content files (soul.md, MANIFEST.md, README.md, LICENSE, etc.) ───────
# Intentionally NOT touched. The variant inherits the template's content
# as a starting point; edit those files locally as the twin hatches into
# its own identity. Re-running this script is non-destructive — it never
# overwrites local data.

# ── Print summon URL hint ────────────────────────────────────────────────

REMOTE_URL="$(git config --get remote.origin.url 2>/dev/null || echo '')"
GH_OWNER_REPO=""
if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+/[^/]+)\.git$ ]]; then
    GH_OWNER_REPO="${BASH_REMATCH[1]}"
elif [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+/[^/]+)$ ]]; then
    GH_OWNER_REPO="${BASH_REMATCH[1]}"
fi

echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo " Variant initialized."
echo "──────────────────────────────────────────────────────────────────────"
echo ""
if [ -n "$GH_OWNER_REPO" ]; then
    GH_OWNER="${GH_OWNER_REPO%%/*}"
    GH_REPO="${GH_OWNER_REPO##*/}"
    echo " Your sovereign vBrainstem URL (after enabling GitHub Pages on this repo):"
    echo "   https://${GH_OWNER}.github.io/${GH_REPO}/vbrainstem.html"
    echo ""
    echo " That URL hosts a copy of the simulator inside YOUR repo — your variant's"
    echo " URL surface does not depend on the upstream's hosting. Regenerate your QR"
    echo " (summon.svg) with that URL — see SUMMON.md for the snippet."
    echo ""
    echo " To enable GitHub Pages from main / root:"
    echo "   gh api -X POST repos/${GH_OWNER}/${GH_REPO}/pages \\"
    echo "     -f 'source[branch]=main' -f 'source[path]=/'"
else
    echo " (Could not detect your repo's GitHub remote. Set 'origin' to your"
    echo "  GitHub repo URL and update SUMMON.md / summon.svg manually.)"
fi
echo ""
echo " Next steps (the installer touched ONLY rappid.json — all other files"
echo " still contain the parent's content as a starting point for you to edit):"
echo "   1. Edit soul.md to define your twin's voice."
echo "   2. Edit MANIFEST.md / README.md to describe your variant."
echo "   3. Customize the agents under agents/ for your variant's purpose."
echo "   4. Decide on a LICENSE (the inherited LICENSE is the parent's)."
echo "   5. (Optional) Repoint or remove the private_companion block in"
echo "      rappid.json — it currently still points at the parent's private"
echo "      repo, which YOU will not have access to."
echo "   6. (Optional) Mark your repo as a template too:"
echo "        gh repo edit $GH_OWNER_REPO --template=true"
echo "   7. Commit + push:"
echo "        git add -A && git commit -m 'init: $VARIANT_NAME' && git push"
echo ""
echo " Lineage walk: your_rappid → $PARENT_RAPPID (wildhaven-ai-homes-twin) → rapp species root"
echo ""
