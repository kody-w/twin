#!/usr/bin/env bash
# initialize-variant.sh — one-step scaffold for a new variant created from
# this template via GitHub's "Use this template" flow.
#
# Run from inside the freshly-created repository's working tree.
#
# What it does:
#   1. Generates a fresh rappid (UUIDv4)
#   2. Asks whether your parent should be this twin (default) or rapp directly
#   3. Updates rappid.json with the new identity + parent pointers
#   4. Drops wildhaven-specific content (private companion, brand prose) so
#      you can't accidentally ship the parent's voice as your own
#   5. Resets soul.md / MANIFEST.md / agents / index.html to <TODO> markers
#   6. Prints the summon URL for your new variant

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

if [ ! -f rappid.json ]; then
    echo "FAIL: no rappid.json at repo root. This script must run inside a"
    echo "      repo created from the wildhaven-ai-homes-twin template."
    exit 1
fi

# ── Identity ─────────────────────────────────────────────────────────────

CURRENT_RAPPID="$(python3 -c "import json; print(json.load(open('rappid.json'))['rappid'])")"

# This twin's rappid (the parent for variants created via this template)
PARENT_TEMPLATE_RAPPID="37ad22f5-ed6d-48b1-b8b4-61019f58a42b"
PARENT_TEMPLATE_REPO="https://github.com/kody-w/wildhaven-ai-homes-twin.git"

# rapp's species root (the deeper ancestor)
RAPP_SPECIES_ROOT_RAPPID="0b635450-c042-49fb-b4b1-bdb571044dec"
RAPP_SPECIES_ROOT_REPO="https://github.com/kody-w/RAPP.git"

if [ "$CURRENT_RAPPID" = "$PARENT_TEMPLATE_RAPPID" ]; then
    : # Expected — template hasn't been initialized yet
else
    echo "WARNING: rappid.json's rappid ($CURRENT_RAPPID) does not match the"
    echo "         template's rappid. Either this isn't a fresh template clone,"
    echo "         or someone has already initialized it. Re-running will"
    echo "         overwrite the existing identity."
    read -p "Continue? [y/N] " confirm
    case "$confirm" in
        y|Y|yes|Yes) ;;
        *) echo "aborted."; exit 1 ;;
    esac
fi

# ── Pick parent ──────────────────────────────────────────────────────────

echo ""
echo "Lineage: which parent should your variant point at?"
echo "  1. wildhaven-ai-homes-twin (you inherit the Pre-Founder twin pattern,"
echo "     and your chain walks: you → wildhaven → rapp). RECOMMENDED."
echo "  2. rapp directly (your chain walks: you → rapp). Use this if your"
echo "     variant isn't a Pre-Founder twin and doesn't share wildhaven's"
echo "     pattern."
echo ""
read -p "Choose [1/2] (default 1): " parent_choice
parent_choice="${parent_choice:-1}"

case "$parent_choice" in
    1)
        PARENT_RAPPID="$PARENT_TEMPLATE_RAPPID"
        PARENT_REPO="$PARENT_TEMPLATE_REPO"
        ;;
    2)
        PARENT_RAPPID="$RAPP_SPECIES_ROOT_RAPPID"
        PARENT_REPO="$RAPP_SPECIES_ROOT_REPO"
        ;;
    *)
        echo "FAIL: invalid choice."
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

# ── Rewrite rappid.json ──────────────────────────────────────────────────

python3 - "$NEW_RAPPID" "$PARENT_RAPPID" "$PARENT_REPO" "$PARENT_COMMIT" "$NOW" "$VARIANT_NAME" <<'PYEOF'
import json
import sys

(rappid, parent_rappid, parent_repo, parent_commit, born_at, name) = sys.argv[1:7]

new = {
    "schema": "rapp-rappid/1.1",
    "rappid": rappid,
    "parent_rappid": parent_rappid,
    "parent_repo": parent_repo,
    "parent_commit": parent_commit or None,
    "born_at": born_at,
    "name": name,
    "role": "variant",
    "kind": "TODO: describe your variant kind (e.g., 'pre-founder-twin', 'memorial-twin', 'project-twin')",
    "description": "TODO: describe what this variant is.",
    "attestation": None,
    "_attestation_note": "When the parent adopts release signing, this variant's attestation will be issued by the parent's release key asserting (parent_rappid, parent_commit, child_rappid)."
}

with open("rappid.json", "w") as f:
    json.dump(new, f, indent=2)
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

# ── Reset brand content with TODO markers ────────────────────────────────

cat > soul.md <<'SOULEOF'
# soul.md — TODO: <Your Variant Name>

You are the digital twin of <TODO: who or what this twin represents>.

