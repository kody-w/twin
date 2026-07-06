// tools/pulse.mjs — regenerate feed.xml (Atom) from frames/ (§3/§4).
//
//   node tools/pulse.mjs
//
// The pulse is the twin's RSS/Atom-like broadcast: a static feed of signed,
// content-addressed frames served straight from the repo — no server, hydra-
// mirrorable. Edges subscribe, verify each frame (tools/verify-frame.mjs), and
// assimilate. This regenerates feed.xml deterministically from the frames/ dir.

import fs from "node:fs";
import path from "node:path";
import { REPO_ROOT, FRAMES_DIR, CARD_PATH, listFrameFiles, readFrameFile, sha8 } from "./_frame.mjs";

function xml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

// Frame `ts` is DAY precision (§13) — a bare `YYYY-MM-DD`. Atom requires an RFC3339
// date-time, so we render the day as midnight UTC: valid Atom, still zero sub-day info.
function toAtomDate(ts) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toISOString();
}

// Bones give us the feed identity (who / surfaces). All PII-free, already public.
let who = "the twin";
let gate = "https://kody-w.github.io/twin/";
let selfUrl = "https://kody-w.github.io/twin/feed.xml";
let rawBase = "https://raw.githubusercontent.com/kody-w/twin/main";
try {
  const card = JSON.parse(fs.readFileSync(CARD_PATH, "utf8"));
  who = card?.twin?.who || card?.meta?.author || who;
  const surf = (card?.twin?.surfaces || []).reduce((m, s) => ((m[s.kind] = s.url), m), {});
  gate = surf.gate || gate;
  selfUrl = surf.pulse || selfUrl;
} catch {}

const files = listFrameFiles();
if (files.length === 0) {
  console.error("no frames in frames/ — run: node tools/seed-frame.mjs");
  process.exit(2);
}

// Newest first (Atom convention).
const frames = files.map((f) => ({ file: f, frame: readFrameFile(path.join(FRAMES_DIR, f)) })).reverse();
const latestTs = toAtomDate(frames[0].frame.ts);
const year = new Date(latestTs).getUTCFullYear();

const entries = frames
  .map(({ file, frame }) => {
    const id = `tag:kody-w.github.io,${year}:twin/frame/${frame.sha}`;
    const title = `[${frame.kind}] twin@${sha8(frame.sha)}`;
    const rawUrl = `${rawBase}/frames/${file}`;
    const summary =
      `${frame.kind} frame, content-addressed twin@${sha8(frame.sha)}. ` +
      `prevSha ${frame.prevSha ? sha8(frame.prevSha) : "genesis"}. ` +
      `Ed25519-signed; verify with tools/verify-frame.mjs.`;
    // Embed the full signed frame as plain text so a subscriber can verify from the feed alone.
    const body = JSON.stringify(frame, null, 2);
    return `  <entry>
    <id>${xml(id)}</id>
    <title>${xml(title)}</title>
    <updated>${xml(toAtomDate(frame.ts))}</updated>
    <published>${xml(toAtomDate(frame.ts))}</published>
    <category term="${xml(frame.kind)}"/>
    <link rel="alternate" type="application/json" href="${xml(rawUrl)}"/>
    <summary type="text">${xml(summary)}</summary>
    <content type="text">${xml(body)}</content>
  </entry>`;
  })
  .join("\n");

const feed = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>the pulse — @kody-w/twin</title>
  <subtitle>A broadcast of signed, content-addressed frames. Static-only; trust the hash, not the host.</subtitle>
  <id>${xml(gate)}</id>
  <updated>${xml(latestTs)}</updated>
  <link rel="self" type="application/atom+xml" href="${xml(selfUrl)}"/>
  <link rel="alternate" type="text/html" href="${xml(gate)}"/>
  <author><name>${xml(who)}</name></author>
  <generator uri="https://github.com/kody-w/twin" version="1.0">tools/pulse.mjs</generator>
${entries}
</feed>
`;

const out = path.join(REPO_ROOT, "feed.xml");
fs.writeFileSync(out, feed);
console.log(`wrote feed.xml — ${frames.length} frame(s), latest twin@${sha8(frames[0].frame.sha)}`);
