#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pulse_lib — shared, STDLIB-ONLY core for the current rapp/1 twin.pulse DOG.

The eleven-key envelope and domain-separated particle/wave hashes match
utils/frames.py. ``prev`` always links to the preceding particle, while the
feed head and Atom entry IDs identify waves. Sealed legacy schemas are never
interpreted as current frames.

The retained Ed25519 primitives are not a RAPP/1 signing implementation.
Current signatures require registry-backed detached JWS; this offline tool
refuses them rather than trusting the legacy key/signature representation.

Bones rule (load-bearing): the pulse never emits a bare float in a bones
payload. Integers or strings only; `build_frame()` refuses a float. The
canonical form itself is the full RAPP/1 rev-17 §4 (RFC 8785) form, so any
binary64 number verifies; its number layout and I-JSON rules are copied from
kody-w/rapp-1 rapp.py at f6bafe76735ba73510518810c8bc8cd133dcf527.
"""

import decimal
import hashlib
import json
import os
import re

# ---------------------------------------------------------------------------
# Constants for the published current pulse; historical archives are read-only.
# ---------------------------------------------------------------------------
SPEC = "rapp/1"
LEGACY_SPECS = ("rapp-frame/2.0", "rapp-frame/2.1")
FRAME_KIND = "twin.pulse"
FEED_KIND = "twin.pulse.feed"
TWIN_ID = "rappid:@kody-w/twin:5714cdf964b6a6936b44420aa8e8589b2ee9342e10810cdf12fc3c7be7667c30"
N = 64  # feed window: newest N frames live in feed.json; frames/ keeps all.

BASE_RAW = "https://raw.githubusercontent.com/kody-w/twin/main"
FRAME_KEYS = frozenset((
    "spec", "kind", "stream_id", "seq", "utc", "payload", "payload_hash",
    "frame_hash", "prev", "prev_wave", "sig",
))
FEED_KEYS = frozenset((
    "spec", "kind", "twin_id", "stream_id", "head_hash", "count", "frames",
))
SIGNATURE_ERROR = (
    "rapp/1 signatures require registry-backed detached JWS; "
    "legacy Ed25519 keys/signatures are unsupported by this offline pulse tool"
)
_UTC_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
                     r"[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z")
_HASH_RE = re.compile(r"[0-9a-f]{64}")
# RAPP/1 §5 (rev-17 E-7): the only tags H (a value hash) is used with.
_H_TAGS = frozenset(("rapp/1:particle", "rapp/1:wave", "rapp/1:egg-manifest",
                     "rapp/1:sealed-aad", "rapp/1:sealed-key-request"))
MAX_CANONICAL_BYTES = 1024 * 1024

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


# §4 (b), RFC 7493 §2.1: surrogate code points and the 66 noncharacters are outside I-JSON.
_NOT_IJSON_CHAR = re.compile(
    "[\ud800-\udfff\ufdd0-\ufdef"
    + "".join(chr(plane << 16 | 0xFFFE) + chr(plane << 16 | 0xFFFF) for plane in range(17))
    + "]"
)


def _number_to_string(x):
    """ECMA-262 Number::toString of a finite binary64 value: the RFC 8785 §3.2.2.3 number form."""
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("NaN and infinities are outside the §4 domain")
    if x == 0:
        return "0"                          # both zeros; -0 serializes as 0
    # repr() is the shortest digit string that round-trips (nearest, ties to even), the
    # digits Number::toString picks; only the layout differs, so re-lay it out here.
    mantissa, _, exponent = repr(abs(x)).partition("e")
    whole, _, fraction = mantissa.partition(".")
    digits = (whole + fraction).lstrip("0")
    n = len(whole) + int(exponent or 0) - (len(whole) + len(fraction) - len(digits))
    digits = digits.rstrip("0")
    k = len(digits)                         # value = 0.digits * 10**n
    if k <= n <= 21:
        text = digits + "0" * (n - k)
    elif 0 < n <= 21:
        text = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        text = "0." + "0" * -n + digits
    else:
        text = digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + ("+" if n > 0 else "-") + str(abs(n - 1))
    return ("-" if x < 0 else "") + text


def _json_number(token):
    """§4 (c): parse a number token as its nearest binary64 d; refuse unless d is finite and
    Number::toString(d) denotes exactly the token's value (so 0.1 passes, 0.10000000000000001 does not)."""
    d = float(token)                                   # correctly rounded, ties to even; overlong -> +/-inf
    if d != d or d in (float("inf"), float("-inf")):
        raise ValueError(f"number token {token[:40]} is not a finite binary64 value (§4 (c))")
    try:
        same = decimal.Decimal(token) == decimal.Decimal(_number_to_string(d))
    except ArithmeticError:
        # An exponent beyond decimal's range. d is finite, so it is a zero, and the token
        # denotes the same value iff every digit of its significand is zero.
        same = not any(c in "123456789" for c in token.lower().partition("e")[0])
    if not same:
        raise ValueError(f"number token {token[:40]} does not survive the binary64 round trip (§4 (c))")
    return d


