# BUILDER BRIEF — THE ESTATE: bones-lint (§13) + succession ceremony (§15)
You are the BUILDER; this brief is your contract. Read `~/rapp-static-apis/my-twin.profile.md`
§13+§15, this repo's `tools/` (_frame.mjs, sign-frame, verify-frame, seed-frame, pulse), README,
and TWIN-LICENSE.md fully first. Work on branch `estate` from latest origin/main; commit locally
with clean messages; **DO NOT PUSH** — the architect gates.

## The two holes being closed
(A) Public frames over years leak pattern-of-life even with a clean bones whitelist — fine
timestamps, precise coords, emission bursts. §13: pattern-of-life is soul, not body.
(B) One lost private key today = twin death. §15: succession is designed while the owner lives —
estate ceremonies between the owner's own devices, never a hosted recovery flow. If it can't be
inherited, it isn't owned.

## Build
### A — privacy as CI (§13)
1. **`tools/bones-lint.mjs`** — scans `frames/*.json`, `feed.xml`, `card.json`, `public-notes.json`:
   FAIL (non-zero, machine-readable report) on: timestamps finer than day precision; geohash-like
   strings >5 chars; >3 frames sharing one calendar day (burst); emails/phone-number patterns;
   any key outside the public whitelist. `--fix` optional flag quantizes timestamps in place.
2. **Quantization at the source** — `_frame.mjs`/`seed-frame.mjs`/`sign-frame.mjs` emit
   day-precision `ts` for public frames from now on. Re-sign the existing seed frame if it fails
   the lint (keep the old one under `frames/attic/` with a note — history is never destroyed).
   `pulse.mjs` feed entries get day precision. Verify-frame must still pass on everything.

### B — the estate ceremony (§15)
3. **`tools/shamir.mjs`** — pure zero-dep GF(256) Shamir k-of-n secret sharing: `split(secret,n,k)`
   / `combine(shards)`, with self-test vectors. No Math.random for anything secret — use
   `crypto.randomBytes`.
4. **`tools/succession.mjs`** subcommands:
   - `enroll <device-name> <pubkey-file>` → appends to `keys/quorum.json` AND emits a signed
     frame `{kind:'enroll', device, pubkey}` (signed by current lead key) into frames/.
   - `succession --heirs <pubkey-file...> --policy k-of-n` → signed frame `{kind:'succession',
     heirs[], policy}` — the public will.
   - `rotate --new <pubkey-file> --sign-with <enrolled-device-keys...>` → frame
     `{kind:'rotate', newKey}` signed by ≥k enrolled device keys (multi-sig array in the frame).
   - `shard --k 2 --n 3 [--qr]` → Shamir-shards `keys/twin.key` into `keys/shards/shard-*.txt`
     (gitignored!) and, with `--qr`, printable SVG QR per shard (also gitignored); prints the
     ceremony instructions ("print, distribute, safe/will").
   - `reconstruct <shard-files...>` → rebuilds twin.key.
5. **`tools/verify-frame.mjs` upgrade** — resolve the EFFECTIVE key by walking the public chain:
   start at card.json pubkey, apply valid `rotate` frames (each verified against the quorum
   at that point). All existing frames must still verify. Add `tools/verify-chain.mjs` that
   walks ALL frames in order and prints the key-history + verdict.
6. **`ESTATE.md`** — the human ceremony doc, heirloom-toned: enroll your devices the day you
   hatch; shard the key when you print the will; heirs inherit under TWIN-LICENSE terms (§15).
   One "90-second ceremony" quickstart.
7. **Self-test** — `tools/estate-selftest.mjs`: shamir split→combine roundtrip (incl. wrong-shard
   failure), enroll→rotate→verify-chain roundtrip with throwaway keys in a temp dir, bones-lint
   red/green fixtures. All PASS, exit 0.

## Constraints & criteria
Zero npm deps (node builtins only); nothing secret ever committed (shards + private keys
gitignored — PROVE with git check-ignore in the report); canon names; branch `estate`, local
commits only, NO PUSH. Criteria: (1) estate-selftest all PASS; (2) bones-lint exits non-zero on
a planted fine-grained frame fixture and zero on the live repo after quantization; (3)
verify-chain passes on live frames incl. a demo rotation in the selftest temp dir (NOT on the
live chain — do not rotate the real key); (4) feed still valid Atom; (5) git status clean, only
branch `estate` ahead. Exit report: files+lines, selftest output, lint before/after, criteria
satisfaction, deviations+why.
