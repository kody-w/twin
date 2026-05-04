---
type: index
tags: [moc, home]
created: 2026-05-04
---

# Home

> The brain repo for the kody-w twin. Obsidian-formatted vault. Wiki-links work; frontmatter is honored; tag from anywhere.

## What this vault is

This is **Kody Wildfeuer's twin brain**. The companion to the public-facing `kody-w.egg` published in [[rapp-egg-hub]]. The egg is portable; this vault is the depth.

Twins hatched from the egg can pull from this vault at runtime via the `private_companion` block. Anonymous visitors get only what's baked into the egg; collaborators with read access here get the richer corpus.

## Vault layout

| Folder | Contents |
|---|---|
| `00 Index/` | Maps-of-content like this one. Entry points. |
| `01 Projects/` | One note per project: [[RAPP]] · [[Wildhaven AI Homes]] · [[rapp-egg-hub]] · [[rappterbox]] · [[RAR]] |
| `02 Concepts/` | The recurring vocabulary: [[Brainstem]] · [[Egg]] · [[Soul]] · [[Rappid]] · [[Wire]] · [[Slot]] · [[Hatching]] · [[Constitution]] |
| `03 Manifestos/` | Stated positions: [[Chat Is The Only Wire]] · [[The Engine Stays Small]] · [[Local-First-by-Design]] |
| `04 Decisions/` | Architectural decisions with rationale. |
| `05 People/` | Public-facing only. |
| `06 Daily/` | Daily notes (currently empty). |
| `07 Inbox/` | Triage zone for new ideas before they get filed. |

## Where things live in the broader ecosystem

- **The kernel** — [`kody-w/RAPP`](https://github.com/kody-w/RAPP). Sacred, drop-in replaceable, never modified by AI assistants. The brainstem under `rapp_brainstem/`.
- **The console** — [`kody-w/rappterbox`](https://github.com/kody-w/rappterbox). Brainstem + Wii Sports + dashboard. Spec at [`rappterbox/SPEC.md`](https://github.com/kody-w/rappterbox/blob/main/SPEC.md).
- **The agent catalog** — [`kody-w/RAR`](https://github.com/kody-w/RAR). 285+ cartridges across 10 publishers.
- **The egg hub** — [`kody-w/rapp-egg-hub`](https://github.com/kody-w/rapp-egg-hub). The public catalog of `.egg` cartridges. Spec at [`rapp-egg-hub/SPEC.md`](https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md).
- **The variant template** — [`kody-w/wildhaven-ai-homes-twin`](https://github.com/kody-w/wildhaven-ai-homes-twin). What this twin descended from.

## Reading paths

If you're new and want to understand this ecosystem in 30 minutes:

1. [[The Engine Stays Small]] — the philosophical core
2. [[Chat Is The Only Wire]] — the protocol commitment
3. [[Local-First-by-Design]] — why permanence requires sovereignty
4. [[RAPP]] — what was built first
5. [[Wildhaven AI Homes]] — what the platform is for

If you want to ship a twin in 5 minutes: see [[rapp-egg-hub]] for the curl-and-hatch flow.

## Constitution articles I cite most

- **Article I** — the brainstem is a loader + an LLM loop + a response splitter, that's it
- **Article XXXII** — the litmus test for kernel vs. body_function
- **Article XXXIII** — the kernel is sacred and drop-in replaceable
- **Article XXXIV** — single-parent rule for variants
- **Article XXXIV.7** — variant attestation (rolling out)
- **Article XXXV** — licenses only relax, never tighten
