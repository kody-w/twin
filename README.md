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
| [`tests/`](./tests/) | The 57-test unittest suite (lineage, eggs, peer registry, estate endpoints) |

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

## The pulse — the twin's public bones, broadcast

The twin has two halves. The **private half** — soul depth, vault notes, agents — is sealed and lives on-device (it never travels). The **public half** is the twin's *bones*: no PII, publishable, content-addressed. The bones broadcast as a **pulse** — a static, RSS/Atom-like feed of signed frames served straight from this repo, no server, hydra-mirrorable.

| Surface | What it is |
|---|---|
| [`feed.xml`](./feed.xml) | The pulse — an Atom feed of signed frames. Edges subscribe, verify, assimilate. |
| [`frames/`](./frames/) | Append-only history. Each frame `{sha, prevSha, ts, kind, cart\|delta, sig}` as `<seq>-<sha8>.json`; `HEAD` points at the latest. |
| [`lookup.html`](./lookup.html) | `/twin` global lookup — `expand('owner/name')` → the person behind the twin. |
| [`gallery/`](./gallery/index.html) | A static portfolio hosted purely from the bones. |
| [`card.json`](./card.json) | The bones' identity card, incl. `twin.{twinId, who, pubkey, surfaces, primary}`. |

Every frame is **signed by the on-device twin** (Ed25519) and **content-addressed** as `twin@<sha8>`. The private signing key (`keys/twin.key`) never leaves the device — only the public key ships in the bones (`card.json`, `keys/twin.pub`). So anyone can verify a frame from the bones alone:

```bash
node tools/verify-frame.mjs frames/0-<sha8>.json   # OK — tamper a byte → non-zero exit
node tools/pulse.mjs                                # regenerate feed.xml from frames/
node tools/seed-frame.mjs                           # snapshot the current bones as frame 0
```

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
