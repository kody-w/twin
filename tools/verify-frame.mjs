// tools/verify-frame.mjs — verify a pulse frame before assimilating it (§2/§4/§15).
//
//   node tools/verify-frame.mjs <frame.json>
//
// Checks, exit NON-ZERO on any failure (tamper -> reject):
//   1. INTEGRITY   — recompute sha256 over the canonical core == frame.sha
//                    AND == the <sha8> in the filename (verify-before-act, PKI-free).
//   2. CHAIN       — prevSha shape is well-formed (null genesis or 64-hex).
//   3. AUTHENTICITY — the signature(s) verify against the EFFECTIVE lead key at this
//                    frame's position in the chain. §15: the lead key can rotate, so the
//                    authoritative key is resolved by replaying the public chain — start at
//                    card.json's pubkey, advance on each quorum-approved `rotate`. A `rotate`
//                    frame is authenticated by its multisig (`sigs[]`) against the quorum.
//
// A frame that lives in frames/ is judged with its true chain context. A standalone
// frame file (not yet in the chain) is judged against the genesis key.

import fs from "node:fs";
import path from "node:path";
import { digestFrame, resolvePublicKey, verifyCanonical, sha8 } from "./_frame.mjs";
import { resolveChain } from "./_chain.mjs";

function fail(msg) {
  console.error(`FAIL: ${msg}`);
  process.exit(1);
}

const framePath = process.argv[2];
if (!framePath) {
  console.error("usage: node tools/verify-frame.mjs <frame.json>");
  process.exit(2);
}
if (!fs.existsSync(framePath)) fail(`no such frame file: ${framePath}`);

let frame;
try {
  frame = JSON.parse(fs.readFileSync(framePath, "utf8"));
} catch (e) {
  fail(`frame is not valid JSON: ${e.message}`);
}

for (const k of ["sha", "kind"]) {
  if (frame[k] === undefined) fail(`frame missing required field: ${k}`);
}
if (frame.sig === undefined && frame.sigs === undefined) {
  fail("frame carries neither `sig` nor `sigs` (unsigned)");
}
if (frame.cart === undefined && frame.delta === undefined) {
  fail("frame carries neither `cart` nor `delta`");
}

// 1. INTEGRITY — recompute the content hash.
const { canonical, sha } = digestFrame(frame);
if (sha !== frame.sha) {
  fail(`integrity: recomputed sha ${sha} != frame.sha ${frame.sha} (tampered)`);
}

// filename check: frames/<seq>-<sha8>.json must carry the true sha8.
const base = path.basename(framePath);
const m = base.match(/^(\d+)-([0-9a-f]{8})\.json$/);
if (m && m[2] !== sha.slice(0, 8)) {
  fail(`integrity: filename sha8 ${m[2]} != content sha8 ${sha.slice(0, 8)} (tampered)`);
}

// 2. CHAIN — prevSha well-formed.
if (!(frame.prevSha === null || /^[0-9a-f]{64}$/.test(frame.prevSha || ""))) {
  fail(`chain: prevSha is neither null (genesis) nor a 64-hex sha: ${frame.prevSha}`);
}

// 3. AUTHENTICITY — resolve the effective key by walking the chain, then judge this frame.
let inChain = null;
try {
  const chain = resolveChain();
  inChain = chain.history.find((h) => h.sha8 === sha8(sha)) || null;
} catch {
  inChain = null;
}

if (inChain) {
  // The chain walk verified this frame against the correct effective key / quorum.
  if (!inChain.ok) {
    fail(`authenticity (in-chain): ${inChain.errors.join("; ")}`);
  }
} else {
  // Standalone frame (not in the live chain). Rotate frames need quorum context we don't have here.
  if (Array.isArray(frame.sigs)) {
    fail("authenticity: this is a multisig `rotate` frame — verify it in-chain (node tools/verify-chain.mjs)");
  }
  let pub;
  try {
    pub = resolvePublicKey();
  } catch (e) {
    fail(`cannot resolve public key: ${e.message}`);
  }
  if (!verifyCanonical(canonical, frame.sig, pub)) {
    fail("authenticity: Ed25519 signature does not verify against the genesis twin pubkey (tampered or wrong key)");
  }
}

console.log("OK");
console.log(`  frame:   ${base}`);
console.log(`  kind:    ${frame.kind}`);
console.log(`  sha:     ${frame.sha}`);
console.log(`  prevSha: ${frame.prevSha ?? "(genesis)"}`);
console.log(`  signed:  ${Array.isArray(frame.sigs) ? `multisig x${frame.sigs.length}` : "lead key"}${inChain ? " (chain-resolved)" : " (genesis key)"}`);
console.log(`  twin@${sha.slice(0, 8)}  — integrity + signature verified`);
process.exit(0);
