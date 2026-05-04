---
type: manifesto
tags: [manifesto, philosophy, minimalism]
created: 2026-05-04
source: https://github.com/kody-w/RAPP/blob/main/pages/vault/Manifestos/The%20Engine%20Stays%20Small.md
---

# The Engine Stays Small

> The engine stays small so the agents can be everything.

## The conservation law

There is a fixed budget of complexity in any platform. RAPP spends it on agents, not on the engine.

Every line in the kernel is a line not in the user's hands. Every abstraction the platform forces is an abstraction the user can't refuse. Every credential the platform demands is a credential the user can't avoid. Every framework convention the platform encodes is a convention the user can't escape.

Complexity spent on the engine is complexity not spent on the agents. Complexity spent on the agents is complexity the user controls.

## Why this matters

Most platforms grow because each new feature adds value. RAPP refuses this trajectory. New features ARE agents — single-file drop-ins under `agents/`. The engine stays at ~1500 lines. The 285+ agents in [[RAR]] are where the value lives.

This is the same principle as Unix philosophy ("do one thing well") applied to AI infrastructure: the brainstem does ONE thing — load + LLM-loop + split — and does it well. Everything else is a tool the user composes.

## What this means in practice

- No decorators in user code. `class MyAgent(BasicAgent)` is the entire framework surface.
- No build step. Drop `*_agent.py` into `agents/`, restart, available.
- No vendor SDK lock-in. The LLM call is one HTTP request to whatever endpoint the user has credentials for.
- No hidden state. Every persistent thing is a file the user can read.
- No "magic". The brainstem is small enough to read in an afternoon.

## See also

- [[Brainstem]] — the engine itself
- [[Wire]] — the contract that stays frozen so the engine can stay small
- [[Constitution]] — the legal encoding of these principles