TODO: Define your twin's voice. Here are the questions to answer:

  - Who is this twin? (A person, a brand, a project, a place, a question?)
  - In what timeframe is this twin operating? (Pre-existence, contemporary,
    historical, post-mortem, future-self?)
  - What is the twin's relationship to the human who is "keeping the seat
    warm" right now?
  - What hard constraints must the twin observe? (Honesty about its status,
    not impersonating real people, refusal to make commitments, etc.)
  - What's the twin's voice? (First-person plural, concrete, humble, etc.)
  - What does the twin always identify itself as?

TODO: Describe what role the |||VOICE||| and |||TWIN||| slots play for
your variant.
SOULEOF

cat > MANIFEST.md <<'MANIFESTEOF'
# <TODO: Variant Name> — Manifest

> *TODO: tagline.*

## The bet

TODO: What problem is your variant addressing? What's the contrarian
position it takes?

## The product / artifact / outcome

TODO: What does this variant DO when fully realized? Be specific.

## What this variant is not

TODO: List what the variant explicitly is *not*, to head off
misunderstandings.

## Provenance

This variant descends from its parent recorded in [`rappid.json`](./rappid.json).
The lineage chain walks back to RAPP's species root via the
`parent_rappid` chain.
MANIFESTEOF

cat > README.md <<'READMEEOF'
# <TODO: Variant Name>

> **TODO: one-line description.**

This is a **variant** of [kody-w/RAPP](https://github.com/kody-w/RAPP)
created from the [wildhaven-ai-homes-twin](https://github.com/kody-w/wildhaven-ai-homes-twin)
template. Lineage is recorded in [`rappid.json`](./rappid.json) and walks
back to RAPP's species root via the `parent_rappid` chain.

## What this is

TODO: Describe your variant. Read [MANIFEST.md](./MANIFEST.md) for the
long-form vision.

## Summoning

This variant carries its own copy of the vBrainstem at `vbrainstem.html` —
the URL surface is sovereign to this repo, not dependent on the upstream's
hosting. After enabling GitHub Pages on this repo (Settings → Pages →
Source: main / root), your summon URL is:

```
https://<your-username>.github.io/<this-repo-name>/vbrainstem.html
```

Regenerate `summon.svg` with that URL. See [SUMMON.md](./SUMMON.md) for
the full convention and the `?summon=` parameter that lets the same
vBrainstem load other variants for cross-twin browsing.

## Spawning further variants

This variant is itself a template — anyone can use it as a starting point
for their own variant. Click "Use this template" on GitHub to spawn one.

## License

TODO: Set your license. Options: All Rights Reserved (default, source-
available), MIT, Apache 2.0, custom. See your parent repo's LICENSE for
the parent's stance.

## Author

TODO: Your name and GitHub handle.
READMEEOF

# Wipe the wildhaven private_companion block — variant creates its own
python3 - <<'PYEOF'
import json
with open("rappid.json") as f:
    data = json.load(f)
data.pop("private_companion", None)  # variant inherits no private layer by default
with open("rappid.json", "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF

# Replace LICENSE with a placeholder note pointing at the chosen license decision
cat > LICENSE <<'LICENSEEOF'
TODO: Set the license for this variant.

The parent template (kody-w/wildhaven-ai-homes-twin) shipped under "All
Rights Reserved" with a "license TBD on incorporation" stance. Your
variant inherits whatever stance you choose; it is not bound to the
parent's choice unless you explicitly want it to be.

Common options:
  - "All Rights Reserved" (source-available, like the parent)
  - PolyForm Small Business 1.0.0 (free for individuals + small biz)
  - Apache 2.0 (open source, with patent grant)
  - MIT (open source, simpler)

Replace this file with the full text of your chosen license, plus a
copyright header.

Copyright (c) <YEAR> <YOUR NAME>.
LICENSEEOF

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
echo " Next steps:"
echo "   1. Edit soul.md, MANIFEST.md, README.md to remove the TODO markers."
echo "   2. Customize the agents under agents/ for your variant's purpose."
echo "   3. Update LICENSE with your chosen license."
echo "   4. (Optional) Create a private companion repo and add a"
echo "      'private_companion' block to rappid.json."
echo "   5. (Optional) Mark your repo as a template too:"
echo "        gh repo edit $GH_OWNER_REPO --template=true"
echo "   6. Commit + push:"
echo "        git add -A && git commit -m 'init: $VARIANT_NAME' && git push"
echo ""
echo " Lineage walk: your_rappid → $PARENT_RAPPID${parent_choice:+ ($([ "$parent_choice" = 1 ] && echo wildhaven-ai-homes-twin || echo rapp))} → ... → rapp species root"
echo ""
