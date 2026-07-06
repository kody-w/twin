// tools/verify-chain.mjs — walk ALL frames in order, print the key-history + verdict (§15).
//
//   node tools/verify-chain.mjs
//
// The single-frame verifier (verify-frame.mjs) answers "is THIS frame authentic?".
// This answers the estate question: "is the WHOLE public biography intact, and who
// holds the lead key now?" It replays every frame, verifying integrity + signatures,
// applies enroll/succession/rotate transitions, and prints the lead-key lineage:
//
//   genesis -> (rotate @seqN by quorum) -> ... -> effective key
//
// Exit 0 only if every frame verifies and every rotation cleared its quorum threshold.

import { resolveChain } from "./_chain.mjs";

const r = resolveChain();

if (r.fatal) {
  console.error(`FAIL: ${r.fatal}`);
  process.exit(1);
}

console.log(`pulse chain — ${r.frameCount} frame(s)`);
console.log("");
console.log("frames:");
for (const h of r.history) {
  const mark = h.ok ? "ok " : "XX ";
  const detail = h.detail ? `  — ${h.detail}` : "";
  console.log(`  ${mark}[${String(h.seq).padStart(2)}] ${h.kind.padEnd(11)} twin@${h.sha8}${detail}`);
  if (!h.ok) for (const e of h.errors) console.log(`        ! ${e}`);
}

console.log("");
console.log("lead-key history:");
for (const k of r.keyEvents) {
  if (k.kind === "genesis") {
    console.log(`  genesis          key ${k.fp}  (${k.detail})`);
  } else {
    console.log(`  rotate @${String(k.seq).padStart(2)} twin@${k.sha.slice(0, 8)}  key ${k.fp}`);
  }
}
console.log("");
console.log(`quorum: ${r.quorum.size} device(s) enrolled${r.policy ? `, policy ${r.policy.k}-of-${r.policy.n}` : ", no succession will yet"}`);
console.log(`effective lead key: ${r.effectiveKeyFp}`);
console.log("");

if (r.ok) {
  console.log(`VERDICT: OK — all ${r.frameCount} frame(s) verify; biography intact.`);
  process.exit(0);
} else {
  console.error(`VERDICT: FAIL — ${r.errors.length} problem(s):`);
  for (const e of r.errors) console.error(`  ${e.file}: ${e.msg}`);
  process.exit(1);
}
