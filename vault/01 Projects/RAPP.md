---
type: project
status: active
tags: [project, rapp, infrastructure, public]
created: 2026-05-04
github: https://github.com/kody-w/RAPP
---

# RAPP

**Rapid Agent Prototype Platform.** The species root. Where the [[Brainstem]] kernel lives. The substrate every other project descends from via the [[Rappid]] lineage chain.

## What it is

A platform for digital organisms. Single-file agents (`*_agent.py`), GitHub Copilot as the LLM backend (no vendor lock-in — uses tokens already on your machine), a brainstem small enough to read in an afternoon. Infrastructure-as-philosophy.

## What it isn't

Not a framework. No decorators, no DSLs, no class hierarchy beyond `BasicAgent`. The point is to spend the platform's complexity budget on user agency, not engine cleverness.

## Why I built it

[[The Engine Stays Small]] is the philosophical core. Every line in the kernel is a line not in the user's hands. The constitutional position from [[Constitution]] Article XXXIII: the kernel is sacred and drop-in replaceable.

I needed a runtime where I could iterate on agents without rebuilding the platform every time. Where adding a capability meant dropping a file in a folder, not subclassing a framework. Where the platform never assumed credentials I didn't already have.

## Key articles

- **Article I** — the brainstem is a loader + an LLM loop + a response splitter
- **Article XXXII** — the kernel/body_function litmus test
- **Article XXXIII** — drop-in kernel replaceability
- **Article XXXIV** — single-parent rule for variants
- **Article XXXV** — licenses only relax, never tighten

## What it powers

- [[rappterbox]] — bundles RAPP's brainstem + the Wii Sports cartridges + a dashboard
- [[Wildhaven AI Homes]] — the residence layer; descended from RAPP via lineage
- [[rapp-egg-hub]] — the egg cartridge catalog; eggs hatch on RAPP brainstems
- [[RAR]] — the public agent catalog; agents are `*_agent.py` files conforming to RAPP's `BasicAgent`

## How to install

```bash
curl -fsSL https://kody-w.github.io/rapp-installer/install.sh | bash
```

Lands at `~/.brainstem/`. The full RAPP repo gets cloned to `~/.brainstem/src/`; the canonical brainstem code is at `~/.brainstem/src/rapp_brainstem/`.
