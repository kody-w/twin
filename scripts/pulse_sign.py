#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pulse_sign.py — mint the next twin.pulse frame for the DOG (stdlib only).

The lead GOD's upstream write path (spec 2.5). It:

  1. Reconstructs the last broadcast bones state by replaying frames/<seq>.json.
  2. Diffs it against the current bones/ directory -> a bones delta (set/delete).
  3. Builds the next rapp/1 twin.pulse frame: seq = head+1, prev = the
     preceding payload_hash, with domain-separated particle and wave hashes.
  4. Refuses legacy signing: current signatures require registry-backed JWS.
  5. Writes the immutable frames/<seq>.json (full history kept forever), then
     rewrites feed.json (append, trim to the newest N=64, refresh head_hash +
     count) and regenerates feed.xml.

This tool mints unsigned current frames, matching the published chain. It
never generates keys or treats a legacy Ed25519 signature as a current JWS.
An existing legacy key requires explicit --no-sign; --sign fails before writes.

Examples:
  python3 scripts/pulse_sign.py                 # unsigned if no legacy key exists
  python3 scripts/pulse_sign.py --no-sign       # force an unsigned frame
  python3 scripts/pulse_sign.py --allow-empty   # heartbeat frame with an empty delta
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pulse_lib as pl  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KEY = os.path.join("keys", "pulse.ed25519.key")


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mint the next twin.pulse frame.")
    ap.add_argument("--repo", default=REPO, help="repo root (default: this repo)")
    ap.add_argument("--bones", default=None, help="bones dir (default: <repo>/bones)")
    ap.add_argument("--ts", default=os.environ.get("PULSE_TS"),
                    help="UTC timestamp (seconds or milliseconds; default: now)")
    ap.add_argument("--key", default=None, help="legacy key path (never read)")
    ap.add_argument("--pub", default=None, help="legacy pubkey path (never read)")
    ap.add_argument("--sign", action="store_true",
                    help="refused: current signing requires registry-backed JWS")
    ap.add_argument("--no-sign", action="store_true",
                    help="force an unsigned frame")
    ap.add_argument("--allow-empty", action="store_true",
                    help="emit a heartbeat frame even with no bones changes")
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    bones_dir = args.bones or os.path.join(repo, "bones")
    key_path = args.key or os.path.join(repo, DEFAULT_KEY)

    if not os.path.isdir(bones_dir):
        print("error: bones dir not found: %s" % bones_dir, file=sys.stderr)
        return 2

    try:
        frames = pl.load_all_frames(repo)
        pl.validate_chain(frames)
        if not args.no_sign and (args.sign or os.path.exists(key_path)):
            raise ValueError(pl.SIGNATURE_ERROR + "; use --no-sign to mint unsigned")
        prev_state = pl.replay(frames)
        cur_state = pl.load_bones(bones_dir)
        ops = pl.diff_ops(prev_state, cur_state)

        if not ops and not args.allow_empty:
            print("[pulse_sign] no bones changes since head — nothing to broadcast.")
            print("             (use --allow-empty to mint a heartbeat frame.)")
            return 0

        seq = frames[-1]["seq"] + 1 if frames else 0
        prev = frames[-1]["payload_hash"] if frames else None
        utc = pl.normalize_utc(args.ts if args.ts is not None else _now_iso())
        frame = pl.build_frame(seq, ops, prev, utc)
        all_frames = frames + [frame]
        feed = pl.build_feed(all_frames)

        pl.write_frame(repo, frame)
        pl.write_feed(repo, feed)
        pl.write_feed_xml(repo, feed)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    print("[pulse_sign] minted frames/%d.json" % seq)
    print("             seq        : %d" % seq)
    print("             utc        : %s" % utc)
    print("             payload_hash: %s" % frame["payload_hash"])
    print("             frame_hash : %s" % frame["frame_hash"])
    print("             prev       : %s" % frame["prev"])
    print("             signed     : no")
    print("             bones ops  : %s" % ", ".join(
        "%s:%s" % (p, o["op"]) for p, o in sorted(ops.items())) or "(none)")
    print("             feed frames: %d (of %d total; window N=%d)" % (
        feed["count"], len(all_frames), pl.N))
    print("             head_hash  : %s" % feed["head_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
