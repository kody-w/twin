# Wildhaven AI Homes — Pre-Founder Twin

> **This repository is a brand operating in public, before the team incorporates.**

This is not yet a company. It is a *Pre-Founder twin* — a digital organism that holds the brand's vision, voice, and operational presence ahead of the human team that will eventually staff it. The twin lives here. You can read everything it has decided. You can talk to it. You can disagree with it. When the founding team is hired, they will inherit eighteen months of synthetic operational memory as their first day's onboarding.

If you found this repo and you're confused: that's the build-in-public bet. We think it's a more honest way to start a company than waiting until everything's ready. Read on.

---

## What is Wildhaven AI Homes?

> **A home for every digital organism.**

Twins, agents, brand personas, family memorial twins, project twins — every meaningful AI organism needs a place to live: somewhere to accumulate memory, somewhere to be reached, somewhere to outlive the laptop that birthed it. Wildhaven AI Homes will be the hosting layer for digital organisms. You bring the soul; we bring the substrate.

The product is not an LLM. It is the long-term residential infrastructure: hosting, memory, identity, lineage, observability, succession planning. Built on the [RAPP digital-organism platform](https://github.com/kody-w/RAPP) — this twin is in fact a **descendant variant** of RAPP, with `parent_rappid` pointed at rapp's species root in [`rappid.json`](./rappid.json).

## What this repo is for

1. **The brand's voice in public.** [`soul.md`](./soul.md) is the system prompt the twin uses every time it speaks. It is the founder voice before there is a founder.
2. **The operational record.** Every commit is the twin acting in the world. PRs are decisions. Issues are deliberations. The git log is the twin's life.
3. **The vision document.** [`MANIFEST.md`](./MANIFEST.md) is what Wildhaven AI Homes intends to be when it has people. Read it like a pitch deck written by the company itself.
4. **A live demonstration of the platform.** This repo is itself a working RAPP variant. You can clone it, point a brainstem at its `agents/` and `soul.md`, and *talk* to the twin. See "Running the twin" below.

## How this repo descends from RAPP

This is a RAPP **variant** per [Constitution Article XXXIV](https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md). The lineage:

```
rapp (kody-w/RAPP, rappid 0b635450-...)
  └── wildhaven-ai-homes-twin (this repo, rappid 37ad22f5-...)
       │
       └── (future) the Wildhaven AI Homes company organism, when founders staff it
```

`parent_commit` in [`rappid.json`](./rappid.json) records the exact rapp main commit this variant forked from. The lineage is walkable forever via the parent_rappid chain.

## Running the twin

This repo carries the brand-specific content (soul + agents + body_functions). It does **not** carry a kernel — that lives upstream at [kody-w/RAPP](https://github.com/kody-w/RAPP). To run the twin locally:

```bash
# 1. Install the RAPP brainstem (one-liner from the upstream)
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash

# 2. Point the running brainstem at THIS variant's content
git clone https://github.com/kody-w/wildhaven-ai-homes-twin.git ~/wah-twin
SOUL_PATH=~/wah-twin/soul.md \
  AGENTS_PATH=~/wah-twin/agents \
  ~/.brainstem/start.sh

# 3. Talk to the twin
curl -X POST http://localhost:7071/chat \
  -H "Content-Type: application/json" \
  -d '{"user_input":"What is Wildhaven AI Homes?"}'
```

Or, when the future `hatchling lay-egg` capability ships in the upstream, a single command will scaffold a brainstem against any variant repo's `rappid.json`.

## Layout

```
.
├── rappid.json                    — lineage identity (parent → rapp's species root)
├── README.md                      — this file
├── MANIFEST.md                    — the brand's vision in long-form
├── LICENSE                        — All Rights Reserved (source-available, not open-source)
├── soul.md                        — the system prompt the twin uses every turn
├── agents/
│   ├── basic_agent.py             — base class, inherited from rapp
│   ├── founder_voice_agent.py     — speaks for the future founder
│   ├── operations_agent.py        — handles operational questions
│   ├── pitch_agent.py             — refines the pitch for investors
│   └── customer_inquiry_agent.py  — responds to interest from prospective customers
└── utils/
    ├── private_layer.py            — bridge to the private companion repo (auth-gated)
    └── body_functions/
        └── manifest_body_function.py  — serves /api/manifest/* (vision + contact + status)
```

## The private layer (operator-only)

The Pre-Founder twin has a **private companion repo** at [`kody-w/wildhaven-ai-homes-twin-private`](https://github.com/kody-w/wildhaven-ai-homes-twin-private) that holds operational state the twin uses to reason but never publishes (real pipeline, financial model, hiring targets, founder notes, research). The pointer to it lives in [`rappid.json`](./rappid.json) under `private_companion`.

**Two access paths**, both supported by [`utils/private_layer.py`](./utils/private_layer.py):

1. **Local clone** — fast, offline-capable, zero-network. From inside this working dir:
   ```bash
   git clone git@github.com:kody-w/wildhaven-ai-homes-twin-private.git .private
   ```
   `.private/` is gitignored so the clone never leaks into commits.

2. **Authenticated remote fetch** — no clone required. Files are fetched via authenticated HTTPS from the private repo's `raw.githubusercontent.com` URLs. **Anonymous requests return 404; authenticated requests with a token that has `repo` scope return the real content.** Token resolution order: `WAH_PRIVATE_TOKEN` env > `GITHUB_TOKEN` env > `gh auth token` CLI subprocess.

The `private_context` agent uses this layer to inform every chat turn when either path is available — and the twin's `soul.md` constrains the LLM to never quote private content verbatim in public-facing output. **No private content is ever served via HTTP from this twin.** The only thing that leaves the brainstem process is an agent's transformed, public-safe summary.

Privacy boundary verified:
- `curl https://raw.githubusercontent.com/kody-w/wildhaven-ai-homes-twin-private/main/operational/pipeline.json` → 404 (anonymous)
- `curl -H "Authorization: token $(gh auth token)" ...` → 200 (operator)

## What this repo is NOT

- **Not a product.** When Wildhaven AI Homes ships, it will be a hosted service. This repo is the brand operating before the service exists.
- **Not a finished company.** No founders, no Delaware C-corp, no payroll. Just the twin.
- **Not a fork in the negative sense.** This is a *variant* of RAPP per the constitutional lineage protocol. The upstream master gains nothing by being polluted with this repo's history; this repo loses nothing by being downstream of upstream.
- **Not a deception.** The twin always identifies itself as a twin. It does not pretend to be a person.

## How to engage

- **Open an issue** — challenge the twin's vision, ask what its position on X is, propose a direction.
- **Open a PR** — draft a press release as the twin would, refine the pitch, propose a product direction.
- **Talk to the twin live** — clone, point a brainstem at the soul + agents, have a real conversation.
- **Watch the commit log** — every push is the twin doing something. The git history is the public record of a brand thinking out loud.

## Lineage

- **Species root:** [kody-w/RAPP](https://github.com/kody-w/RAPP) — the platform.
- **This variant:** kody-w/wildhaven-ai-homes-twin — the brand's Pre-Founder twin.
- **Future child:** the Wildhaven AI Homes company organism, when founders are hired. They will fork from this repo at the commit where they take over; the twin's accumulated memory becomes their inheritance.

## License

**Source-available, not open-source.** All rights reserved. See [`LICENSE`](./LICENSE).

This repository is public so the brand can operate, iterate, and be evaluated transparently. It is not a software-libre release — content and code may not be copied, redistributed, or used to operate a competing brand. License terms will be relaxed and clarified when the company incorporates. The pattern this repo demonstrates (Pre-Founder twin as a RAPP variant) is freely reusable; *this specific brand's content* is not.

## Topics

`rapp-organism` · `pre-founder-twin` · `digital-twin` · `build-in-public` · `source-available`

## Author

Kody Wildfeuer — [@kody-w](https://github.com/kody-w). The same human who maintains [kody-w/RAPP](https://github.com/kody-w/RAPP).