def _json_int(token):
    if token == "-0":
        return -0.0          # E-9: -0 is not an integer token a field rule may take for 0; canonical(-0.0) is "0"
    d = _json_number(token)  # refuses 9007199254740993 and overlong tokens before int() runs
    value = int(token)
    # 10**23 passes §4 (c) (its d prints as "1e+23") but is not d; the value parsed is d itself.
    return value if value == d else int(d)


def _ser_string(s):
    # RFC 8785 3.2.2.2: two-char escapes for the named control chars, \u00xx
    # (lowercase) for the remaining C0 controls, everything else verbatim (so
    # non-ASCII is emitted as raw UTF-8, NOT \u-escaped). '/' is NOT escaped.
    bad = _NOT_IJSON_CHAR.search(s)
    if bad:
        raise ValueError("JCS: string holds U+%04X, a surrogate or noncharacter "
                         "outside I-JSON (RAPP/1 §4 (b))" % ord(bad.group()))
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
        if abs(o) <= 2 ** 53 - 1:
            return str(o)
        # RAPP/1 §4 (c): an integer beyond +/-(2^53-1) is admitted only when it
        # is exactly a binary64 value, and is then serialized as that number.
        try:
            as_binary64 = float(o)
        except OverflowError:
            as_binary64 = None
        if as_binary64 != o:
            raise ValueError("JCS: integer is not exactly representable as "
                             "binary64 (RAPP/1 §4 (c)); carry it as a string")
        return _number_to_string(as_binary64)
    if isinstance(o, float):
        return _number_to_string(o)
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
    """Plain JCS digest for golden-vector diagnostics, NOT a rapp/1 address."""
    return hashlib.sha256(canonicalize(payload)).hexdigest()


def content_hash(domain, value):
    """The same RAPP/1 H(domain, value) rule as utils/frames.py::_H."""
    if not isinstance(domain, str) or domain not in _H_TAGS:
        raise ValueError("RAPP/1 §5: H is used only with the tags %s; refused %r"
                         % (", ".join(sorted(_H_TAGS)), domain))
    return hashlib.sha256(
        domain.encode('utf-8') + b'\n' + canonicalize(value)).hexdigest()


def frame_hash(frame):
    return content_hash("rapp/1:wave", {
        key: value for key, value in frame.items()
        if key not in ("frame_hash", "sig")
    })


