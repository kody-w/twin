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

## Specs this repo conforms to

- [`rapp-twin-spec/1.0`](https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md) — the digital twin contract
- [`rappterbox-console-spec/1.0`](https://github.com/kody-w/rappterbox/blob/main/SPEC.md) — the console spec (this repo is also runnable)
- [`brainstem-egg/2.1`](https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md#7-the-egg-cartridge-format) — the egg cartridge format

## See also

- [Constitution Article XXXIV](https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md) — variant lineage protocol
- [`vault/00 Index/Home.md`](./vault/00%20Index/Home.md) — the entry point into the brain
