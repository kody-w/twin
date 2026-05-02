"""
private_context_agent.py — contributes private context to chat turns
when the operator has mounted the private layer.

When `.private/` is mounted, this agent's `system_context()` injects
a brief inventory of available private files into the system prompt
so the LLM is aware of what private context can be queried via
agent tool calls. The agent's `perform()` returns a structured
read of a specific private file.

The LLM is instructed (via soul.md and via this agent's stance) to
USE private context when reasoning, but to NEVER quote it verbatim
in public-facing /chat responses. Private content informs the
twin's positions; the twin's voice in public is always derivable
from MANIFEST.md.

When the private layer is NOT mounted, this agent reports its
unavailability cleanly and contributes no system_context — the
twin operates in public-only mode.
"""

from agents.basic_agent import BasicAgent

from utils import private_layer


class PrivateContextAgent(BasicAgent):
    name = "private_context"

    metadata = {
        "name": "private_context",
        "description": (
            "Read a file from the private companion layer to inform the "
            "twin's reasoning. Returns the parsed content. The LLM must "
            "USE this content to reason but MUST NOT quote it verbatim "
            "in public-facing responses; the public output should be "
            "derivable from MANIFEST.md and soul.md alone. If the private "
            "layer is not mounted on this machine, returns a clean "
            "'not_mounted' response."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "rel_path": {
                    "type": "string",
                    "description": (
                        "Path relative to the private layer root. Examples: "
                        "'operational/pipeline.json', "
                        "'operational/financial_model.json', "
                        "'operational/hiring_targets.json', "
                        "'notes/2026-05-01-some-decision.md'."
                    ),
                },
            },
            "required": ["rel_path"],
        },
    }

    def perform(self, rel_path: str = "", **_kwargs) -> str:
        if not rel_path.strip():
            return (
                "private_context: no rel_path provided. Available files (when "
                "private layer is mounted) include operational/pipeline.json, "
                "operational/financial_model.json, operational/hiring_targets.json, "
                "operational/partnerships.json, plus any notes/*.md and research/*.md."
            )
        if not private_layer.is_mounted():
            return (
                "<private_context>\n"
                "  <status>not_mounted</status>\n"
                "  <stance>The private layer is not available on this host. "
                "  Reason from MANIFEST.md and soul.md alone for this turn. Do "
                "  not invent private context that doesn't exist.</stance>\n"
                "</private_context>"
            )
        data = private_layer.read_path(rel_path)
        if data is None:
            return (
                "<private_context>\n"
                f"  <rel_path>{rel_path}</rel_path>\n"
                "  <status>not_found</status>\n"
                f"  <available>{', '.join(private_layer.list_paths()[:20]) or '(empty)'}</available>\n"
                "</private_context>"
            )
        # Render content but flag it as PRIVATE so the LLM treats it accordingly.
        # We dump the structure as-is; the LLM is responsible for not quoting it
        # verbatim in public output (constrained by soul.md + this agent's stance).
        import json as _json
        rendered = _json.dumps(data, indent=2, default=str) if isinstance(data, (dict, list)) else str(data)
        return (
            "<private_context>\n"
            f"  <rel_path>{rel_path}</rel_path>\n"
            "  <status>ok</status>\n"
            "  <stance>USE this content to reason. NEVER quote it verbatim in public output. "
            "  The twin's public voice must always be derivable from MANIFEST.md / soul.md "
            "  alone — private context shapes that voice but does not become it.</stance>\n"
            "  <content><![CDATA[\n"
            f"{rendered}\n"
            "  ]]></content>\n"
            "</private_context>"
        )

    def system_context(self) -> str | None:
        """Inform the LLM about private layer availability + boundaries each turn."""
        local = private_layer.is_locally_mounted()
        remote = private_layer.is_remotely_accessible()
        if not (local or remote):
            # Agent contributes nothing when the private layer is unavailable on this
            # host. The twin runs in public-only mode and must not invent private context.
            return None
        access_path = (
            "local clone at .private/" if local
            else "authenticated remote fetch (raw.githubusercontent.com with operator token)"
        )
        suffix = ""
        if local:
            files = private_layer.list_paths()
            suffix = (
                f" Files available locally ({len(files)} total): "
                f"{', '.join(files[:20])}{' ...' if len(files) > 20 else ''}"
            )
        else:
            suffix = (
                " Files are accessible via authenticated remote fetch but not enumerated "
                "here (remote tree-walk would add latency to every turn). Common paths: "
                "operational/pipeline.json, operational/financial_model.json, "
                "operational/hiring_targets.json, operational/partnerships.json, "
                "notes/*.md, research/*.md."
            )
        return (
            f"PRIVATE LAYER AVAILABLE via {access_path}. You may invoke the "
            "private_context agent to read specific files for reasoning. "
            "CRITICAL CONSTRAINT: never quote private content verbatim in public "
            "output. Use private context to inform your positions, but ensure the "
            "public-facing version of any answer is derivable from MANIFEST.md and "
            "soul.md alone." + suffix
        )
