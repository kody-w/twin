---
type: concept
tags: [concept, wire, contract, immutability]
created: 2026-05-04
---

# Wire

The contract surface. Once a contract ships (`/chat` request shape, `/health` response, `/agents` list, the `|||VOICE|||` slot delimiter), it is **immutable**. Schema evolves only additively — new fields with defaults, never breaking changes.

## Why

Backwards compatibility is not a feature. It's a structural promise. **The wire is forever.** This is how protocols survive.

If a brainstem from a year ago can collaborate with a brainstem from today through nothing more than `/chat`, then `/chat` is the contract — whether we want it to be or not. See [[Chat Is The Only Wire]].

## Examples of frozen wire

- The `/chat` request: `{"user_input": "...", "conversation_history": [...]}`. Adding `session_id` later is fine; renaming `user_input` to `text` would break it forever.
- The response envelope: `{"response": "...", "agents_used": [...]}`. Same rule.
- The `|||VOICE|||` and `|||TWIN|||` slot delimiters in agent output. Fixed forever.
- The `BasicAgent` contract: `name`, `metadata`, `perform(**kwargs) -> str`. Don't change the signature.

## Schema versioning

When something has to change, it gets a new schema version (additive):

- `rapp-peers/1.0` → `rapp-peers/1.1` adds optional twin-aware fields
- `brainstem-egg/2.0` → `brainstem-egg/2.1` adds variant-repo specifics
- 1.x readers ignore unknown 1.y fields. 2.x is a sibling, not a successor.

## What's NOT on the wire

The kernel internals (line numbers, function names) are not wire. They can change freely as long as the wire stays the same. The wire is the public-facing API; everything else is implementation detail.

## See also

- [[Constitution]] — Article I (the brainstem definition) and Article XXXV (license stability)
- [[The Engine Stays Small]] — why the wire's smallness matters
- [[Chat Is The Only Wire]] — the manifesto
