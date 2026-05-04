---
type: concept
tags: [concept, hatching, lifecycle, egg]
created: 2026-05-04
---

# Hatching

The act of materializing an [[Egg]] into a running twin. The Twin agent's `hatch` action does this:

1. Read the `.egg` (local file via `egg_path` or remote URL via `egg_url`)
2. Verify integrity (sha256 against sidecar from [[rapp-egg-hub]] or explicit `expect_sha256`)
3. Unpack `repo/` → `~/.rapp/twins/<rappid>/`
4. Unpack `data/` → `~/.rapp/twins/<rappid>/.brainstem_data/`
5. Verify viability (rappid.json present, soul.md present)
6. Return the workspace path + boot recipe

Then `Twin(action="boot", rappid_uuid="<rappid>")` brings the twin online — starts a brainstem process pointing at the workspace's soul + agents on a fresh port.

## Hatching from a URL (the hub pattern)

```
User: "Hatch the egg at https://raw.githubusercontent.com/kody-w/rapp-egg-hub/main/eggs/grandma-rose.egg"
Model: <invokes Twin(action="hatch", egg_url="...")>
Tool: downloads, sha256-verifies, unpacks
Tool returns: workspace path + suggested next action
Model: <invokes Twin(action="boot", rappid_uuid="...")>
Tool: starts brainstem, returns http://127.0.0.1:7081/
```

## The hatching cycle (kernel updates)

Twins survive kernel updates via the egg-based hatching cycle:

1. **Lay egg** — pack current workspace into `.egg` (preserves identity + memory + mutations)
2. **Swap kernel** — replace the brainstem.py files with new ones
3. **Summon back** — `hatch` the egg again with `keep_existing_kernel=True`

No git merge, no conflicts. The egg is the organism; the brainstem is the runtime. Updating the runtime doesn't disturb the organism.

## See also

- [[Egg]] — the cartridge that gets hatched
- [[Rappid]] — the identity preserved across hatches
- [[Brainstem]] — the runtime the twin lands on
