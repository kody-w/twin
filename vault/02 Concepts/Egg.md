---
type: concept
tags: [concept, egg, cartridge, transport]
created: 2026-05-04
schema: brainstem-egg/2.1
---

# Egg

A `.egg` is a portable digital organism — a zip cartridge containing a [[Rappid|rappid.json]] (lineage), a [[Soul|soul.md]] (voice), conversation memory, and any local mutations the original keeper made.

## What's inside

```
<egg>.egg                               (zip)
├── manifest.json                       ← schema brainstem-egg/2.1
├── repo/                               ← public repo tree
│   ├── rappid.json
│   ├── soul.md
│   ├── MANIFEST.md, README.md, LICENSE
│   ├── agents/                         ← bundled cartridges
│   ├── utils/, installer/              ← optional kernel pin
└── data/                               ← .brainstem_data tree
    ├── memory.json
    ├── identity.json
    └── conversations/
```

`soul_history/` is intentionally NOT included — receivers don't need the donor's edit log.

## Schema versions

| Schema | Use |
|---|---|
| `brainstem-egg/2.0` | rapplications, twins, snapshots, swarms (rapp-instance shape) |
| `brainstem-egg/2.1` | variant repos (default for twins) |
| `brainstem-egg/2.2-organism` | brainstem-instance organisms |
| `brainstem-egg/2.2-rapplication` | rapplications with state cartridge |

## How it gets created

The Twin agent's `lay_egg` action packs a workspace at `~/.rapp/twins/<rappid>/` into a `.egg` blob, lands it at `~/.rapp/eggs/<rappid>/<timestamp>.egg`, and writes a sidecar JSON with sha256.

## How it gets used

The Twin agent's `hatch` action accepts either `egg_path` (local file) or `egg_url` (remote URL). For URLs, downloads to `~/.rapp/.tmp/`, then unpacks into `~/.rapp/twins/<rappid>/`. Auto-fetches the matching sidecar from [[rapp-egg-hub]] for sha256 verification when the URL matches the hub pattern.

## Why eggs matter

- **Portability.** Move a twin between devices in seconds. No reinstall, no reconfig.
- **Identity preservation.** The [[Rappid]] is permanent. The egg carries it. Same twin, different substrate.
- **Backup.** Lay an egg = take a snapshot. Restore = hatch the egg.
- **Distribution.** Eggs in [[rapp-egg-hub]] are public, hatchable by anyone.
- **Kernel updates.** The egg-based hatching cycle (lay → swap kernel → summon) sidesteps git merge entirely.

## See also

- [[Rappid]] — the identity that survives the egg roundtrip
- [[Hatching]] — the action that materializes an egg
- [[rapp-egg-hub]] — where eggs live publicly
