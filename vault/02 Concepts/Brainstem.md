---
type: concept
tags: [concept, brainstem, kernel]
created: 2026-05-04
---

# Brainstem

The minimal Flask runtime that hosts agents. ~1500 lines of Python. Loads `*_agent.py` from `agents/`, dispatches `*_service.py` (or `*_body_function.py`) at `/api/<name>/`, exposes a `/chat` endpoint that round-trips through the configured LLM.

## What it is

- A loader (discovers `*_agent.py` files)
- An LLM loop (sends messages, receives tool-call responses)
- A response splitter (parses `|||VOICE|||`, `|||TWIN|||` slots)

That's it. See [[Constitution]] Article I.

## What it isn't

- Not a framework. No decorators, no class hierarchy beyond `BasicAgent`.
- Not a UI. The `/chat` endpoint is the contract; UI is a separate concern.
- Not modifiable. AI assistants never edit brainstem.py. New features are agents or body_functions. See [[Constitution]] Article XXXIII.

## Where it lives

After [[RAPP]] install via `rapp-installer`:

```
~/.brainstem/
├── src/                      ← full kody-w/RAPP clone
│   └── rapp_brainstem/       ← the brainstem source
│       ├── brainstem.py      ← the kernel
│       ├── agents/           ← *_agent.py files (auto-loaded)
│       └── utils/            ← kernel-sibling utilities
├── venv/                     ← Python runtime
└── memory.json               ← persistent state
```

## Drop-in replaceability (Article XXXIII)

The kernel is sacred. A user can `cp upstream/brainstem.py ~/.brainstem/.../brainstem.py` over a locally-mutated install, and the organism keeps living. Cartridges are not invalidated by kernel updates.

The egg-based hatching cycle (lay-egg → swap kernel → summon back) exists exactly so kernel updates never lose state.

## Multi-tenancy

The brainstem is single-tenant. Each running instance hosts ONE [[Soul]] + ONE set of agents on ONE port. Multiple twins on a device = multiple brainstem processes, each on its own port (7071 = global, 7081+ = twin-only). See [[Twin Estate]].

## See also

- [[Egg]] — what travels between brainstems
- [[Hatching]] — how a twin lands on a brainstem
- [[Wire]] — the contract surface
