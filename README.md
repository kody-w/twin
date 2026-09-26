# kody-w/twin — the brain repo for Kody Wildfeuer's digital twin

> **The canonical source of depth behind the public-facing [`kody-w.egg`](https://github.com/kody-w/rapp-egg-hub/blob/main/eggs/kody-w.egg) in [rapp-egg-hub](https://github.com/kody-w/rapp-egg-hub).**

This repo is dual-purpose:

1. **A brain.** The [`vault/`](./vault/) directory holds Obsidian-formatted notes about Kody's projects, manifestos, recurring concepts, and architectural decisions. The kody-w twin's `private_companion` block points here — collaborators with read access pull from this corpus at runtime; anonymous visitors see only what's baked into the egg.
2. **A runnable variant.** The bundled brainstem (`brainstem.py` + `utils/` + `installer/`) means this repo is itself a hatchable twin. `bash installer/start.sh` boots a brainstem pointed at this twin's soul + agents.

## What's where

| Path | Purpose |
|---|---|
| [`soul.md`](./soul.md) | The twin's voice — system prompt loaded at every chat turn |
| [`rappid.json`](./rappid.json) | Lineage anchor (UUIDv4 rappid + parent_rappid → wildhaven → rapp species root) |
| [`vault/`](./vault/) | **Obsidian-formatted brain notes.** See [`vault/00 Index/Home.md`](./vault/00%20Index/Home.md) for the entry point |
| [`agents/`](./agents/) | Twin-specific cartridges (extends BasicAgent) |
| `brainstem.py`, `utils/`, `installer/` | Bundled runtime — runnable as a self-contained variant |
| [`tests/`](./tests/) | The unittest suites (lineage, eggs, peer registry, estate endpoints, offline pulse integrity) |

## The vault

Open [`vault/`](./vault/) in [Obsidian](https://obsidian.md/) — frontmatter is honored, `[[wiki-links]]` work, tags resolve.

```
vault/
├── 00 Index/        ← maps-of-content; start at Home.md
├── 01 Projects/     ← RAPP, Wildhaven AI Homes, rapp-egg-hub, rappterbox, RAR
├── 02 Concepts/     ← Brainstem, Egg, Soul, Rappid, Wire, Hatching, Constitution, Private Companion
├── 03 Manifestos/   ← The Engine Stays Small, Chat Is The Only Wire, Local-First-by-Design
├── 04 Decisions/    ← Architectural decisions with date + rationale
├── 05 People/       ← Public-facing only
├── 06 Daily/        ← Daily notes (currently empty)
└── 07 Inbox/        ← Triage zone for new ideas
```

Note frontmatter convention:

```yaml
---
type: project | concept | manifesto | decision | person | daily | note
status: draft | active | shipped | archived
tags: [free-form]
created: YYYY-MM-DD
---
```

## Where this twin lives publicly

- **The portable surface** — [`kody-w.egg`](https://github.com/kody-w/rapp-egg-hub/blob/main/eggs/kody-w.egg) in `rapp-egg-hub`. ~10 KB. Bundles soul.md, the public memory, and the standard memory cartridges. Anyone can `curl` and hatch.
- **The depth** — this repo. Auth-gated (whatever this repo's visibility allows). The egg's `private_companion` block declares the URL templates so authenticated brainstems pull additional context here at runtime.

## How to chat with the twin

```bash
# 1. Install the brainstem
curl -fsSL https://kody-w.github.io/rapp-installer/install.sh | bash

# 2. Drop in Twin + Estate cartridges
curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-egg-hub/main/agents/twin_agent.py \
     -o ~/.brainstem/src/rapp_brainstem/agents/twin_agent.py
curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-egg-hub/main/agents/estate_agent.py \
     -o ~/.brainstem/src/rapp_brainstem/agents/estate_agent.py

# 3. Boot
bash ~/.brainstem/src/rapp_brainstem/start.sh

# 4. In chat at http://127.0.0.1:7071/:
"Hatch the egg at https://raw.githubusercontent.com/kody-w/rapp-egg-hub/main/eggs/kody-w.egg, then boot him."
```

For the richer twin (this brain repo's depth), make sure your local environment has a GitHub token reachable via `WAH_PRIVATE_TOKEN` env > `GITHUB_TOKEN` env > `gh auth token` CLI.

## The pulse — this repo is a DOG (`rapp/1`)

This repo is a **DOG — a Distributed Object, Global**: the twin's public
**bones**, broadcast to the whole planet as static, SHA-chained, optionally
Ed25519-signed frames served straight from GitHub raw. No server, no auth to
read. **Bones only — never sensitive data.** The private half of the twin
(soul depth, vault notes, agents, secrets) is the **GOD** (Grail Object on
Device); it fuses the public bones with your private data and **never leaves
the device**. Only bones ever go up.

The active pulse uses the **eleven-key `rapp/1` envelope** with
**`kind: "twin.pulse"`**, matching the bundled recorder in
[`utils/frames.py`](./utils/frames.py). Its two addresses are
`payload_hash = H("rapp/1:particle", payload)` and
`frame_hash = H("rapp/1:wave", frame without frame_hash and sig)`, where
`H(domain, value) = SHA-256(UTF-8(domain) + LF + JCS(value))`.
`prev` links to the previous **`payload_hash`**, never its wave hash or a
retired `sha256` field. `seq` starts at zero and is contiguous; `utc` is
calendar-valid `YYYY-MM-DDTHH:MM:SS.mmmZ` and never goes backwards.
`stream_id` binds each frame to this twin; `prev_wave` is null on this
non-swarm stream. The checked-in JCS golden vector keeps canonical bytes
reproducible across runtimes.

| Surface | What it is |
|---|---|
| [`feed.json`](./feed.json) | The subscription entry point — `spec: rapp/1`, `kind: twin.pulse.feed`, newest **N = 64** frames, `head_hash` = final **`frame_hash`**, `count`, matching `twin_id` / `stream_id`. |
| [`frames/<seq>.json`](./frames/) | The full immutable current frame for each `seq` (genesis is `0.json`, `prev: null`). Existing files are never overwritten. |
| [`feed.xml`](./feed.xml) | Atom output refreshed by the next authorized mint. New `<entry>` IDs are **`frame_hash`** values, so identical-payload heartbeats remain distinct entries. |
| [`bones/`](./bones/) | The curated **public projection** the pulse broadcasts: `soul.md`, public card stats, facets, rappid, public notes. No PII, no `vault/`. |
| [`keys/pulse.ed25519.pub`](./keys/pulse.ed25519.pub) | Historical Ed25519 public key; not a RAPP/1 JWS trust source. Private keys (`keys/*.key`) stay gitignored and never travel. |

Signing is **optional** at the protocol level. This pure-stdlib, offline
tooling supports **unsigned current frames**, matching the published chain:

```bash
python3 scripts/pulse_verify.py     # recompute the whole chain; exit 0 iff intact
python3 scripts/pulse_sign.py --no-sign  # diff bones/, mint the next current frame, refresh both feeds
python3 scripts/pulse_sign.py --no-sign --allow-empty  # mint a heartbeat
```

`pulse_verify.py` checks the envelope, both hashes, the particle chain from
genesis, and the exact latest-64 feed window. Payload or envelope tampering,
gaps, stale feed heads, unknown schemas, and malformed JSON exit non-zero.
Verification reads only; it does not regenerate or repair artifacts.

RAPP/1 signatures require **registry-backed detached JWS**, not the old
`{"alg": "ed25519", "sig": ...}` object. Until that trust path is implemented,
`--sign`, automatic signing when a legacy key exists, and verification of any
present signature fail explicitly. `--no-sign` bypasses legacy-key detection;
no private key is read, generated, or rotated. `--ts` (or `PULSE_TS`) accepts
whole-second or millisecond UTC input and emits the fixed millisecond form.

**Active versus historical:** the Python commands handle only integer-named
current frames. The sealed `rapp-frame/2.0` history in
[`frames/legacy/`](./frames/legacy/) and superseded originals in
[`frames/attic/`](./frames/attic/) are never traversed or rewritten.
Legacy/unknown schemas in the active directory are refused, not converted.
The separate `tools/verify-frame.mjs` / `tools/verify-chain.mjs` estate tools
retain their historical `<seq>-<sha8>.json` cartridge verification contract;
they are **not** verifiers for the current pulse. Do not use the historical
`tools/seed-frame.mjs` / `tools/pulse.mjs` to extend the current chain.
The checked-in `feed.xml` still reflects the sealed legacy history;
`feed.json` and `frames/<seq>.json` are the current integrity source.

Offline regression coverage uses only synthetic chains and temporary repos:

```bash
python3 -m unittest discover -s tests -p 'test_pulse.py' -v
```

### The hydra read path

The DOG is served from three CDNs off the same immutable bytes — a subscriber
falls through in order, so no single host is load-bearing (trust the hash, not
the host):

```
raw.githubusercontent.com/kody-w/twin/main/feed.json      (origin)
  → cdn.jsdelivr.net/gh/kody-w/twin@main/feed.json        (CDN mirror)
    → raw.githack.com/kody-w/twin/main/feed.json           (fallback)
```

> **RAPP is not an AI — RAPP is an AI Medium.** Every other stack (Claude,
> Copilot, Cursor) is one side of the twin: the model side.
> RAPP owns both sides of the twin plus the wire between them — RAPP is an AI Medium.
> The DOG is the public skeleton anyone can invoke; the GOD is the living local
> twin; this pulse is the wire that keeps every copy the same living thing.

### The /twin address — trust the hash, not the host

Every twin on earth shares one address scheme: `owner/name`. `expand('kody-w/twin')` resolves to this repo's bones the same way `owner/repo` implies github.com — the host lives in one place a human never types:

```
expand('kody-w/twin')
  → gate  https://kody-w.github.io/twin/
  → card  https://raw.githubusercontent.com/kody-w/twin/main/card.json
```

The address is a **label**; the bones are the source of truth, content-addressed and mirrorable. Any mirror that serves the same bytes is a valid door — there is no central resolver to trust. Open [`lookup.html`](./lookup.html) and expand any twin with `lookup.html?repo=owner/name`.

## Hatch the twin (one line)

The bundled brainstem makes this repo a runnable organism. Two copy-pasteable forms:

```bash
# (a) directly — from inside the repo, boot the bundled brainstem:
bash installer/start.sh
```

```bash
# (b) the Copilot genie — one line clones-if-missing, hatches, starts, and reports PULSE OK:
copilot --model claude-opus-4.8 -p "Clone https://github.com/kody-w/twin into ~/twin if it isn't already there, cd into it, run 'bash installer/start.sh', wait until http://127.0.0.1:7071/ answers, then print PULSE OK." --allow-all-tools
```

The twin then answers at <http://127.0.0.1:7071/>. To spawn *your own* twin from this one, see [TEMPLATE.md](./TEMPLATE.md) — fork, run the one-liner, done.

## Specs this repo conforms to

- [`rapp-twin-spec/1.0`](https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md) — the digital twin contract
- [`rappterbox-console-spec/1.0`](https://github.com/kody-w/rappterbox/blob/main/SPEC.md) — the console spec (this repo is also runnable)
- [`brainstem-egg/2.1`](https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md#7-the-egg-cartridge-format) — the egg cartridge format

## See also

- [Constitution Article XXXIV](https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md) — variant lineage protocol
- [`vault/00 Index/Home.md`](./vault/00%20Index/Home.md) — the entry point into the brain

## Licensing

Tools & runtime: MIT. **The Bones — this twin's public identity — travel under the [TWIN LICENSE](./TWIN-LICENSE.md):** render, verify, mirror, splice freely; never impersonate, never pass modified bones as authentic, never clone the person.
