// tools/sign-frame.mjs — sign a draft frame into the pulse chain (§3/§4).
//
//   node tools/sign-frame.mjs <draft.json>
//
// A draft carries { kind, cart | delta } (+ optional prevSha, ts). This tool
// links it to frames/HEAD, content-addresses it (sha256 over the canonical
// core), signs the canonical bytes with the on-device key (keys/twin.key),
// writes frames/<seq>-<sha8>.json, and re-points frames/HEAD.
//
// The private key never leaves the device; only sha + sig travel in the bones.

import fs from "node:fs";
import { buildSignedFrame, persistFrame, sha8 } from "./_frame.mjs";

const draftPath = process.argv[2];
if (!draftPath) {
  console.error("usage: node tools/sign-frame.mjs <draft.json>");
  process.exit(2);
}

let draft;
try {
  draft = JSON.parse(fs.readFileSync(draftPath, "utf8"));
} catch (e) {
  console.error(`cannot read draft: ${e.message}`);
  process.exit(2);
}

let built;
try {
  built = buildSignedFrame(draft);
} catch (e) {
  console.error(e.message);
  process.exit(2);
}

persistFrame(built);

console.log(`signed frame ${built.seq} -> frames/${built.fileName}`);
console.log(`  sha:     ${built.sha}`);
console.log(`  prevSha: ${built.frame.prevSha ?? "(genesis)"}`);
console.log(`  twin@${sha8(built.sha)}  (content-addressed pulse id)`);
console.log(`HEAD -> frames/${built.fileName}`);
