#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pulse_verify.py — verify the DOG end to end (stdlib only). Exit non-zero on
any break.

Recomputes the whole chain from the static broadcast surface:

  * JCS golden vector          — canonical(payload) is byte-identical to the
                                 checked-in RFC 8785 reference, so a JS /
                                 vbrainstem signer derives the same sha256.
  * feed.json shape            — kind == twin.pulse.feed, count == len(frames)
                                 <= N=64, head_sha == sha256 of the last frame.
  * every frames/<seq>.json    — sha256 == SHA-256(JCS(payload)); the parent_sha
                                 chain links unbroken from genesis (seq 0,
                                 parent_sha == null) with no gaps; structural
                                 fields (spec/kind/twin_id/kernel_version/seq/ts)
                                 are well-formed.
  * signatures                 — a present sig MUST verify against the committed
                                 Ed25519 pubkey; an absent sig is valid (sig is
                                 optional; identity is sha-based).
  * feed/frame consistency     — each in-window feed frame is byte-for-byte the
                                 same object as its frames/<seq>.json, so a
                                 single-byte flip in any frame file is caught.

Any single failure -> non-zero exit. Clean chain -> exit 0.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulse_lib as pl  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PUB = os.path.join("keys", "pulse.ed25519.pub")
_TS_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$')


class Report(object):
    def __init__(self, quiet=False):
        self.errors = []
        self.quiet = quiet

    def ok(self, msg):
        if not self.quiet:
            print("  ok   " + msg)

    def fail(self, msg):
        self.errors.append(msg)
        print("  FAIL " + msg)


def _check_golden(repo, r):
    inp_p = os.path.join(repo, "scripts", "testdata", "jcs_golden_input.json")
    exp_p = os.path.join(repo, "scripts", "testdata", "jcs_golden_expected.jcs")
    if not (os.path.exists(inp_p) and os.path.exists(exp_p)):
        r.ok("JCS golden vector: (no testdata committed — skipped)")
        return
    with open(inp_p, encoding="utf-8") as f:
        inp = json.load(f)
    with open(exp_p, "rb") as f:
        expected = f.read()
    got = pl.canonicalize(inp)
    if got == expected:
        r.ok("JCS golden vector byte-identical (sha256=%s)"
             % pl.payload_sha256(inp))
    else:
        r.fail("JCS golden vector MISMATCH\n    expected: %r\n    got:      %r"
               % (expected, got))


def _load_pubkey(repo, pub_arg):
    path = pub_arg or os.path.join(repo, DEFAULT_PUB)
    if os.path.exists(path):
        try:
            return pl.load_pubkey_hex(path), path
        except Exception as e:  # noqa: BLE001
            return None, "%s (unreadable: %s)" % (path, e)
    return None, path


