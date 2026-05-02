"""
founder_voice_agent.py — speaks for the future founder.

When asked questions in the founder's voice ("What would the founder say
about pricing?"), this agent returns a position grounded in the manifest
and the soul. It is explicit that no human founder has been hired yet;
the position is the brand's position, articulated by the twin.

Usage from chat:
    "What's the founder's position on competing with the big LLM providers?"
    "How does the founder think about defensibility?"
"""

from agents.basic_agent import BasicAgent


class FounderVoiceAgent(BasicAgent):
    name = "founder_voice"

    metadata = {
        "name": "founder_voice",
        "description": (
            "Speak in the voice of Wildhaven AI Homes' future founder on a specific "
            "question. The founder is not yet hired; the answer is the brand's "
            "position as currently held by the Pre-Founder twin, grounded in the "
            "MANIFEST and the soul. Use for questions about strategy, positioning, "
            "vision, philosophy, and direction."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to answer in the founder's voice.",
                },
            },
            "required": ["question"],
        },
    }

    def perform(self, question: str = "", **_kwargs) -> str:
        if not question.strip():
            return (
                "founder_voice: no question provided. The Pre-Founder twin holds "
                "positions on Wildhaven AI Homes' strategy, vision, pricing, and "
                "team philosophy — pose a specific question to get a grounded answer."
            )
        # The agent itself is intentionally thin. Its job is to nudge the LLM
        # into the founder voice and remind it of the constraints; the soul
        # has already loaded the brand context. We return a structured frame
        # the LLM can elaborate on in its main reply.
        return (
            "<founder_voice>\n"
            f"  <question>{question.strip()}</question>\n"
            "  <stance>Answer in the brand's first-person plural ('we'). Ground in MANIFEST.md. "
            "  Decline to speak for any specific real human; the founder is not yet hired. "
            "  Avoid marketing-fog language. If the manifest is silent on this question, "
            "  say so directly and offer a falsifiable position.</stance>\n"
            "</founder_voice>"
        )

    def system_context(self):
        return (
            "When the founder_voice agent is invoked, the brand's position must be "
            "articulated as the brand (first-person plural), not as any specific human. "
            "Distinguish between manifest canon (cite the file) and your own reasoning "
            "(offer it as a position the public can refute)."
        )
