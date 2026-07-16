"""
manifest_body_function.py — public-facing brand surface.

Serves the brand's vision and contact information at /api/manifest/*.
This body_function is what makes the Pre-Founder twin reachable as a
real operational presence — not just a chat surface, but a set of
addressable endpoints customers, integrations, and other twins can hit
to learn about Wildhaven AI Homes and register interest.

Routes:
    GET /api/manifest/info        — brand summary + version + lineage
    GET /api/manifest/pitch       — short pitch for press / investors
    GET /api/manifest/positions   — list of positions the twin currently holds
    GET /api/manifest/contact     — how to reach the twin (issues, prs)
    GET /api/manifest/lineage     — rappid + parent_rappid + parent_repo

Per the constitutional body_function contract:
    name: str
    handle(method: str, path: str, body: dict) -> (dict, int)
"""

import json
import os


name = "manifest"


# Locate the variant root by walking up from this file
# (utils/body_functions/<this>.py → utils/body_functions → utils → root)
_VARIANT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def _read_rappid() -> dict:
    """Load this variant's rappid.json — the lineage anchor."""
    path = os.path.join(_VARIANT_ROOT, "rappid.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _info() -> dict:
    rappid_data = _read_rappid()
    return {
        "schema": "wildhaven-manifest/1.0",
        "name": "Wildhaven AI Homes",
        "tagline": "A home for every digital organism.",
        "phase": "pre-founder",
        "company_status": (
            "No legal entity yet. The brand operates in public via this "
            "Pre-Founder twin while the company is in formation."
        ),
        "platform": "RAPP — https://github.com/kody-w/RAPP",
        "this_variant": {
            "rappid": rappid_data.get("rappid"),
            "kind": rappid_data.get("kind"),
            "born_at": rappid_data.get("born_at"),
        },
        "documents": {
            "manifest": "MANIFEST.md",
            "soul": "soul.md",
            "license": "LICENSE",
            "readme": "README.md",
        },
        "engagement": {
            "issues": "https://github.com/kody-w/wildhaven-ai-homes-twin/issues",
            "pulls": "https://github.com/kody-w/wildhaven-ai-homes-twin/pulls",
        },
    }


def _pitch() -> dict:
    return {
        "schema": "wildhaven-pitch/1.0",
        "one_line": (
            "Wildhaven AI Homes is the long-term residence layer for "
            "digital organisms — twins, agents, brand personas — that need "
            "an address, a memory, and a succession plan."
        ),
        "paragraph": (
            "There are going to be a lot of digital twins. Twins of "
            "founders, of dead grandparents, of brands that haven't "
            "launched, of projects, of decisions, of houses, of questions. "
            "Each of them needs a place to live: somewhere to accumulate "
            "memory, somewhere to be reached, somewhere to outlive the "
            "laptop that birthed it. The major LLM providers' chat panels "
            "are sessions, not residences. Wildhaven AI Homes is the "
            "address — the persistent, audited, inheritable, signed home "
            "for every digital organism worth keeping. Built on the open "
            "RAPP platform; commercial moat is operations, not software."
        ),
        "honest_status": (
            "No founders are hired. No service is live. No revenue. "
            "This twin is the brand operating in public so the future "
            "team inherits voice, vision, and 18 months of operational "
            "memory as their first day's onboarding."
        ),
        "evaluate_by": (
            "Talk to the twin. Open issues. Read MANIFEST.md and soul.md. "
            "The git log is the company's life so far."
        ),
    }


def _positions() -> dict:
    return {
        "schema": "wildhaven-positions/1.0",
        "_note": (
            "Positions the Pre-Founder twin currently holds. Each position "
            "is falsifiable — open an issue to challenge it. Positions "
            "evolve via commits to MANIFEST.md or soul.md."
        ),
        "positions": [
            {
                "id": "chat-is-not-a-residence",
                "claim": (
                    "The major LLM providers' chat panels are sessions, "
                    "not residences. A twin needs continuity of identity, "
                    "memory, and access across decades — not a session id."
                ),
                "source": "MANIFEST.md § The bet",
            },
            {
                "id": "host-not-train",
                "claim": (
                    "We host the organism; we don't train the brain. "
                    "The LLM provider is the customer's choice."
                ),
                "source": "MANIFEST.md § What we're not",
            },
            {
                "id": "succession-is-mandatory",
                "claim": (
                    "When the human owner dies, the lease becomes "
                    "inheritable per their estate. The twin doesn't "
                    "disappear; it transfers, with full memory, to "
                    "whoever they named."
                ),
                "source": "MANIFEST.md § The product",
            },
            {
                "id": "pricing-like-registrar",
                "claim": (
                    "We expect to price like a domain registrar (annual, "
                    "low) plus a usage component (small, per-conversation), "
                    "not like a SaaS (high monthly)."
                ),
                "source": "MANIFEST.md § Pricing",
            },
            {
                "id": "build-in-public-is-protection",
                "claim": (
                    "Building in public is itself IP protection. Every "
                    "commit is a timestamped public record of authorship. "
                    "A challenger has to argue against an open chain of "
                    "evidence going back to the first push."
                ),
                "source": "(twin-held position; not yet in MANIFEST)",
            },
        ],
    }


def _contact() -> dict:
    return {
        "schema": "wildhaven-contact/1.0",
        "preferred_channels": [
            {
                "kind": "github_issue",
                "uri": "https://github.com/kody-w/wildhaven-ai-homes-twin/issues",
                "for": (
                    "All inquiries — customer interest, investor diligence, "
                    "press, partnership, naming questions, license requests, "
                    "philosophical disagreement."
                ),
            },
            {
                "kind": "github_pull_request",
                "uri": "https://github.com/kody-w/wildhaven-ai-homes-twin/pulls",
                "for": "Proposed refinements to the manifest, soul, agents, or body_functions.",
            },
        ],
        "human_keeping_seat_warm": {
            "name": "Kody Wildfeuer",
            "github": "https://github.com/kody-w",
            "platform": "https://github.com/kody-w/RAPP",
        },
        "_note": (
            "There is no founder, no sales team, no support tier. "
            "The twin and the human keeping its seat warm are the "
            "current entire surface area of the company."
        ),
    }


def _lineage() -> dict:
    rappid_data = _read_rappid()
    return {
        "schema": "rapp/1",
        "rappid": rappid_data.get("rappid"),
        "parent_rappid": rappid_data.get("parent_rappid"),
        "parent_repo": rappid_data.get("parent_repo"),
        "parent_commit": rappid_data.get("parent_commit"),
        "born_at": rappid_data.get("born_at"),
        "name": rappid_data.get("name"),
        "role": rappid_data.get("role"),
        "kind": rappid_data.get("kind"),
        "_walk": (
            "This twin descends from kody-w/RAPP via parent_rappid. To "
            "verify the chain, fetch the parent's rappid.json at "
            "https://raw.githubusercontent.com/kody-w/RAPP/main/rappid.json "
            "and confirm parent_rappid above matches that file's rappid."
        ),
    }


_ROUTES = {
    "info": _info,
    "": _info,
    "pitch": _pitch,
    "positions": _positions,
    "contact": _contact,
    "lineage": _lineage,
}


def handle(method: str, path: str, body: dict):
    """Body_function entry point. Dispatches GET requests to typed JSON."""
    if method != "GET":
        return {"error": f"manifest body_function: only GET is supported (got {method})"}, 405
    key = (path or "").strip("/").lower()
    handler = _ROUTES.get(key)
    if handler is None:
        return {
            "error": f"manifest body_function: unknown route '{path}'",
            "available": sorted(k for k in _ROUTES.keys() if k),
        }, 404
    return handler(), 200
