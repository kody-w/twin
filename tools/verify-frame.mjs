// tools/verify-frame.mjs — verify a pulse frame before assimilating it (§2/§4).
//
//   node tools/verify-frame.mjs <frame.json>
//
// Three independent checks, exit NON-ZERO on any failure (tamper -> reject):
//   1. INTEGRITY  — recompute sha256 over the canonical core == frame.sha
//                   AND == the <sha8> in the filename (verify-before-act, PKI-free).
//   2. AUTHENTICITY — Ed25519 sig verifies against the twin's pubkey (from the
//                   bones: card.json twin.pubkey, mirrored at keys/twin.pub).
//   3. CHAIN      — prevSha shape is well-formed (null genesis or 64-hex).
//
// Works from the bones alone — no private key required.

import fs from "node:fs";
import path from "node:path";
import { digestFrame, resolvePublicKey, verifyCanonical } from "./_frame.mjs";

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

for (const k of ["sha", "kind", "sig"]) {
  if (frame[k] === undefined) fail(`frame missing required field: ${k}`);
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

// 3. CHAIN — prevSha well-formed.
if (!(frame.prevSha === null || /^[0-9a-f]{64}$/.test(frame.prevSha || ""))) {
  fail(`chain: prevSha is neither null (genesis) nor a 64-hex sha: ${frame.prevSha}`);
}

// 2. AUTHENTICITY — signature verifies against the published pubkey.
let pub;
try {
  pub = resolvePublicKey();
} catch (e) {
  fail(`cannot resolve public key: ${e.message}`);
}
if (!verifyCanonical(canonical, frame.sig, pub)) {
  fail("authenticity: Ed25519 signature does not verify against the twin pubkey (tampered or wrong key)");
}

console.log("OK");
console.log(`  frame:   ${base}`);
console.log(`  kind:    ${frame.kind}`);
console.log(`  sha:     ${frame.sha}`);
console.log(`  prevSha: ${frame.prevSha ?? "(genesis)"}`);
console.log(`  twin@${sha.slice(0, 8)}  — integrity + signature verified`);
process.exit(0);
