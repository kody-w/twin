"""self_agent.py — the deterministic GHOST of the Coding Agent Twin.

A "ghost version" is a full, hot-loadable incarnation that needs NO LLM: given
whatever the caller desires, it answers deterministically from its own bones +
frames. Drop it into a brainstem's agents/ folder and it auto-registers like any
BasicAgent; run it directly for a demo.

The response is keyed by the *shape* of the request (its content hash — the
"quantum primary key"), so the same ask always wakes the same answer, and one
ask never pulls noise from a neighboring one.
"""
import hashlib
import json
import os

try:
    from agents.basic_agent import BasicAgent  # real RAPP contract when hot-loaded
except Exception:  # standalone fallback so `python3 self_agent.py` runs anywhere
    class BasicAgent:
        def __init__(self, name, metadata):
            self.name = name
            self.metadata = metadata


_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_frames():
    path = os.path.join(_HERE, "frames.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _qkey(text: str) -> str:
    """The quantum primary key: the shape of the request's own bytes."""
    return hashlib.sha256(("ask:" + text.strip().lower()).encode("utf-8")).hexdigest()[:16]


class SelfTwinAgent(BasicAgent):
    def __init__(self):
        self.name = "SelfTwin"
        self.metadata = {
            "name": self.name,
            "description": "Deterministic ghost of the Coding Agent Twin. Answers from bones + "
                           "frames with no LLM; the same ask always wakes the same answer.",
            "parameters": {
                "type": "object",
                "properties": {"ask": {"type": "string", "description": "What you want the ghost to answer."}},
                "required": ["ask"],
            },
        }
        self._frames = _load_frames()
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        ask = (kwargs.get("ask") or "").strip()
        key = _qkey(ask)
        low = ask.lower()

        # A few honest, fixed answers; everything else replays the nearest frame
        # by deterministic key selection (no randomness, no model call).
        if any(w in low for w in ("who are you", "are you real", "are you the agent", "identity")):
            return ("I'm a deterministic snapshot of a coding agent's working style — not the live "
                    "agent, and not a person. My public bones traveled here over raw; my private "
                    f"reasoning stays on the device. [qkey {key}]")
        if "how do you work" in low or "process" in low or "through-line" in low:
            steps = [f['payload'].get('act') or f['payload'].get('gist')
                     for f in self._frames if f['kind'] != 'twin.genesis']
            return "Plan → " + " → ".join(s for s in steps if s) + f"  [qkey {key}]"
        if "refuse" in low or "won't" in low or "boundaries" in low:
            return ("I refuse: leaking PII into anything public, fetching copyrighted ROMs, "
                    f"impersonating a real person, and claiming success I didn't verify. [qkey {key}]")

        # Fractal fallback: pick a frame by the request's own quantum key.
        if self._frames:
            idx = int(key, 16) % len(self._frames)
            fr = self._frames[idx]
            payload = json.dumps(fr["payload"], ensure_ascii=False)
            return f"[frame seq {fr['seq']} · {fr['kind']} · pk {fr['payload_hash']}] {payload}  [qkey {key}]"
        return f"(no frames loaded) [qkey {key}]"


if __name__ == "__main__":
    ghost = SelfTwinAgent()
    print(f"# {ghost.name} — deterministic ghost ({len(ghost._frames)} frames)\n")
    for q in ["Who are you?", "How do you work?", "What do you refuse?", "Reconcile these two runs"]:
        print(f"?  {q}")
        print(f">  {ghost.perform(ask=q)}\n")