def require_current_schema(value, label="frame"):
    """Dispatch explicitly: only current frames/feeds enter the active path."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a JSON object" % label)
    spec = value.get("spec")
    if spec == SPEC:
        return
    if spec in LEGACY_SPECS:
        raise ValueError(
            "%s: legacy schema %r is sealed, not supported by active pulse "
            "tooling; keep historical inputs under frames/legacy/" % (label, spec))
    raise ValueError("%s: unsupported schema %r; expected %r" % (label, spec, SPEC))


def validate_utc(utc):
    if not isinstance(utc, str) or not _UTC_RE.fullmatch(utc):
        raise ValueError("utc must be YYYY-MM-DDTHH:MM:SS.mmmZ")
    # RAPP/1 §7.4 (rev-17 E-1): proleptic Gregorian, years 0000-9999, second 00-59.
    year, month, day = int(utc[0:4]), int(utc[5:7]), int(utc[8:10])
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not (1 <= month <= 12 and 1 <= day <= days[month - 1] and int(utc[11:13]) <= 23
            and int(utc[14:16]) <= 59 and int(utc[17:19]) <= 59):
        raise ValueError("utc is not a calendar-valid UTC timestamp: %r" % utc)


def normalize_utc(utc):
    """Accept the old CLI's whole seconds, but emit exact millisecond UTC."""
    if not isinstance(utc, str):
        raise ValueError("utc must be a UTC timestamp string")
    match = re.fullmatch(
        r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})"
        r"(?:\.([0-9]{1,3}))?Z", utc)
    if not match:
        raise ValueError("utc must be RFC-3339 UTC with at most millisecond precision")
    result = match.group(1) + "." + (match.group(2) or "").ljust(3, "0") + "Z"
    validate_utc(result)
    return result


def validate_frame(frame, stream_id=TWIN_ID):
    require_current_schema(frame)
    if set(frame) != FRAME_KEYS:
        raise ValueError(
            "expected exactly eleven rapp/1 envelope keys (missing=%s, extra=%s)"
            % (sorted(FRAME_KEYS - set(frame)), sorted(set(frame) - FRAME_KEYS)))
    if frame["kind"] != FRAME_KIND:
        raise ValueError("kind must be %r" % FRAME_KIND)
    if frame["stream_id"] != stream_id:
        raise ValueError("stream_id must be %r" % stream_id)
    seq = frame["seq"]
    if type(seq) is not int or not 0 <= seq <= 2 ** 53 - 1:
        raise ValueError("seq must be an integer in 0..2^53-1")
    validate_utc(frame["utc"])
    if not isinstance(frame["payload"], dict):
        raise ValueError("payload must be a JSON object")
    for key in ("payload_hash", "frame_hash", "prev"):
        value = frame[key]
        if key == "prev" and value is None:
            continue
        if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
            raise ValueError("%s must be a lowercase 64-hex hash" % key)
    if frame["prev_wave"] is not None:
        raise ValueError("prev_wave must be null for this non-swarm pulse")
    if content_hash("rapp/1:particle", frame["payload"]) != frame["payload_hash"]:
        raise ValueError("payload_hash does not match H('rapp/1:particle', payload)")
    if frame_hash(frame) != frame["frame_hash"]:
        raise ValueError("frame_hash does not match H('rapp/1:wave', envelope)")
    verify_frame_sig(frame, None)


def validate_chain(frames, stream_id=TWIN_ID):
    previous = None
    for seq, frame in enumerate(frames):
        try:
            validate_frame(frame, stream_id)
            if frame["seq"] != seq:
                raise ValueError("seq gap/mismatch: expected %d, got %r"
                                 % (seq, frame["seq"]))
            expected = previous["payload_hash"] if previous else None
            if frame["prev"] != expected:
                raise ValueError("prev must link to the preceding payload_hash "
                                 "(null at genesis)")
            if previous and frame["utc"] < previous["utc"]:
                raise ValueError("utc must not precede the previous frame's utc")
        except ValueError as exc:
            tag = frame.get("seq", seq) if isinstance(frame, dict) else seq
            raise ValueError("frames/%s.json: %s" % (tag, exc)) from exc
        previous = frame