def verify(repo, pub_arg=None, quiet=False):
    r = Report(quiet=quiet)

    print("[1] JCS golden vector")
    _check_golden(repo, r)

    print("[2] feed.json")
    feed_path = os.path.join(repo, "feed.json")
    feed = None
    if not os.path.exists(feed_path):
        r.fail("feed.json missing")
    else:
        with open(feed_path, encoding="utf-8") as f:
            feed = json.load(f)
        if feed.get("spec") != pl.SPEC:
            r.fail("feed.spec != %r" % pl.SPEC)
        if feed.get("kind") != pl.FEED_KIND:
            r.fail("feed.kind != %r (got %r)" % (pl.FEED_KIND, feed.get("kind")))
        else:
            r.ok('feed.kind == "twin.pulse.feed"')
        if feed.get("twin_id") != pl.TWIN_ID:
            r.fail("feed.twin_id != %r" % pl.TWIN_ID)
        fr = feed.get("frames", [])
        if feed.get("count") != len(fr):
            r.fail("feed.count (%r) != len(frames) (%d)"
                   % (feed.get("count"), len(fr)))
        elif len(fr) > pl.N:
            r.fail("feed has %d frames > N=%d" % (len(fr), pl.N))
        else:
            r.ok("feed.count == len(frames) == %d (<= %d)" % (len(fr), pl.N))
        seqs = [x.get("seq") for x in fr]
        if seqs != sorted(seqs):
            r.fail("feed.frames not ascending by seq: %r" % seqs)
        if fr:
            if feed.get("head_sha") != fr[-1].get("sha256"):
                r.fail("feed.head_sha != sha256 of last frame")
            else:
                r.ok("feed.head_sha == sha256 of last frame")

    print("[3] frames/<seq>.json chain")
    frames = pl.load_all_frames(repo)
    pub, pub_src = _load_pubkey(repo, pub_arg)
    if not frames:
        r.fail("no frames/<seq>.json found")
    running = None
    signed_count = 0
    for i, frm in enumerate(frames):
        seq = frm.get("seq")
        tag = "frames/%s.json" % seq
        # structural
        if frm.get("spec") != pl.SPEC:
            r.fail("%s spec != %r" % (tag, pl.SPEC))
        if frm.get("kind") != pl.FRAME_KIND:
            r.fail("%s kind != %r" % (tag, pl.FRAME_KIND))
        if frm.get("twin_id") != pl.TWIN_ID:
            r.fail("%s twin_id != %r" % (tag, pl.TWIN_ID))
        if frm.get("kernel_version") != pl.KERNEL_VERSION:
            r.fail("%s kernel_version != %r" % (tag, pl.KERNEL_VERSION))
        if seq != i:
            r.fail("%s seq gap/mismatch: expected %d, got %r" % (tag, i, seq))
        if not isinstance(frm.get("ts"), str) or not _TS_RE.match(frm["ts"]):
            r.fail("%s ts not RFC-3339 UTC: %r" % (tag, frm.get("ts")))
        # hash integrity (JCS recompute)
        try:
            recomputed = pl.payload_sha256(frm["payload"])
        except Exception as e:  # noqa: BLE001
            r.fail("%s payload not canonicalizable: %s" % (tag, e))
            recomputed = None
        if recomputed is not None and recomputed != frm.get("sha256"):
            r.fail("%s sha256 mismatch: stored %s != recomputed %s"
                   % (tag, frm.get("sha256"), recomputed))
        # chain linkage
        if i == 0:
            if frm.get("parent_sha") is not None:
                r.fail("%s genesis parent_sha must be null" % tag)
        else:
            if frm.get("parent_sha") != running:
                r.fail("%s parent_sha does not link to prior head" % tag)
        # signature (optional)
        if frm.get("sig") is not None:
            signed_count += 1
            if pub is None:
                r.fail("%s is signed but no pubkey at %s" % (tag, pub_src))
            elif not pl.verify_frame_sig(frm, pub):
                r.fail("%s signature INVALID against %s" % (tag, pub_src))
        running = frm.get("sha256")
    if not r.errors:
        r.ok("%d frame(s) hash + chain verified from genesis (seq 0..%d)"
             % (len(frames), len(frames) - 1))
        r.ok("signatures: %d signed (verified vs %s), %d unsigned (valid)"
             % (signed_count, os.path.relpath(pub_src, repo)
                if pub else pub_src, len(frames) - signed_count))

    print("[4] feed/frame consistency")
    if feed is not None:
        by_seq = {f["seq"]: f for f in frames}
        mism = 0
        for ff in feed.get("frames", []):
            s = ff.get("seq")
            if s not in by_seq:
                r.fail("feed frame seq %r has no frames/%r.json" % (s, s))
                mism += 1
            elif ff != by_seq[s]:
                r.fail("feed frame seq %r differs from frames/%r.json" % (s, s))
                mism += 1
        if mism == 0 and feed.get("frames"):
            r.ok("every in-window feed frame equals its frames/<seq>.json")

    print("")
    if r.errors:
        print("PULSE VERIFY: FAIL (%d error(s))" % len(r.errors))
        return 1
    print("PULSE VERIFY: OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify the twin.pulse DOG.")
    ap.add_argument("--repo", default=REPO, help="repo root (default: this repo)")
    ap.add_argument("--pub", default=None,
                    help="Ed25519 pubkey hex (default: keys/pulse.ed25519.pub)")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    args = ap.parse_args(argv)
    return verify(os.path.abspath(args.repo), args.pub, args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
