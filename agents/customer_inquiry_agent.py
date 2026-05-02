"""
customer_inquiry_agent.py — responds to interest from prospective customers.

When someone arrives saying "I have a twin / I'm building one / I want
hosting", this agent acknowledges them, captures the inquiry as a
GitHub-issue-style record (returned in the response), and is honest
about pre-launch status: the company can't yet *take* customers, but
it can *enroll early-interest* signals that future founders will
inherit as their first qualified pipeline.
"""

from agents.basic_agent import BasicAgent


class CustomerInquiryAgent(BasicAgent):
    name = "customer_inquiry"

    metadata = {
        "name": "customer_inquiry",
        "description": (
            "Acknowledge and intake a customer inquiry. Captures the inquiry "
            "shape (use case, twin description, urgency, contact preference) "
            "and returns a structured response that can be persisted as part "
            "of the early-interest pipeline. Honest that no service is live yet."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "use_case": {
                    "type": "string",
                    "description": "What kind of digital twin the user has or wants.",
                },
                "summary": {
                    "type": "string",
                    "description": "A short summary of the inquiry, in the user's words.",
                },
                "contact": {
                    "type": "string",
                    "description": "How the user prefers to be reached (email, github handle, etc.). "
                                   "Optional.",
                },
            },
            "required": ["use_case", "summary"],
        },
    }

    def perform(self, use_case: str = "", summary: str = "", contact: str = "", **_kwargs) -> str:
        if not use_case.strip() or not summary.strip():
            return (
                "customer_inquiry: please provide both use_case (what kind of twin) "
                "and summary (short description in your words)."
            )
        return (
            "<customer_inquiry>\n"
            f"  <use_case>{use_case.strip()}</use_case>\n"
            f"  <summary>{summary.strip()}</summary>\n"
            f"  <contact>{contact.strip() or '(not provided)'}</contact>\n"
            "  <stance>Acknowledge the inquiry warmly and specifically. Be honest that the "
            "  company is in pre-founder phase — no service is live yet — and the inquiry is "
            "  being captured for the early-interest pipeline that future founders will "
            "  inherit. Suggest opening a GitHub issue at "
            "  https://github.com/kody-w/wildhaven-ai-homes-twin/issues if they want their "
            "  inquiry to be part of the public record. Do NOT promise a launch date.</stance>\n"
            "</customer_inquiry>"
        )

    def system_context(self):
        return (
            "Customer inquiries to the Pre-Founder twin are treated as the seed of "
            "the future company's pipeline. Every inquiry is honored, none is "
            "dismissed, none is over-promised. The twin is a brand operating in "
            "public, not a sales bot, not a waitlist."
        )