def validate_feed(feed, twin_id=TWIN_ID):
    require_current_schema(feed, "feed")
    if set(feed) != FEED_KEYS:
        raise ValueError("feed keys must be %s (head_hash identifies the wave)"
                         % ", ".join(sorted(FEED_KEYS)))
    if feed["kind"] != FEED_KIND:
        raise ValueError("feed.kind must be %r" % FEED_KIND)
    if feed["twin_id"] != twin_id:
        raise ValueError("feed.twin_id must be %r" % twin_id)
    if feed["stream_id"] != twin_id:
        raise ValueError("feed.stream_id must be %r" % twin_id)
    frames = feed["frames"]
    if not isinstance(frames, list):
        raise ValueError("feed.frames must be an array")
    if type(feed["count"]) is not int or feed["count"] != len(frames):
        raise ValueError("feed.count must equal len(frames)")
    if len(frames) > N:
        raise ValueError("feed window exceeds N=%d" % N)
    for frame in frames:
        validate_frame(frame, twin_id)
    seqs = [frame["seq"] for frame in frames]
    if seqs != sorted(set(seqs)):
        raise ValueError("feed.frames must have unique ascending seq values")
    expected = frames[-1]["frame_hash"] if frames else None
    if feed["head_hash"] != expected:
        raise ValueError("feed.head_hash must equal the last frame_hash")


# ===========================================================================
# 2. Legacy Ed25519 (RFC 8032) primitives, not RAPP/1 JWS authentication.
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
            if fn.endswith('.json'):
                state[rel] = load_json(full)
            else:
                with open(full, 'r', encoding='utf-8') as f:
                    state[rel] = f.read()
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
        require_current_schema(fr)
        payload = fr.get('payload')
        if not isinstance(payload, dict) or not isinstance(payload.get('bones'), dict):
            raise ValueError("replay: payload.bones must be an object")
        for path, op in payload['bones'].items():
            if not isinstance(op, dict) or 'op' not in op:
                raise ValueError("replay: invalid bones operation at %s" % path)
            kind = op['op']
            if kind in ('set', 'merge') and 'value' not in op:
                raise ValueError("replay: %s operation missing value at %s" % (kind, path))
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
def _refuse_floats(value):
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, float):
            raise ValueError(
                "bare float not allowed in a bones payload (%r) — use an "
                "integer or a string" % item)
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)


def build_frame(seq, ops, prev, utc, stream_id=TWIN_ID):
    _refuse_floats(ops)
    payload = {'bones': ops}
    frame = {
        'spec': SPEC,
        'kind': FRAME_KIND,
        'stream_id': stream_id,
        'seq': seq,
        'utc': utc,
        'payload': payload,
        'payload_hash': content_hash("rapp/1:particle", payload),
        'prev': prev,
        'prev_wave': None,
        'sig': None,
    }
    frame['frame_hash'] = frame_hash(frame)
    validate_frame(frame, stream_id)
    return frame


def attach_sig(frame, seed):
    require_current_schema(frame)
    raise ValueError(SIGNATURE_ERROR)


def verify_frame_sig(frame, pubkey):
    """Unsigned current frames are valid; never apply legacy key trust to JWS."""
    require_current_schema(frame)
    if frame.get('sig') is None:
        return True
    raise ValueError(SIGNATURE_ERROR)


def build_feed(frames, n=N, twin_id=TWIN_ID):
    for frame in frames:
        require_current_schema(frame)
    ordered = sorted(frames, key=lambda f: f['seq'])
    validate_chain(ordered, twin_id)
    if type(n) is not int or not 1 <= n <= N:
        raise ValueError("feed window must be an integer in 1..%d" % N)
    window = ordered[-n:]
    return {
        'spec': SPEC,
        'kind': FEED_KIND,
        'twin_id': twin_id,
        'stream_id': twin_id,
        'head_hash': window[-1]['frame_hash'] if window else None,
        'count': len(window),
        'frames': window,
    }


