---
type: concept
tags: [concept, private-companion, auth, escalation]
created: 2026-05-04
source: https://github.com/kody-w/rapp-egg-hub/blob/main/SPEC.md
---

# Private Companion

The auth-gated escalation pattern. A twin's `rappid.json` declares a `private_companion` block pointing at a separate GitHub repo. When the chatting user has read access via a GitHub token, the twin can pull additional context at runtime — same shape, different observed twin depending on who's looking.

## The shape

```json
"private_companion": {
  "repo": "https://github.com/<owner>/<repo>.git",
  "ssh": "git@github.com:<owner>/<repo>.git",
  "purpose": "Why this private layer exists.",
  "access_required": "Read access to <owner>/<repo>.",
  "mount_path": ".private/",
  "raw_url_template": "https://raw.githubusercontent.com/<owner>/<repo>/main/{path}",
  "tree_url_template": "https://api.github.com/repos/<owner>/<repo>/contents/{path}",
  "auth": {
    "scheme": "github_token",
    "scope_required": "repo",
    "_note": "Token resolution: WAH_PRIVATE_TOKEN env > GITHUB_TOKEN env > `gh auth token` CLI."
  }
}
```

## The flow

1. Anonymous user → no token → twin sees only what's in the [[Egg]]
2. Authenticated collaborator → token present, has read on the private repo → twin can fetch from `raw_url_template` for richer context
3. Authenticated non-collaborator → token present, no read access → 404, falls back to public-only

The user types the same question. The twin responds with whatever depth the user is authorized for.

## Implementation

The brainstem's `utils/private_layer.py` handles auth resolution:

1. Try `WAH_PRIVATE_TOKEN` env var
2. Try `GITHUB_TOKEN` env var
3. Try `gh auth token` CLI

If none works: graceful degradation. No error to the user; just less context.

## Why this design

- **Privacy-preserving by default.** Anonymous = public. The twin doesn't leak unauthenticated.
- **Decentralized.** No central auth server; piggybacks on GitHub's existing access controls.
- **Reversible.** If you remove someone's repo access, they immediately stop seeing private context.
- **Composable.** Many twins in [[rapp-egg-hub]] can point at the same private repo. One source of truth, many surfaces.

## Examples in the wild

- `wildhaven-ai-homes-twin` → `wildhaven-ai-homes-twin-private` (operational shadow: pipeline, financial model, hiring targets)
- `kody-w.egg` → `kody-w/twin` (this repo — the brain)

## See also

- [[Egg]] — the public surface that points at the private layer
- [[rapp-twin-spec]] §5 — the formal spec
- [[2026-05-04 — Repurpose kody-w-twin as the brain repo]] — the decision to use this pattern
