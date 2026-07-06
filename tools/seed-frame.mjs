// tools/seed-frame.mjs — mint the genesis frame from the current bones (§3/§4).
//
//   node tools/seed-frame.mjs [--force]
//
// Frame 0 of the pulse: a content-addressed snapshot of the twin's current
// public bones (card.json, facets.json, holo.svg, ...). prevSha = null. This
// is "the twin's current bones" broadcast as the first heartbeat. Refuses to
// run if frames already exist (pass --force to reseed a fresh chain).

import fs from "node:fs";
import { FRAMES_DIR, listFrameFiles, buildSignedFrame, persistFrame, snapshotBones, sha8 } from "./_frame.mjs";

const force = process.argv.includes("--force");

if (listFrameFiles().length > 0 && !force) {
  console.error("frames/ already has frames — refusing to reseed (pass --force to start a new chain)");
  process.exit(2);
}
if (force) {
  for (const f of fs.readdirSync(FRAMES_DIR)) fs.rmSync(`${FRAMES_DIR}/${f}`);
}

const snap = snapshotBones();
const draft = {
  prevSha: null,
  kind: "seed",
  cart: {
    spec: "hologram-cartridge/1.0",
    note: "genesis pulse — the twin's current bones, content-addressed",
    ...snap,
  },
};

let built;
try {
  built = buildSignedFrame(draft);
} catch (e) {
  console.error(e.message);
  process.exit(2);
}
persistFrame(built);

console.log(`seeded frame 0 -> frames/${built.fileName}`);
console.log(`  sha:   ${built.sha}`);
console.log(`  twin@${sha8(built.sha)}  (genesis, prevSha=null)`);
console.log(`  bones: ${Object.keys(snap.bones).join(", ")}`);
console.log(`HEAD -> frames/${built.fileName}`);
