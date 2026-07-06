#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pulse_sign.py — mint the next twin.pulse frame for the DOG (stdlib only).

The lead GOD's upstream write path (spec 2.5). It:

  1. Reconstructs the last broadcast bones state by replaying frames/<seq>.json.
  2. Diffs it against the current bones/ directory -> a bones delta (set/delete).
  3. Builds the next rapp-frame/2.0 twin.pulse frame: seq = head+1,
     parent_sha = current head, sha256 = SHA-256(JCS(payload)).
  4. OPTIONALLY attaches a detached Ed25519 signature over sha256.
  5. Writes the immutable frames/<seq>.json (full history kept forever), then
     rewrites feed.json (append, trim to the newest N=64, refresh head_sha +
     count) and regenerates feed.xml.

Signing keys: the PRIVATE seed lives at keys/pulse.ed25519.key (gitignored via
keys/*.key) and never travels in the bones; only keys/pulse.ed25519.pub is
committed, which is what edges verify against.

Examples:
  python3 scripts/pulse_sign.py                 # sign if a key exists, else unsigned
  python3 scripts/pulse_sign.py --sign          # sign (generate a keypair if missing)
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
DEFAULT_PUB = os.path.join("keys", "pulse.ed25519.pub")


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _ensure_key(key_path, pub_path):
    """Return the 32-byte seed, generating + persisting a keypair if absent."""
    if os.path.exists(key_path):
        return pl.load_seed_hex(key_path)
    seed, pub = pl.gen_keypair()
    os.makedirs(os.path.dirname(key_path) or ".", exist_ok=True)
    with open(key_path, "w", encoding="utf-8") as f:
        f.write(seed.hex() + "\n")
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    with open(pub_path, "w", encoding="utf-8") as f:
        f.write(pub.hex() + "\n")
    print("[pulse_sign] generated a new Ed25519 keypair")
    print("             private (gitignored): %s" % key_path)
    print("             public  (committed):  %s" % pub_path)
    return seed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mint the next twin.pulse frame.")
    ap.add_argument("--repo", default=REPO, help="repo root (default: this repo)")
    ap.add_argument("--bones", default=None, help="bones dir (default: <repo>/bones)")
    ap.add_argument("--ts", default=os.environ.get("PULSE_TS"),
                    help="RFC-3339 UTC timestamp (advisory; default: now)")
    ap.add_argument("--key", default=None, help="Ed25519 private seed (hex)")
    ap.add_argument("--pub", default=None, help="Ed25519 public key (hex)")
    ap.add_argument("--sign", action="store_true",
                    help="sign the frame (generate a keypair if none exists)")
    ap.add_argument("--no-sign", action="store_true",
                    help="force an unsigned frame")
    ap.add_argument("--allow-empty", action="store_true",
                    help="emit a heartbeat frame even with no bones changes")
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    bones_dir = args.bones or os.path.join(repo, "bones")
    key_path = args.key or os.path.join(repo, DEFAULT_KEY)
    pub_path = args.pub or os.path.join(repo, DEFAULT_PUB)

    if not os.path.isdir(bones_dir):
        print("error: bones dir not found: %s" % bones_dir, file=sys.stderr)
        return 2

    frames = pl.load_all_frames(repo)
    prev_state = pl.replay(frames)
    cur_state = pl.load_bones(bones_dir)
    ops = pl.diff_ops(prev_state, cur_state)

    if not ops and not args.allow_empty:
        print("[pulse_sign] no bones changes since head — nothing to broadcast.")
        print("             (use --allow-empty to mint a heartbeat frame.)")
        return 0

    seq = (frames[-1]["seq"] + 1) if frames else 0
    parent_sha = frames[-1]["sha256"] if frames else None
    ts = args.ts or _now_iso()

    frame = pl.build_frame(seq, ops, parent_sha, ts)

    # Signing policy: --no-sign wins; else --sign or an existing key triggers it.
    do_sign = False
    if args.no_sign:
        do_sign = False
    elif args.sign or os.path.exists(key_path):
        do_sign = True
    if do_sign:
        seed = _ensure_key(key_path, pub_path)
        pl.attach_sig(frame, seed)

    pl.write_frame(repo, frame)

    all_frames = pl.load_all_frames(repo)          # includes the new frame
    feed = pl.build_feed(all_frames)               # trims to newest N=64
    pl.write_feed(repo, feed)
    pl.write_feed_xml(repo, feed)

    print("[pulse_sign] minted frames/%d.json" % seq)
    print("             seq        : %d" % seq)
    print("             ts         : %s" % ts)
    print("             sha256     : %s" % frame["sha256"])
    print("             parent_sha : %s" % frame["parent_sha"])
    print("             signed     : %s" % ("yes (ed25519)" if do_sign else "no"))
    print("             bones ops  : %s" % ", ".join(
        "%s:%s" % (p, o["op"]) for p, o in sorted(ops.items())) or "(none)")
    print("             feed frames: %d (of %d total; window N=%d)" % (
        feed["count"], len(all_frames), pl.N))
    print("             head_sha   : %s" % feed["head_sha"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
