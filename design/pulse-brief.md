# BUILDER BRIEF — kody-w/twin: THE PULSE (bones · feed · lookup · gallery · hatch)
You are the BUILDER; this brief is your contract. Governing spec:
`~/rapp-static-apis/my-twin.profile.md` (read FULLY; your scope is §2, §3, §4, §7, §8, §12 + the
hatch one-liner). Also read this repo's README.md, SUMMON.md, TEMPLATE.md, card.json, facets.json,
installer/, and `~/rapp-static-apis/rapp-twin.profile.md` (frozen canon — do not drift from it) and
`~/rapp-static-apis/resolver/` (the expand()/hash-trust pattern).

## Work discipline
Work on branch `twin-pulse` in THIS repo (~/Documents/GitHub/twin). `git fetch` first; branch from
origin/main. Commit locally with clear messages. **DO NOT PUSH** — the architect gates publishing.

## Build
1. **Keys + signing (§2/§4)** — generate an Ed25519 keypair (Node `crypto`). Public key →
   `card.json` (+ `keys/twin.pub`). Private key → `keys/twin.key` and add to `.gitignore` — NEVER
   committed (verify with git check-ignore in your exit report). `tools/sign-frame.mjs` signs a
   frame file; `tools/verify-frame.mjs` verifies any frame against the pubkey + its sha —
   exit non-zero on tamper.
2. **Frames + the feed (§3/§4)** — `frames/` dir: each frame
   `{sha, prevSha, ts, kind, delta|cart, sig}` as `frames/<seq>-<sha8>.json`; `frames/HEAD` points
   at latest. `tools/pulse.mjs` regenerates `feed.xml` (Atom) from frames/ — the RSS-like broadcast;
   static-only, no server. Seed frame 0 from the current repo state (the twin's current bones).
3. **/twin lookup (§8)** — enrich `card.json`: `{twinId, who, pubkey, surfaces[], primary:true}`.
   `lookup.html`: static page that renders any twin repo's card (default this repo's; `?repo=owner/name`
   param fetches another's raw card.json) — "expand('kody-w/twin') → the user behind the twin".
   Document the address pattern in README (one short section, hash-trust framing).
4. **Gallery (§12)** — `gallery/index.html`: a static portfolio hosted purely from the bones
   (card + facets + holo.svg + vault-safe public notes if MANIFEST marks any public). Generic: works
   for ANY twin repo layout (reads card.json/facets.json relative). Quiet, muted, creature-forward
   aesthetic consistent with kody-w.github.io surfaces. An `?auth=local` stub shows where the
   authenticated on-device dimension will attach (clearly marked stub, no fake auth).
5. **Hatch one-liner (genie invoke)** — README + SUMMON.md get THE one-liner pattern, two forms:
   (a) `bash installer/start.sh` (exists — verify it still works, fix bitrot if trivial);
   (b) the Copilot genie: one line feeding copilot CLI a prompt to clone-if-missing + hatch + start
   the twin and report PULSE OK (`copilot --model claude-opus-4.8 -p "..." --allow-all-tools`).
   Keep each to ONE copy-pasteable line.
6. **Workshop alignment** — TEMPLATE.md: one tight section "bring your own twin": fork → the
   one-liner → your twin breathes; needs only a GitHub account.

## Hard constraints
- Static-only additions (tools/ may be Node scripts, zero npm deps). No CDN. No PII beyond what
  card.json already exposes. Frozen canon names (on-device twin / public twin), god/dog only as
  quoted aliases. DO NOT PUSH; do not touch main.

## Acceptance criteria
1. `node tools/verify-frame.mjs frames/<seed>` → OK; tamper a byte → non-zero exit.
2. `keys/twin.key` untracked (git check-ignore passes); pubkey present in card.json.
3. `tools/pulse.mjs` → valid Atom feed.xml listing the seed frame.
4. `lookup.html` + `gallery/index.html` render from bones alone via python3 -m http.server (no console errors).
5. Branch `twin-pulse` has clean, logical commits; nothing pushed; main untouched.

## Exit report
Files + line counts; criteria satisfaction; any bitrot found in installer/; deviations + why.
