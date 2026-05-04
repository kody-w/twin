---
type: concept
tags: [concept, constitution, governance]
created: 2026-05-04
source: https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md
---

# Constitution

The 35+ articles governing [[RAPP]]. Lives at `kody-w/RAPP/CONSTITUTION.md`. Changes only via deliberate constitutional commit; never via routine refactors.

## Articles I cite most

### Article I — The brainstem
> The brainstem is a loader + an LLM loop + a response splitter. That's it. Nothing else.

### Article XXXII — Kernel vs. body_function
The litmus test: **what does chat require?** That's kernel. Everything else is a body_function (a `*_service.py`). The kernel can boot without any body_functions.

### Article XXXIII — Drop-in kernel replaceability
> A user must be able to `cp upstream/brainstem.py ~/.brainstem/.../brainstem.py` over a locally-mutated install, and the organism keeps living.

The kernel is sacred. AI assistants never edit it. New features are agents or body_functions.

### Article XXXIV — Single-parent rule for variants
A twin's `parent_rappid` declares its code ancestor — no exceptions. You can only claim as parent the repo whose code you actually inherited. See [[Rappid]].

### Article XXXIV.7 — Variant attestation
Rolling out. Eggs will carry an `attestation` envelope signed by the publisher's release key. The slot is wired today (`"attestation": null`); the signing infrastructure ships when key management is decided.

### Article XXXV — Licenses only relax, never tighten
> Past versions of RAPP stay as permissive as they were on release day. Future versions can only loosen, never restrict. Once code is shipped under a license, downstream users can rely on it forever.

This is the equivalent commitment to the wire's immutability — applied to legal terms.

## Why the constitution exists

So the platform's invariants are LAW, not convention. So future contributors know not just WHAT but WHY. So design decisions are auditable. The constitution is governance-as-law, not governance-as-vibe.

## See also

- [[The Engine Stays Small]] — the philosophy the constitution encodes
- [[Wire]] — the immutability principle as applied to APIs
- [[Brainstem]] — what Article I + XXXIII govern
