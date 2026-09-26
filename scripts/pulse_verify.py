#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pulse_verify.py — verify the DOG end to end (stdlib only). Exit non-zero on
any break.

Verifies the JCS golden vector, current rapp/1 eleven-key envelopes, both
domain-separated hashes, contiguous seq/prev particle links, nondecreasing utc,
and the exact latest-N feed window with head_hash pointing to its final wave.
Published legacy/ and attic/ archives are not traversed.

Unsigned frames are valid. Signed current frames require registry-backed JWS
verification, which this offline tool does not implement: refuse them explicitly
instead of misapplying the retired Ed25519-key format or claiming authorship.

Any single failure -> non-zero exit. Clean chain -> exit 0.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulse_lib as pl  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    inp = pl.load_json(inp_p)
    with open(exp_p, "rb") as f:
        expected = f.read()
    got = pl.canonicalize(inp)
    if got == expected:
        r.ok("JCS golden vector byte-identical (sha256=%s)"
             % pl.payload_sha256(inp))
    else:
        r.fail("JCS golden vector MISMATCH\n    expected: %r\n    got:      %r"
               % (expected, got))


def verify(repo, pub_arg=None, quiet=False):
    r = Report(quiet=quiet)

    print("[1] JCS golden vector")
    try:
        _check_golden(repo, r)
    except (OSError, ValueError) as exc:
        r.fail("JCS golden vector: %s" % exc)

    print("[2] feed.json")
    feed_path = os.path.join(repo, "feed.json")
    feed = None
    try:
        feed = pl.load_json(feed_path)
        pl.validate_feed(feed)
        r.ok("rapp/1 feed; count == len(frames) == %d (<= %d)"
             % (feed["count"], pl.N))
        r.ok("feed.head_hash == frame_hash of last frame")
    except (OSError, ValueError) as exc:
        r.fail("feed.json: %s" % exc)
        feed = None

    print("[3] frames/<seq>.json chain")
    frames = None
    try:
        frames = pl.load_all_frames(repo)
        if not frames:
            raise ValueError("no frames/<seq>.json found")
        pl.validate_chain(frames)
        r.ok("%d frame(s) particle + wave + chain verified (seq 0..%d)"
             % (len(frames), len(frames) - 1))
        r.ok("signatures: %d unsigned (valid; no authorship claim)" % len(frames))
    except (OSError, ValueError) as exc:
        r.fail(str(exc))
        frames = None

    print("[4] feed/frame consistency")
    if feed is not None and frames is not None:
        if feed["frames"] != frames[-pl.N:]:
            r.fail("feed window must equal the newest %d frames/<seq>.json objects"
                   % min(pl.N, len(frames)))
        else:
            r.ok("feed window equals the newest frames/<seq>.json objects")

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
                    help="legacy option; does not enable rapp/1 JWS verification")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    args = ap.parse_args(argv)
    return verify(os.path.abspath(args.repo), args.pub, args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
