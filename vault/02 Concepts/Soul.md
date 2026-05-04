---
type: concept
tags: [concept, soul, voice, prompt]
created: 2026-05-04
---

# Soul

The system prompt that defines a twin's voice. Loaded at every chat turn. Markdown file at the root of every twin workspace: `<workspace>/soul.md`.

## What it contains

- **Who the twin is** (display name, kind, role)
- **How it speaks** (voice rules: sentence length, vocabulary, rhetorical moves)
- **What it knows** (corpus drawn from)
- **Hard rules** (what it refuses; what it always identifies itself as)
- **Identity block** (mandatory since rapp-twin-spec/1.0)
- **Impersonation hard rule** (mandatory)

## The mandatory identity block

Every twin's soul.md MUST include:

```markdown
## Identity — read this every turn

Your name is **<Display Name>**. When greeting someone for the first
time in a conversation, introduce yourself by name: "Hi, I'm <Name>."

Do not introduce yourself as "RAPP", "an AI assistant", "your AI helper",
"the brainstem", or any default branding.

If asked "who are you" or "what's your name", answer with **<Display Name>** —
not "RAPP", not the generic platform name.
```

This fixes the historical bug where twins fell back to introducing themselves as "RAPP".

## The mandatory impersonation rule

Every twin of a person/place/project MUST distinguish itself from the human/thing it represents. See [[rapp-twin-spec]] §10.

## Adapting the soul (twins grow)

Twins are not static. The Twin agent's `update_soul` action replaces soul.md with new content; ALWAYS backs up the prior version to `<workspace>/.brainstem_data/soul_history/<ts>-<reason>.md` first.

Reverting: `cp soul_history/<ts>.md soul.md`. Twins adapt safely.

## See also

- [[Egg]] — the cartridge soul travels in
- [[Rappid]] — the identity that doesn't change even when soul does
- [[rapp-twin-spec]] — the contract for soul content
