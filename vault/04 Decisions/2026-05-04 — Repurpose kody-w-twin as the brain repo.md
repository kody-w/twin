---
type: decision
status: shipped
date: 2026-05-04
tags: [decision, architecture, twin, vault]
---

# Repurpose `kody-w/twin` as the brain repo

## Context

`kody-w/twin` was originally a wildhaven-ai-homes-twin variant — same Pre-Founder twin pattern, just a personal copy. After several iterations of building [[rapp-egg-hub]] and [[rappterbox]], this repo's role evolved: it became the natural home for the deeper corpus that the public-facing [[kody-w.egg]] should point its [[Private Companion|private_companion]] block at.

## Decision

Repurpose `kody-w/twin` as Kody Wildfeuer's twin **brain repo**:

1. Update `rappid.json`: `name=kody-w`, `display_name=Kody Wildfeuer`, `kind=personal`, description reflects brain-repo role.
2. Update `soul.md`: reflects v1.0.5 identity block + the brain framing (not wildhaven Pre-Founder content).
3. Add `vault/` — Obsidian-formatted notes following [[wiki-link]] conventions:
   - `00 Index/` — entry points and MOCs
   - `01 Projects/` — one note per shipped project
   - `02 Concepts/` — recurring vocabulary
   - `03 Manifestos/` — stated positions
   - `04 Decisions/` — architectural decisions with rationale
   - `05 People/` — public-facing only
   - `06 Daily/` — daily notes (currently empty)
   - `07 Inbox/` — triage zone
4. Drop the wildhaven `private_companion` block from `rappid.json` (this IS the brain that other repos' private_companion blocks point AT).
5. Keep the bundled brainstem + agents/ + installer/ — the repo is still RUNNABLE as a variant; it just adopts a new primary purpose.

## Why now

The kody-w.egg in [[rapp-egg-hub]] declares a private_companion pointing at this repo. That made the role concrete: this repo is the **canonical depth** behind the **portable surface** in the egg.

Without a vault, the egg's private layer pointer was aspirational. With the vault, it's real: anyone with read access here gets the richer context the public egg can't carry.

## Rule respected: never overwrite local data

The repo's prior content (the brainstem, the agents, the rappterbox-style infrastructure we built earlier) is preserved. The vault is purely additive. Anyone who cloned this repo before the change still has a working variant install; they now ALSO have a brain.

## See also

- [[rapp-egg-hub]] — where the public egg lives
- [[Private Companion]] — the auth-gated escalation pattern
- [[rapp-twin-spec]] §5 — the formal spec for private_companion
