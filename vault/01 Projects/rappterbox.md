---
type: project
status: active
tags: [project, rappterbox, console, public]
created: 2026-05-04
github: https://github.com/kody-w/rappterbox
spec: https://github.com/kody-w/rappterbox/blob/main/SPEC.md
---

# rappterbox

The local-first console. Brainstem + Wii Sports cartridges + dashboard, pre-bundled. Static ancestor: the rapp-installer brainstem is the immutable substrate; cartridges plug in; the console never changes.

## Why it exists

Most users don't want to assemble the brainstem + cartridges + UI by hand. rappterbox is the curated bundle — install once, get a working console in 30 seconds.

## What's bundled (Wii Sports)

Four cartridges ship pre-loaded:

- **ManageMemory** — save typed facts that survive across conversations
- **ContextMemory** — recall saved memories at conversation start
- **HackerNews** — top stories from HN's public Firebase API
- **LearnNewAgent** — the meta-cartridge: generates new agents at runtime

## Expansion packs

Optional cartridges, install on demand:

- `twin/` — `SummonTwin` + `HatchEgg` (the early pattern; superseded by the consolidated [[Twin agent]] in [[rapp-egg-hub]]'s `agents/`)

## The dashboard

`console.html` — a 2005-era 'blades' dashboard aesthetic. Horizontal blade tabs at top: My Cartridges · Twin Estate · Marketplace · System. Click a cartridge tile → modal with chat panel scoped to that cartridge.

## SPEC

The console spec: [SPEC.md](https://github.com/kody-w/rappterbox/blob/main/SPEC.md) — schema `rappterbox-console-spec/1.0`, frozen. Defines:

- Mental model (game console + cartridges + estate)
- Canonical paths (~/.brainstem, ~/.rapp, ~/.config/rapp)
- The cartridge contract (BasicAgent, manifest, hard rules)
- Kernel-side guarantees (loader, registered shims, vendored utilities)
- Egg cartridge format (brainstem-egg/2.x manifests)
- Peer registry schema (rapp-peers/1.1)
- Versioning + stability (frozen 1.0; additive-only)
- Lineage rules (Article XXXIV)
- Drop-in kernel replaceability (Article XXXIII)
- Compliance checklist for cartridge authors

## Install

```bash
curl -fsSL https://kody-w.github.io/rappterbox/installer/install.sh | bash
bash ~/.brainstem/src/rapp_brainstem/start.sh
open http://127.0.0.1:7071/web/console.html
```

## See also

- [[RAPP]] — the kernel underneath
- [[Brainstem]] — the runtime
- [[rapp-egg-hub]] — where rappterbox-compatible eggs live
