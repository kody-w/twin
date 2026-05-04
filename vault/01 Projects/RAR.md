---
type: project
status: active
tags: [project, rar, agents, registry, public]
created: 2026-05-04
github: https://github.com/kody-w/RAR
---

# RAR

The public agent catalog. `*_agent.py` files namespaced under `@<github-handle>`. ~285 agents across 10 publishers as of 2026.

## What it is

A static registry — no server, no auth for reads, just files in a GitHub repo. Anyone can `curl` an agent file and drop it in `~/.brainstem/agents/`. The brainstem auto-loads on next boot.

## Layout

```
RAR/
├── agents/
│   ├── @kody-w/
│   │   ├── twin_agent.py
│   │   ├── estate_agent.py
│   │   ├── hello_world_agent.py
│   │   └── vibe_coding_loop_agent.py
│   ├── @rapp/
│   │   ├── basic_agent.py
│   │   ├── manage_memory_agent.py
│   │   ├── context_memory_agent.py
│   │   ├── hacker_news_agent.py
│   │   └── learn_new_agent.py
│   └── @<other-publishers>/
├── registry.json                ← machine-readable catalog
├── api.json                     ← API discovery
├── rapp_sdk.py                  ← contract test runner
├── template_agent.py            ← author template
└── README.md
```

## Submission flow

1. Register a binder (one-time per namespace) — open a GitHub issue with `[RAR] register_binder`.
2. Place agent at `agents/@<your-handle>/<slug>_agent.py`.
3. Include a `__manifest__` dict (schema `rapp-agent/1.0`).
4. Test with `python rapp_sdk.py test agents/@<your-handle>/<slug>_agent.py`.
5. Open a GitHub issue with the code OR PR directly.

## Naming rules

**snake_case everywhere. No dashes.** Enforced at every layer.

- Filename: `my_agent.py`
- Manifest name: `@yourname/my_agent`
- Dependencies: `@rapp/basic_agent`

## What I've published there

- `@kody-w/twin_agent` — full twin lifecycle (latest v1.0.5)
- `@kody-w/estate_agent` — read-only estate inspection
- `@kody-w/hello_world_agent` — tutorial agent
- `@kody-w/vibe_coding_loop_agent` — agent that vibes through coding tasks

## See also

- [[rapp-egg-hub]] — companion catalog for `.egg` cartridges (the organism format; RAR is the cartridge format)
- [[rappterbox]] — bundles agents from RAR as Wii Sports + expansion packs
- [[Soul]] — what every agent's `perform()` method extends
