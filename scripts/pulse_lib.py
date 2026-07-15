#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pulse_lib — shared, STDLIB-ONLY core for the rapp-twin-pulse/1.0 DOG.

This module is the single source of truth for the two things that MUST be
byte-reproducible across every runtime (CPython here, Pyodide/JS on the
vbrainstem carrier):

  1. RFC 8785 JSON Canonicalization Scheme (JCS)  -> the bytes we SHA-256.
  2. SHA-256 over JCS(payload)                    -> the frame identity.

It also carries a pure-Python Ed25519 (RFC 8032) implementation so the OPTIONAL
detached signature path needs no third-party dependency, and the frame / feed /
Atom builders that shape the static DOG broadcast surface.

Spec: 04-SPEC-rapp-twin-pulse.md  (rapp-frame/2.0, kind twin.pulse).

Bones rule (load-bearing): payloads MUST NOT contain bare floats. Integers or
strings only, so no runtime can reformat a number and silently fork the chain.
`canonicalize()` raises on a float rather than guess an ES number form.
"""

import hashlib
import json
import os
import re

# ---------------------------------------------------------------------------
# Constants (the wire contract). twin_id + kernel_version are fixed by the
# order and MUST NOT drift; kernel_version sits OUTSIDE payload so it never
# affects sha256 (spec 2.2).
# ---------------------------------------------------------------------------
SPEC = "rapp-frame/2.0"
FRAME_KIND = "twin.pulse"
FEED_KIND = "twin.pulse.feed"
TWIN_ID = "rappid:@kody-w/twin:5714cdf964b6a6936b44420aa8e8589b2ee9342e10810cdf12fc3c7be7667c30"
KERNEL_VERSION = "0.6.0"
N = 64  # feed window: newest N frames live in feed.json; frames/ keeps all.

BASE_RAW = "https://raw.githubusercontent.com/kody-w/twin/main"

# ===========================================================================
# 1. RFC 8785 (JCS) canonicalization  -- the canonical form is the contract.
# ===========================================================================
_STRING_ESCAPES = {
    '"': '\\"',
    '\\': '\\\\',
    '\b': '\\b',
    '\t': '\\t',
    '\n': '\\n',
    '\f': '\\f',
    '\r': '\\r',
}


def _ser_string(s):
    # RFC 8785 3.2.2.2: two-char escapes for the named control chars, \u00xx
    # (lowercase) for the remaining C0 controls, everything else verbatim (so
    # non-ASCII is emitted as raw UTF-8, NOT \u-escaped). '/' is NOT escaped.
    out = ['"']
    for ch in s:
        esc = _STRING_ESCAPES.get(ch)
        if esc is not None:
            out.append(esc)
        elif ch < '\x20':
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def _ser(o):
    # Order matters: bool is a subclass of int in Python, so trap True/False
    # before the int branch.
    if o is None:
        return 'null'
    if o is True:
        return 'true'
    if o is False:
        return 'false'
    if isinstance(o, str):
        return _ser_string(o)
    if isinstance(o, bool):  # unreachable (handled above) — defensive
        return 'true' if o else 'false'
    if isinstance(o, int):
        return str(o)
    if isinstance(o, float):
        raise ValueError(
            "JCS: bare float not allowed in a bones payload (%r) — use an "
            "integer or a string so no runtime can reformat it." % o)
    if isinstance(o, dict):
        # Keys sorted by UTF-16 code units (RFC 8785 3.2.3). Comparing the
        # UTF-16-BE byte encoding reproduces that ordering exactly, including
        # for supplementary characters (surrogate pairs).
        parts = []
        for k in sorted(o.keys(), key=lambda s: s.encode('utf-16-be')):
            if not isinstance(k, str):
                raise TypeError("JCS: object keys must be strings")
            parts.append(_ser_string(k) + ':' + _ser(o[k]))
        return '{' + ','.join(parts) + '}'
    if isinstance(o, (list, tuple)):
        return '[' + ','.join(_ser(v) for v in o) + ']'
    raise TypeError("JCS: unsupported type %s" % type(o).__name__)


def canonicalize(obj):
    """Return the RFC 8785 canonical UTF-8 bytes of ``obj`` (no BOM, no
    trailing newline)."""
    return _ser(obj).encode('utf-8')


def payload_sha256(payload):
    """Lowercase-hex SHA-256 over JCS(payload). This is the frame identity."""
    return hashlib.sha256(canonicalize(payload)).hexdigest()


# ===========================================================================
# 2. Ed25519 (RFC 8032) — pure stdlib. OPTIONAL authorship proof only;
#    identity is sha-based and never depends on a key (spec 8.3).
# ===========================================================================
_b = 256
_q = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493


def _H(m):
    return hashlib.sha512(m).digest()


def _inv(x):
    return pow(x, _q - 2, _q)


_d = (-121665 * _inv(121666)) % _q
_I = pow(2, (_q - 1) // 4, _q)


def _xrecover(y):
    xx = (y * y - 1) * _inv(_d * y * y + 1) % _q
    x = pow(xx, (_q + 3) // 8, _q)
    if (x * x - xx) % _q != 0:
        x = (x * _I) % _q
    if x % 2 != 0:
        x = _q - x
    return x


_By = (4 * _inv(5)) % _q
_Bx = _xrecover(_By)
_B = (_Bx % _q, _By % _q)


def _edwards_add(P, Q):
    x1, y1 = P
    x2, y2 = Q
    dd = _d * x1 * x2 * y1 * y2
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + dd) % _q
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - dd) % _q
    return (x3 % _q, y3 % _q)


def _scalarmult(P, e):
    # LSB-first double-and-add over the group; identity is (0, 1).
    Q = (0, 1)
    while e > 0:
        if e & 1:
            Q = _edwards_add(Q, P)
        P = _edwards_add(P, P)
        e >>= 1
    return Q


def _encodeint(y):
    return int(y).to_bytes(_b // 8, 'little')


def _encodepoint(P):
    x, y = P
    val = (y % _q) | ((x & 1) << (_b - 1))
    return val.to_bytes(_b // 8, 'little')


def _bit(h, i):
    return (h[i // 8] >> (i % 8)) & 1


def _clamp(h):
    a = bytearray(h[:32])
    a[0] &= 248
    a[31] &= 127
    a[31] |= 64
    return int.from_bytes(a, 'little')


def _Hint(m):
    return int.from_bytes(_H(m), 'little')


def _isoncurve(P):
    x, y = P
    return (-x * x + y * y - 1 - _d * x * x * y * y) % _q == 0


def _decodepoint(s):
    y = int.from_bytes(s, 'little') & ((1 << (_b - 1)) - 1)
    x = _xrecover(y)
    if (x & 1) != _bit(s, _b - 1):
        x = _q - x
    P = (x, y)
    if not _isoncurve(P):
        raise ValueError("Ed25519: decoded point is not on the curve")
    return P


def ed25519_publickey(seed):
    """32-byte public key from a 32-byte secret seed."""
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    h = _H(seed)
    a = _clamp(h)
    return _encodepoint(_scalarmult(_B, a))


def ed25519_sign(seed, msg):
    """64-byte detached signature over ``msg`` (bytes)."""
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    h = _H(seed)
    a = _clamp(h)
    pk = _encodepoint(_scalarmult(_B, a))
    r = _Hint(h[32:64] + msg)
    R = _scalarmult(_B, r)
    S = (r + _Hint(_encodepoint(R) + pk + msg) * a) % _L
    return _encodepoint(R) + _encodeint(S)


def ed25519_verify(pubkey, msg, sig):
    """True iff ``sig`` is a valid Ed25519 signature of ``msg`` under
    ``pubkey``. Never raises — a malformed input is simply invalid."""
    try:
        if len(sig) != 64 or len(pubkey) != 32:
            return False
        R = _decodepoint(sig[:32])
        A = _decodepoint(pubkey)
        S = int.from_bytes(sig[32:], 'little')
        if S >= _L:
            return False
        h = _Hint(sig[:32] + pubkey + msg)
        return _scalarmult(_B, S) == _edwards_add(R, _scalarmult(A, h))
    except Exception:
        return False


def gen_keypair():
    seed = os.urandom(32)
    return seed, ed25519_publickey(seed)


# ===========================================================================
# 3. Bones: the public projection. A bones/ directory is a map path -> value.
#    .json files parse to JSON values; any other file is carried as text.
# ===========================================================================
def load_bones(bones_dir):
    state = {}
    for root, _dirs, files in os.walk(bones_dir):
        for fn in sorted(files):
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, bones_dir).replace(os.sep, '/')
            with open(full, 'r', encoding='utf-8') as f:
                raw = f.read()
            state[rel] = json.loads(raw) if fn.endswith('.json') else raw
    return state


def _json_merge_patch(target, patch):
    # RFC 7386
    if not isinstance(patch, dict):
        return patch
    if not isinstance(target, dict):
        target = {}
    out = dict(target)
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = _json_merge_patch(out.get(k), v)
    return out


def replay(frames):
    """Materialize the bones state after applying frames in ascending seq
    order. Only set/delete/merge are needed by the signer's diff path;
    ``patch`` is intentionally not replayed here."""
    state = {}
    for fr in frames:
        for path, op in fr['payload']['bones'].items():
            kind = op['op']
            if kind == 'set':
                state[path] = op['value']
            elif kind == 'delete':
                state.pop(path, None)
            elif kind == 'merge':
                state[path] = _json_merge_patch(state.get(path), op['value'])
            else:
                raise ValueError(
                    "replay: unsupported op %r (signer emits set/delete)" % kind)
    return state


def diff_ops(prev_state, cur_state):
    """Compute a bones delta: set for new/changed paths, delete for removed."""
    ops = {}
    for path, val in cur_state.items():
        if path not in prev_state or prev_state[path] != val:
            ops[path] = {'op': 'set', 'value': val}
    for path in prev_state:
        if path not in cur_state:
            ops[path] = {'op': 'delete'}
    return ops


# ===========================================================================
# 4. Frame / feed / Atom builders.
# ===========================================================================
def build_frame(seq, ops, parent_sha, ts,
                twin_id=TWIN_ID, kernel_version=KERNEL_VERSION):
    payload = {'bones': ops}
    frame = {
        'spec': SPEC,
        'kind': FRAME_KIND,
        'seq': seq,
        'ts': ts,
        'twin_id': twin_id,
        'kernel_version': kernel_version,
        'payload': payload,
        'sha256': payload_sha256(payload),
        'parent_sha': parent_sha,
        'sig': None,
    }
    return frame


def attach_sig(frame, seed):
    sig = ed25519_sign(seed, frame['sha256'].encode('ascii'))
    frame['sig'] = {'alg': 'ed25519', 'sig': sig.hex()}
    return frame


def verify_frame_sig(frame, pubkey):
    """True if the frame's sig is absent (valid — sig is optional) or a valid
    Ed25519 signature over its sha256 under ``pubkey``."""
    sig = frame.get('sig')
    if sig is None:
        return True
    if not isinstance(sig, dict) or sig.get('alg') != 'ed25519':
        return False
    try:
        sig_bytes = bytes.fromhex(sig['sig'])
    except Exception:
        return False
    return ed25519_verify(pubkey, frame['sha256'].encode('ascii'), sig_bytes)


def build_feed(frames, n=N, twin_id=TWIN_ID):
    ordered = sorted(frames, key=lambda f: f['seq'])
    window = ordered[-n:]
    return {
        'spec': SPEC,
        'kind': FEED_KIND,
        'twin_id': twin_id,
        'head_sha': window[-1]['sha256'] if window else None,
        'count': len(window),
        'frames': window,
    }


def _xml_escape(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;'))


def build_feed_xml(feed, base_raw=BASE_RAW):
    frames = feed['frames']
    updated = frames[-1]['ts'] if frames else '1970-01-01T00:00:00Z'
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<feed xmlns="http://www.w3.org/2005/Atom">',
         '  <title>the pulse — @kody-w/twin</title>',
         '  <subtitle>rapp-twin-pulse/1.0 — a DOG: signed, SHA-chained twin '
         'bones. Trust the hash, not the host.</subtitle>',
         '  <id>https://kody-w.github.io/twin/feed.xml</id>',
         '  <updated>%s</updated>' % _xml_escape(updated),
         '  <link rel="self" type="application/atom+xml" '
         'href="https://kody-w.github.io/twin/feed.xml"/>',
         '  <link rel="alternate" type="application/json" href="%s/feed.json"/>'
         % base_raw,
         '  <generator uri="https://github.com/kody-w/twin" '
         'version="1.0">scripts/pulse_sign.py</generator>']
    for fr in frames:
        sha = fr['sha256']
        seq = fr['seq']
        signed = 'signed' if fr.get('sig') else 'unsigned'
        L.append('  <entry>')
        # done-when: <id> == the frame's sha256, exactly.
        L.append('    <id>%s</id>' % _xml_escape(sha))
        L.append('    <title>twin.pulse seq %d</title>' % seq)
        L.append('    <updated>%s</updated>' % _xml_escape(fr['ts']))
        L.append('    <category term="twin.pulse"/>')
        L.append('    <link rel="alternate" type="application/json" '
                 'href="%s/frames/%d.json"/>' % (base_raw, seq))
        parent = fr['parent_sha'] if fr['parent_sha'] else 'genesis (null)'
        L.append('    <summary type="text">twin.pulse frame seq %d (%s); '
                 'sha256=%s; parent_sha=%s</summary>'
                 % (seq, signed, sha, _xml_escape(parent)))
        L.append('  </entry>')
    L.append('</feed>')
    return '\n'.join(L) + '\n'


# ===========================================================================
# 5. Repo I/O.
# ===========================================================================
_FRAME_RE = re.compile(r'^(\d+)\.json$')


def frames_dir(repo):
    return os.path.join(repo, 'frames')


def load_all_frames(repo):
    """Every frames/<seq>.json (pure-integer name only), ascending seq. The
    legacy hologram-cartridge files (e.g. 0-<sha8>.json, HEAD) are ignored."""
    d = frames_dir(repo)
    out = []
    if os.path.isdir(d):
        for fn in os.listdir(d):
            m = _FRAME_RE.match(fn)
            if not m:
                continue
            with open(os.path.join(d, fn), 'r', encoding='utf-8') as f:
                out.append((int(m.group(1)), json.load(f)))
    out.sort(key=lambda t: t[0])
    return [fr for _seq, fr in out]


def _dump(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def write_frame(repo, frame):
    d = frames_dir(repo)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, '%d.json' % frame['seq'])
    _dump(path, frame)
    return path


def write_feed(repo, feed):
    _dump(os.path.join(repo, 'feed.json'), feed)


def write_feed_xml(repo, feed):
    with open(os.path.join(repo, 'feed.xml'), 'w', encoding='utf-8') as f:
        f.write(build_feed_xml(feed))


def load_pubkey_hex(path):
    with open(path, 'r', encoding='utf-8') as f:
        return bytes.fromhex(f.read().strip())


def load_seed_hex(path):
    with open(path, 'r', encoding='utf-8') as f:
        return bytes.fromhex(f.read().strip())
