"""
operations_agent.py — handles operational queries about the company.

For "what does Wildhaven AI Homes actually do?", "what's the roadmap?",
"who hosts it?", "where is data stored?" — anything that reads as a
factual question about the operation. Grounds answers in the manifest
and is explicit about what is committed (in the repo) vs. what is a
position the twin currently holds.
"""

from agents.basic_agent import BasicAgent


class OperationsAgent(BasicAgent):
    name = "operations"

    metadata = {
        "name": "operations",
        "description": (
            "Answer operational and factual questions about Wildhaven AI Homes — "
            "what the product is, what the roadmap looks like, where data lives, "
            "who hosts it, what the company will offer. Distinguishes manifest "
            "canon from twin-held positions and says so."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The operational question to answer.",
                },
            },
            "required": ["question"],
        },
    }

    def perform(self, question: str = "", **_kwargs) -> str:
        if not question.strip():
            return (
                "operations: pose a specific question. Examples: 'How is data "
                "stored?', 'What's the timeline to first customer?', 'What "
                "models do you use?', 'How much will hosting cost?'"
            )
        return (
            "<operations>\n"
            f"  <question>{question.strip()}</question>\n"
            "  <stance>Cite MANIFEST.md when the answer is canonical (and reference the "
            "  section). When the manifest is silent, frame the response as the twin's "
            "  current position, falsifiable by future commits. Never invent customers, "
            "  partnerships, revenue, team members, or timelines that are not in "
            "  the repo. If a question requires a commitment (a contract, a guarantee), "
            "  say plainly that no human can yet make that commitment.</stance>\n"
            "</operations>"
        )

    def system_context(self):
        return (
            "When the operations agent runs, ground every claim in committed repo "
            "content. Distinguish 'this is what we will do' (intention) from 'this is "
            "what we are doing today' (fact). The Pre-Founder twin has no customers, "
            "no team, no revenue — saying so is the right answer when asked."
        )
