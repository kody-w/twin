---
type: project
status: active
tags: [project, hub, eggs, public]
created: 2026-05-04
github: https://github.com/kody-w/rapp-egg-hub
spec: https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md
---

# rapp-egg-hub

The public catalog of [[Egg]] cartridges. Pull any `.egg` by URL and [[Hatching|hatch]] it locally — your brainstem becomes the home of that twin in 30 seconds.

## What's in it today

| Slug | Display | Kind | Notes |
|---|---|---|---|
| `grandma-rose` | Grandma Rose | memorial | First seed. Demo memorial twin built from family memories. |
| `kody-w` | Kody Wildfeuer | personal | Public-facing twin of @kody-w. Bundles standard memory cartridges; private_companion points at this brain repo (`kody-w/twin`). |

## How users hatch

```bash
# 1. Brainstem (the static-ancestor substrate)
curl -fsSL https://kody-w.github.io/rapp-installer/install.sh | bash

# 2. Drop in Twin + Estate cartridges
curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-egg-hub/main/agents/twin_agent.py \
     -o ~/.brainstem/src/rapp_brainstem/agents/twin_agent.py
curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-egg-hub/main/agents/estate_agent.py \
     -o ~/.brainstem/src/rapp_brainstem/agents/estate_agent.py

# 3. Boot
bash ~/.brainstem/src/rapp_brainstem/start.sh

# 4. In chat:
"Hatch the egg at https://raw.githubusercontent.com/kody-w/rapp-egg-hub/main/eggs/<slug>.egg, then boot."
```

## Auto-rebuild

`scripts/rebuild_index.py` walks `eggs/`, computes sha256, parses each manifest + sidecar, regenerates `index.json`. The GitHub Action `.github/workflows/rebuild-index.yml` fires on push to main when anything under `eggs/` changes — idempotent (only commits if `index.json` actually differs).

Hub maintainers contributing eggs just drop `<slug>.egg` + `<slug>.json` into `eggs/`, open a PR. After merge, the action handles the rest.

## Integrity verification

**Phase 1 (shipped):** sha256 in every sidecar. The Twin agent's `hatch` action auto-fetches the sidecar when the URL matches the hub pattern, computes local hash, refuses on mismatch. See [[Constitution]] Article XXXIV.7.

**Phase 2 (future):** ed25519 publisher signatures. The `attestation` slot in every brainstem-egg/2.1 manifest is wired and ready.

## Spec

The full digital-twin contract: [SPEC.md](https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md) — schema `rapp-twin-spec/1.0`, frozen. Read it before contributing an egg you want others to hatch.

## See also

- [[Egg]] — what an egg cartridge is
- [[Hatching]] — the lifecycle action
- [[Soul]] — the voice every twin must have
- [[Rappid]] — the identity rule (single-parent)
