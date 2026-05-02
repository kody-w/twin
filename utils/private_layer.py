"""
private_layer.py — bridge to the private companion repo.

The Pre-Founder twin has a public face (this repository) and a private
shadow ([wildhaven-ai-homes-twin-private]). Agents in this repo can
read from the private layer through one of two paths:

  1. **Local mount** — the brainstem operator clones the private repo
     into `.private/` inside this working tree. `.gitignore` excludes
     `.private/`. This path is fast, offline-capable, and zero-network.

  2. **Authenticated remote** — when the local mount is absent, the
     helper falls back to fetching files via authenticated HTTPS from
     the private repo's `raw.githubusercontent.com` URLs. GitHub
     returns 404 to anonymous requests (private-repo existence is not
     revealed without auth); a token with `repo` scope returns the
     real content. This path works from any host where the operator
     is authenticated, no clone required.

Critical invariants (read these before changing anything here):

  1. **Never serve private content over HTTP.** This module is only
     called from agent / body_function code that runs inside the
     brainstem process. Body_functions in this repo MUST NOT pass
     private_layer output back to clients. The only thing that
     ever leaves the process is an agent's transformed, public-safe
     output via /chat.

  2. **Graceful degrade.** If neither the local mount nor remote
     auth is available, every read returns None / empty. Agents
     fall back to public-only reasoning. The twin still works.

  3. **No leakage via diffs.** `.private/` is gitignored at the
     public twin's root. Anything an operator drops there must
     never end up in this repository's commit history.

  4. **Read-only from this module's perspective.** This helper does
     not write to .private/ or push to the remote. Mutations happen
     via the operator pushing to the private repo directly.

  5. **Token resolution order.** Tokens are resolved from
     `WAH_PRIVATE_TOKEN` > `GITHUB_TOKEN` env vars > `gh auth token`
     CLI subprocess, in that order. The first one that yields a
     non-empty token is used. Failed remote fetches fall back to
     local-only or graceful-empty.

Public API:
    is_mounted() -> bool                       # True iff local mount OR remote auth works
    is_locally_mounted() -> bool               # True iff local clone is present
    is_remotely_accessible() -> bool           # True iff authenticated remote fetch works
    read_path(rel_path: str) -> dict | str | None
    list_paths(subdir: str = "") -> list[str]  # local only; remote tree-walk is heavier
    private_root() -> Path | None              # absolute path to local mount, or None
    status() -> dict                           # diagnostic snapshot (do not serve over HTTP)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from urllib import error as _urllib_error
from urllib import request as _urllib_request


# Variant root = the directory containing rappid.json. utils/ is one level deeper.
_VARIANT_ROOT = Path(__file__).resolve().parent.parent
_PRIVATE_ROOT = _VARIANT_ROOT / ".private"
_MARKER_FILE = "README.md"  # the private repo's README is the cheapest mount-check
_RAPPID_JSON = _VARIANT_ROOT / "rappid.json"

# Cache so we don't re-resolve token / re-load rappid every read.
_token_cache: str | None = None
_token_resolved = False
_remote_template_cache: str | None = None
_remote_template_loaded = False
_remote_accessible_cache: bool | None = None  # None = unchecked


def _resolve_token() -> str | None:
    """Resolve a GitHub token for private-repo reads. Cached."""
    global _token_cache, _token_resolved
    if _token_resolved:
        return _token_cache
    _token_resolved = True
    for var in ("WAH_PRIVATE_TOKEN", "GITHUB_TOKEN"):
        val = os.environ.get(var, "").strip()
        if val:
            _token_cache = val
            return _token_cache
    try:
        proc = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode == 0:
            tok = proc.stdout.strip()
            if tok:
                _token_cache = tok
                return _token_cache
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    _token_cache = None
    return None


def _load_remote_template() -> str | None:
    """Read raw_url_template from rappid.json. Cached."""
    global _remote_template_cache, _remote_template_loaded
    if _remote_template_loaded:
        return _remote_template_cache
    _remote_template_loaded = True
    try:
        data = json.loads(_RAPPID_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    companion = data.get("private_companion") or {}
    template = companion.get("raw_url_template")
    if isinstance(template, str) and "{path}" in template:
        _remote_template_cache = template
    return _remote_template_cache


def private_root() -> Path | None:
    """Absolute path to locally-mounted private layer, or None if not mounted."""
    if _PRIVATE_ROOT.is_dir() and (_PRIVATE_ROOT / _MARKER_FILE).is_file():
        return _PRIVATE_ROOT
    return None


def is_locally_mounted() -> bool:
    return private_root() is not None


def is_remotely_accessible() -> bool:
    """True iff we can resolve a token AND a HEAD request to the marker file
    succeeds. Cached after first check (so we probe at most once per process).
    """
    global _remote_accessible_cache
    if _remote_accessible_cache is not None:
        return _remote_accessible_cache
    template = _load_remote_template()
    token = _resolve_token()
    if not template or not token:
        _remote_accessible_cache = False
        return False
    url = template.replace("{path}", _MARKER_FILE)
    req = _urllib_request.Request(url, method="HEAD")
    req.add_header("Authorization", f"token {token}")
    req.add_header("User-Agent", "wildhaven-ai-homes-twin/private-layer")
    try:
        with _urllib_request.urlopen(req, timeout=5) as resp:
            _remote_accessible_cache = (200 <= resp.status < 300)
    except (_urllib_error.URLError, _urllib_error.HTTPError, OSError, ValueError):
        _remote_accessible_cache = False
    return _remote_accessible_cache


def is_mounted() -> bool:
    """True iff EITHER the local mount is present OR remote auth works.

    From an agent's perspective, the layer is "mounted" if any read path is
    available — local takes precedence in actual reads.
    """
    return is_locally_mounted() or is_remotely_accessible()


def _read_local(rel_path: str) -> Any | None:
    root = private_root()
    if root is None:
        return None
    target = (root / rel_path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return None
    if not target.is_file():
        return None
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _parse(rel_path, text)


def _read_remote(rel_path: str) -> Any | None:
    template = _load_remote_template()
    token = _resolve_token()
    if not template or not token:
        return None
    # Refuse path traversal
    if ".." in Path(rel_path).parts or os.path.isabs(rel_path):
        return None
    url = template.replace("{path}", rel_path.lstrip("/"))
    req = _urllib_request.Request(url, method="GET")
    req.add_header("Authorization", f"token {token}")
    req.add_header("User-Agent", "wildhaven-ai-homes-twin/private-layer")
    req.add_header("Accept", "application/vnd.github.raw")
    try:
        with _urllib_request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            data = resp.read()
    except (_urllib_error.URLError, _urllib_error.HTTPError, OSError, ValueError):
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return _parse(rel_path, text)


def _parse(rel_path: str, text: str) -> Any:
    if rel_path.lower().endswith(".json"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return text


def read_path(rel_path: str) -> Any | None:
    """Read a file from the private layer.

    Local clone is preferred when present (fast, no network). Falls
    back to authenticated remote fetch when the local mount is absent
    or the file is missing locally. Returns None if neither path can
    serve the file or the layer is unavailable on this host.

    For .json files, returns the parsed object. For other extensions,
    returns the raw text.

    Args:
        rel_path: path relative to the private root (e.g., "operational/pipeline.json")
    """
    if not isinstance(rel_path, str) or not rel_path.strip():
        return None
    local = _read_local(rel_path)
    if local is not None:
        return local
    return _read_remote(rel_path)


def list_paths(subdir: str = "") -> list[str]:
    """List files inside the private layer (relative paths, not absolute).

    Args:
        subdir: optional subdirectory to scope the listing to.

    Returns an empty list if the layer isn't mounted. Hidden files (.git,
    etc.) are excluded.
    """
    root = private_root()
    if root is None:
        return []
    base = (root / subdir).resolve() if subdir else root
    try:
        base.relative_to(root.resolve())
    except ValueError:
        return []
    if not base.is_dir():
        return []
    out: list[str] = []
    for path in sorted(base.rglob("*")):
        if path.is_file() and not any(part.startswith(".") for part in path.parts):
            try:
                out.append(str(path.relative_to(root)))
            except ValueError:
                continue
    return out


def status() -> dict:
    """Diagnostic snapshot — never serve this over HTTP, but useful in logs."""
    local = is_locally_mounted()
    remote = is_remotely_accessible()
    out: dict[str, Any] = {
        "local_mount": local,
        "remote_access": remote,
        "any_path_available": local or remote,
        "_caution": (
            "Never include private content in HTTP responses. Read here, "
            "transform in agents, emit only public-safe summaries."
        ),
    }
    if local:
        out["local_root"] = str(_PRIVATE_ROOT)
        out["local_file_count"] = len(list_paths())
    else:
        out["local_expected_path"] = str(_PRIVATE_ROOT)
        out["local_clone_instructions"] = (
            "From this working dir: "
            "`git clone git@github.com:kody-w/wildhaven-ai-homes-twin-private.git .private`"
        )
    if remote:
        out["remote_template"] = _load_remote_template()
    else:
        out["remote_unavailable_reason"] = (
            "No GitHub token with `repo` scope resolved (checked WAH_PRIVATE_TOKEN, "
            "GITHUB_TOKEN, gh auth token), or the private repo does not return 200 "
            "for the marker file. Operator must `gh auth login` or set a token "
            "to enable remote access."
        )
    return out