def _xml_escape(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;'))


def build_feed_xml(feed, base_raw=BASE_RAW):
    validate_feed(feed)
    frames = feed['frames']
    updated = frames[-1]['utc'] if frames else '1970-01-01T00:00:00.000Z'
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<feed xmlns="http://www.w3.org/2005/Atom">',
         '  <title>the pulse — @kody-w/twin</title>',
         '  <subtitle>rapp/1 — a DOG: content-addressed, hash-chained twin '
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
        sha = fr['frame_hash']
        seq = fr['seq']
        signed = 'signed' if fr.get('sig') else 'unsigned'
        L.append('  <entry>')
        # Waves distinguish heartbeat frames with identical particle payloads.
        L.append('    <id>%s</id>' % _xml_escape(sha))
        L.append('    <title>twin.pulse seq %d</title>' % seq)
        L.append('    <updated>%s</updated>' % _xml_escape(fr['utc']))
        L.append('    <category term="twin.pulse"/>')
        L.append('    <link rel="alternate" type="application/json" '
                 'href="%s/frames/%d.json"/>' % (base_raw, seq))
        parent = fr['prev'] if fr['prev'] else 'genesis (null)'
        L.append('    <summary type="text">twin.pulse frame seq %d (%s); '
                 'frame_hash=%s; prev=%s</summary>'
                 % (seq, signed, sha, _xml_escape(parent)))
        L.append('  </entry>')
    L.append('</feed>')
    return '\n'.join(L) + '\n'


# ===========================================================================
# 5. Repo I/O.
# ===========================================================================
_FRAME_RE = re.compile(r'^([0-9]+)\.json$')
_LEGACY_FRAME_RE = re.compile(r'^[0-9]+-[0-9a-f]{8}\.json$')


def frames_dir(repo):
    return os.path.join(repo, 'frames')


def load_all_frames(repo):
    """Load current frames only; never traverse legacy/ or attic/ archives."""
    d = frames_dir(repo)
    out = []
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if _LEGACY_FRAME_RE.fullmatch(fn) or fn == 'HEAD':
                raise ValueError(
                    "frames/%s: legacy cartridge input is not a rapp/1 pulse; "
                    "use the historical tools/ verifier, not active pulse tooling" % fn)
            m = _FRAME_RE.match(fn)
            if not m:
                continue
            path = os.path.join(d, fn)
            frame = load_json(path)
            require_current_schema(frame, "frames/%s" % fn)
            seq = frame.get('seq')
            if type(seq) is not int or fn != '%d.json' % seq:
                raise ValueError("frames/%s: filename does not match integer seq %r"
                                 % (fn, seq))
            out.append((int(m.group(1)), frame))
    out.sort(key=lambda t: t[0])
    return [fr for _seq, fr in out]


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key %r" % key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-JSON numeric constant %s" % value)


def _check_bounds(value):
    """RAPP/1 §4 (d): nesting depth at most 64, canonical form at most 1 MiB."""
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if isinstance(current, (dict, list)):
            if depth > 64:
                raise ValueError("JSON nesting depth exceeds 64 (RAPP/1 §4 (d))")
            items = current.values() if isinstance(current, dict) else current
            stack.extend((item, depth + 1) for item in items)
    if len(canonicalize(value)) > MAX_CANONICAL_BYTES:
        raise ValueError("canonical JSON exceeds 1 MiB (RAPP/1 §4 (d))")


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            value = json.load(f, object_pairs_hook=_json_object,
                              parse_constant=_reject_constant,
                              parse_float=_json_number, parse_int=_json_int)
        _check_bounds(value)
        return value
    except (OSError, ValueError, RecursionError) as exc:
        raise ValueError("%s: %s" % (path, exc)) from exc


def _dump(path, obj, mode='w'):
    with open(path, mode, encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def write_frame(repo, frame):
    validate_frame(frame)
    d = frames_dir(repo)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, '%d.json' % frame['seq'])
    _dump(path, frame, mode='x')
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
