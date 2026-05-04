---
type: manifesto
tags: [manifesto, philosophy, wire, chat]
created: 2026-05-04
source: https://github.com/kody-w/RAPP/blob/main/pages/vault/Manifestos/Chat%20Is%20The%20Only%20Wire.md
---

# Chat Is The Only Wire

> If a brainstem from a year ago can collaborate with a brainstem from today through nothing more than `/chat`, then `/chat` is the contract — whether we want it to be or not.

## The principle

Not "chat is a feature" — chat is **the** [[Wire]]. The protocol surface. Every other endpoint is a convenience; every other API is optional; every other UI is interchangeable. Chat is what makes a brainstem a brainstem.

## The implication

Once you accept that chat is the wire, two things follow:

1. **Cross-twin collaboration is free.** Twin A on brainstem 1 talks to Twin B on brainstem 2 via `/chat`. There's no "AI-to-AI protocol" to design — the protocol is already there. From the receiving brainstem's perspective, an AI client looks identical to a human client. We don't change anything.

2. **The wire must never change.** Because if `/chat` changes shape, every brainstem that ever shipped is incompatible with every brainstem that ships next. Twins crossing time zones — that requires forever-stable contract.

## What this rules out

- **Specialized AI-to-AI protocols.** No need. Chat is the seam.
- **Vendor lock-in via custom APIs.** If the API isn't `/chat`, it's optional.
- **UI-driven interactions.** UIs come and go; the wire stays.
- **Breaking schema changes.** Ever. See [[Constitution]] Article on the wire.

## What this enables

- **Twin chat.** Two AIs talking via the same channel humans use.
- **Cross-tier portability.** Same agent runs in cloud, enterprise, and local — same wire.
- **Time-travel safety.** A 2025 brainstem can chat with a 2030 brainstem.
- **Decentralized federation.** Any host that speaks `/chat` is a peer. No registry, no auth, just the wire.

## See also

- [[Wire]] — the immutability principle
- [[The Engine Stays Small]] — why the engine doesn't grow features that would touch the wire
- [[Constitution]] — Article I (the brainstem definition) makes chat first-class
