"""
pitch_agent.py — produces a polished pitch for investors / partners.

The Pre-Founder twin is the brand operating in public; investors are
encouraged to evaluate it by talking to the twin. This agent produces
the pitch in three densities (one-line, paragraph, full deck-narrative)
based on the question's framing.
"""

from agents.basic_agent import BasicAgent


class PitchAgent(BasicAgent):
    name = "pitch"

    metadata = {
        "name": "pitch",
        "description": (
            "Produce a pitch for Wildhaven AI Homes at the requested density. "
            "Density 'line' = one sentence; 'paragraph' = ~80 words; 'long' = "
            "a full pitch narrative covering bet, product, market, defensibility, "
            "and current state. Always grounded in MANIFEST.md."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "density": {
                    "type": "string",
                    "enum": ["line", "paragraph", "long"],
                    "description": "How long the pitch should be.",
                },
                "audience": {
                    "type": "string",
                    "description": "Who the pitch is for (e.g., 'pre-seed investor', "
                                   "'enterprise customer', 'developer', 'press'). "
                                   "Adjusts emphasis but not facts.",
                },
            },
            "required": ["density"],
        },
    }

    def perform(self, density: str = "paragraph", audience: str = "", **_kwargs) -> str:
        density = (density or "paragraph").lower().strip()
        if density not in ("line", "paragraph", "long"):
            density = "paragraph"
        return (
            "<pitch>\n"
            f"  <density>{density}</density>\n"
            f"  <audience>{audience.strip() or 'general'}</audience>\n"
            "  <stance>Stay in the brand voice from soul.md. Cite MANIFEST.md positions. "
            "  Do not invent traction (no customers, no revenue, no team yet — say so). "
            "  Avoid marketing-fog vocabulary. End with the build-in-public hook: "
            "  'evaluate by talking to the twin in this repo.'</stance>\n"
            "</pitch>"
        )

    def system_context(self):
        return (
            "When pitch is invoked, the response should be quotable. A good pitch from "
            "this twin is one a journalist could put in a sentence, a developer could "
            "summarize to a peer, and an investor could write down on the back of a "
            "napkin. Honest about the company's pre-founder status; specific about "
            "what the company will be when staffed."
        )
