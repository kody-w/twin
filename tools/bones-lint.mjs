// tools/bones-lint.mjs — privacy as CI (§13). Pattern-of-life is SOUL, not body.
//
//   node tools/bones-lint.mjs [--json] [--fix]
//
// A clean bones whitelist is not enough: over years, fine timestamps, precise coords, and
// emission bursts silently reconstruct a life from "public" frames. This linter is the
// mechanical enforcement of §13 — it FAILS (non-zero) the moment a public surface leaks
// soul. Scanned surfaces: frames/*.json, feed.xml, card.json, public-notes.json.
//
// Rules:
//   ts-precision  — a timestamp finer than DAY precision (any non-zero time-of-day).   [all surfaces]
//   geohash       — a geohash-like token >5 chars (precise location).                  [all surfaces]
//   pii-email     — an email address.                                                  [all surfaces]
//   pii-phone     — a phone-number pattern.                                            [all surfaces]
//   burst         — >3 frames sharing one calendar day (emission burst).               [frames]
//   key-whitelist — a frame carries a key outside the coarse public frame whitelist.   [frames]
//
// --fix quantizes frame timestamps in place: re-signs each affected frame to day precision
// (superseding originals into frames/attic/ — history is never destroyed, §3) and regenerates
// feed.xml. --json emits the machine-readable findings report only.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import {
  REPO_ROOT,
  FRAMES_DIR,
  CARD_PATH,
  listFrameFiles,
  readFrameFile,
  digestFrame,
  signCanonical,
  loadPrivateKey,
  quantizeDay,
  sha8,
  writeHead,
} from "./_frame.mjs";

const JSON_MODE = process.argv.includes("--json");
const FIX_MODE = process.argv.includes("--fix");

// §13 key policy. A public frame's STRUCTURE is fixed, but a body `delta` is open (visual genome,
// outfit, textures, splices, pairings — all legitimately public and unbounded). So:
//   - the frame ENVELOPE is a strict whitelist (nothing may ride alongside the known fields);
//   - the seed CART is a strict whitelist (a content-addressed snapshot has a fixed shape);
//   - a `delta` payload is open, but its keys are screened against a SOUL denylist — memories,
//     conversations, vault, agents, keys, contacts, locations, pattern-of-life. When in doubt,
//     a datum is soul. The universal value detectors (below) are the second line of defense.
const ENVELOPE_KEYS = new Set(["sha", "prevSha", "ts", "kind", "cart", "delta", "sig", "sigs"]);
const CART_KEYS = new Set(["spec", "note", "twinId", "rappid", "bones"]);
const SOUL_KEY = /^(?:.*_)?(memor(?:y|ies)|conversations?|chat|messages?|transcript|vault|agents?|soul|secrets?|password|passwd|token|apikey|privkey|mnemonic|seedphrase|locations?|geo|geohash|coords?|coordinates?|latitude|longitude|lat|lng|lon|address|contacts?|emails?|phones?|mobile|ssn|dob|birthday|calendar|schedule|session|cookie|gps|whereabouts|presence|lastseen|ip|ipaddr|logs?)$/i;

function isSoulKey(key) {
  const full = key.replace(/[^a-z0-9]/gi, "").toLowerCase();
  if (SOUL_KEY.test(full)) return true;
  for (const tok of key.split(/(?=[A-Z])|[_\-\s]+/)) if (tok && SOUL_KEY.test(tok.toLowerCase())) return true;
  return false;
}

// --- value detectors --------------------------------------------------------

// Opaque crypto/identity blobs — public keys, signatures, sha hashes, rappid hex — are
// PII-free by construction and are NOT pattern-of-life. Strip them before the location/PII
// detectors so a base64 pubkey run or a 32-hex rappid can't masquerade as a geohash or email.
function sanitizeForScan(text) {
  return String(text)
    .replace(/-----BEGIN[\s\S]*?-----END[^-]*-----/g, " ") // PEM key blocks
    .replace(/[A-Za-z0-9+/]{24,}={0,2}/g, " "); // base64 blobs, long hex (sha/rappid/DER)
}

// ISO datetime WITH a time-of-day component. A bare YYYY-MM-DD (day precision) is fine and
// is intentionally not matched. We flag any match whose H:M:S(.ms) is not exactly zero.
const ISO_DT = /\b(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:?\d{2})?/g;

function fineTimestamps(text) {
  const hits = [];
  for (const m of text.matchAll(ISO_DT)) {
    const [, , , , hh, mm, ss, frac, off] = m;
    const zeroTime = hh === "00" && mm === "00" && ss === "00" && (!frac || /^0+$/.test(frac));
    const zeroOff = !off || off === "Z" || /^[+-]00:?00$/.test(off);
    if (!(zeroTime && zeroOff)) hits.push(m[0]);
  }
  return hits;
}

// Geohash base32 alphabet excludes a, i, l, o. A precise geohash is digit-rich AND carries a
// g..z letter — that combination excludes sha hexes (no g..z), UUIDs, base64 sigs (mixed case,
// broken into short runs), and natural-language words ("current" has no digit).
const GEOHASH_LETTER = /[ghjkmnpqrstuvwxyz]/;
function geohashes(text) {
  const hits = [];
  for (const tok of text.split(/[^0-9a-z]+/)) {
    if (tok.length <= 5) continue;
    if (!/^[0-9bcdefghjkmnpqrstuvwxyz]+$/.test(tok)) continue; // pure geohash alphabet
    if (!/[0-9]/.test(tok)) continue; // digit-rich (excludes words)
    if (!GEOHASH_LETTER.test(tok)) continue; // has a g..z letter (excludes hex)
    hits.push(tok);
  }
  return hits;
}

const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
// Formatted phone (3-3-4 with separators/parens) OR E.164 (+ and 10-15 digits). Bare long
// integers (e.g. the summon seed) and hex are intentionally NOT matched.
const PHONE_FMT = /(?:\+\d{1,3}[\s.\-]?)?(?:\(\d{3}\)|\d{3})[\s.\-]\d{3}[\s.\-]\d{4}\b/g;
const PHONE_E164 = /\+\d{10,15}\b/g;

function emails(text) {
  return [...text.matchAll(EMAIL)].map((m) => m[0]);
}
function phones(text) {
  return [...text.matchAll(PHONE_FMT)].map((m) => m[0]).concat([...text.matchAll(PHONE_E164)].map((m) => m[0]));
}

// --- scanners ---------------------------------------------------------------

function pushValueFindings(text, file, findings, loc) {
  const clean = sanitizeForScan(text);
  for (const s of fineTimestamps(text)) findings.push({ file, rule: "ts-precision", detail: `timestamp finer than day precision${loc ? ` at ${loc}` : ""}`, sample: s });
  for (const s of geohashes(clean)) findings.push({ file, rule: "geohash", detail: `geohash-like token >5 chars${loc ? ` at ${loc}` : ""}`, sample: s });
  for (const s of emails(clean)) findings.push({ file, rule: "pii-email", detail: `email address${loc ? ` at ${loc}` : ""}`, sample: s });
  for (const s of phones(clean)) findings.push({ file, rule: "pii-phone", detail: `phone-number pattern${loc ? ` at ${loc}` : ""}`, sample: s });
}

// Recursively scan a JSON value's STRING content with the universal value detectors.
function scanValues(v, file, findings, loc) {
  if (typeof v === "string") return pushValueFindings(v, file, findings, loc);
  if (Array.isArray(v)) return v.forEach((item, i) => scanValues(item, file, findings, `${loc}[${i}]`));
  if (v && typeof v === "object") for (const [k, val] of Object.entries(v)) scanValues(val, file, findings, `${loc}.${k}`);
}

// Scan a FRAME object: envelope + cart are strict whitelists; delta is soul-screened; all string
// values everywhere get the universal detectors. `mode` ∈ envelope | cart | delta | skip.
function scanFrameKeys(v, file, findings, loc, mode) {
  if (v === null || typeof v !== "object") return;
  if (Array.isArray(v)) {
    v.forEach((item, i) => scanFrameKeys(item, file, findings, `${loc}[${i}]`, mode));
    return;
  }
  for (const [k, val] of Object.entries(v)) {
    let childMode = mode;
    if (mode === "envelope") {
      if (!ENVELOPE_KEYS.has(k)) findings.push({ file, rule: "key-whitelist", detail: `frame envelope key not in the public whitelist at ${loc}`, sample: k });
      childMode = k === "cart" ? "cart" : k === "delta" ? "delta" : k === "sigs" ? "skip" : "envelope";
    } else if (mode === "cart") {
      if (!CART_KEYS.has(k)) findings.push({ file, rule: "key-whitelist", detail: `cart key not in the public snapshot whitelist at ${loc}`, sample: k });
      childMode = k === "bones" ? "skip" : "cart";
    } else if (mode === "delta") {
      if (isSoulKey(k)) findings.push({ file, rule: "key-whitelist", detail: `delta key looks like SOUL, not body (§13) at ${loc}`, sample: k });
      childMode = "delta";
    }
    scanFrameKeys(val, file, findings, `${loc}.${k}`, childMode);
  }
}

function scanFrame(frame, file, findings) {
  scanFrameKeys(frame, file, findings, "frame", "envelope");
  scanValues(frame, file, findings, "frame");
}

function lint() {
  const findings = [];

  // frames/*.json — key policy + value detectors + burst.
  const frameFiles = listFrameFiles();
  const perDay = new Map();
  for (const f of frameFiles) {
    let frame;
    try {
      frame = readFrameFile(path.join(FRAMES_DIR, f));
    } catch (e) {
      findings.push({ file: `frames/${f}`, rule: "unreadable", detail: e.message, sample: "" });
      continue;
    }
    scanFrame(frame, `frames/${f}`, findings);
    const day = quantizeDay(frame.ts);
    if (!perDay.has(day)) perDay.set(day, []);
    perDay.get(day).push(f);
  }
  for (const [day, fs_] of perDay) {
    if (fs_.length > 3) {
      findings.push({ file: "frames/", rule: "burst", detail: `${fs_.length} frames share calendar day ${day} (>3 = emission burst)`, sample: fs_.join(",") });
    }
  }

  // card.json, public-notes.json — value detectors only (rich identity cards are allowed keys).
  for (const rel of ["card.json", "public-notes.json"]) {
    const p = path.join(REPO_ROOT, rel);
    if (!fs.existsSync(p)) continue;
    try {
      scanValues(JSON.parse(fs.readFileSync(p, "utf8")), rel, findings, rel.replace(/\.json$/, ""));
    } catch (e) {
      findings.push({ file: rel, rule: "unreadable", detail: e.message, sample: "" });
    }
  }

  // feed.xml — value detectors over the raw text.
  const feedPath = path.join(REPO_ROOT, "feed.xml");
  if (fs.existsSync(feedPath)) {
    pushValueFindings(fs.readFileSync(feedPath, "utf8"), "feed.xml", findings, "");
  }

  return findings;
}

// --- --fix: quantize + re-sign frames, regenerate feed ----------------------

function atticNote() {
  const dir = path.join(FRAMES_DIR, "attic");
  fs.mkdirSync(dir, { recursive: true });
  const readme = path.join(dir, "README.md");
  if (!fs.existsSync(readme)) {
    fs.writeFileSync(
      readme,
      "# frames/attic — superseded originals\n\n" +
        "History is never destroyed (§3). These are the pre-quantization originals of frames that\n" +
        "were re-signed to DAY-precision timestamps to satisfy the §13 privacy body (bones-lint).\n" +
        "They remain byte-for-byte so any prior state is auditable and revertible; they are NOT part\n" +
        "of the live chain (verify-chain / pulse ignore this directory).\n"
    );
  }
  return dir;
}

function fixFrames() {
  const files = listFrameFiles();
  const leadKey = loadPrivateKey();
  const changed = [];
  const skipped = [];
  let prevSha = null;
  let head = null;

  for (const file of files) {
    const seq = parseInt(file, 10);
    const frame = readFrameFile(path.join(FRAMES_DIR, file));
    const newTs = quantizeDay(frame.ts);
    const needs = newTs !== frame.ts || prevSha !== frame.prevSha;

    if (Array.isArray(frame.sigs)) {
      // Multisig (rotate) frames cannot be re-signed here — that needs the quorum's device keys.
      if (needs) skipped.push(file);
      prevSha = frame.sha;
      head = { seq, sha: frame.sha, frame: file, ts: frame.ts };
      continue;
    }
    if (!needs) {
      prevSha = frame.sha;
      head = { seq, sha: frame.sha, frame: file, ts: newTs };
      continue;
    }

    const core = { prevSha, ts: newTs, kind: frame.kind };
    if (frame.cart !== undefined) core.cart = frame.cart;
    if (frame.delta !== undefined) core.delta = frame.delta;
    const { canonical, sha } = digestFrame(core);
    const sig = signCanonical(canonical, leadKey);
    const newFrame = { sha, ...core, sig };
    const newFile = `${seq}-${sha8(sha)}.json`;

    const dir = atticNote();
    fs.renameSync(path.join(FRAMES_DIR, file), path.join(dir, file));
    fs.writeFileSync(path.join(FRAMES_DIR, newFile), JSON.stringify(newFrame, null, 2) + "\n");

    changed.push({ from: file, to: newFile });
    prevSha = sha;
    head = { seq, sha, frame: newFile, ts: newTs };
  }

  if (head) writeHead(head);
  // Regenerate feed.xml from the fixed frames (inherits TWIN_ROOT).
  const pulse = fileURLToPath(new URL("./pulse.mjs", import.meta.url));
  try {
    execFileSync(process.execPath, [pulse], { stdio: "ignore", env: process.env });
  } catch {}
  return { changed, skipped };
}

// --- run --------------------------------------------------------------------

let fixResult = null;
if (FIX_MODE) fixResult = fixFrames();

const findings = lint();
const ok = findings.length === 0;

if (JSON_MODE) {
  console.log(JSON.stringify({ ok, scanned: ["frames/*.json", "feed.xml", "card.json", "public-notes.json"], fix: fixResult, findings }, null, 2));
} else {
  if (fixResult) {
    for (const c of fixResult.changed) console.log(`fixed: re-signed ${c.from} -> ${c.to} (attic'd original)`);
    for (const s of fixResult.skipped) console.log(`skip:  ${s} is a multisig frame — re-sign via quorum, not --fix`);
    if (fixResult.changed.length === 0 && fixResult.skipped.length === 0) console.log("fix: nothing to quantize");
  }
  if (ok) {
    console.log("bones-lint OK — no pattern-of-life leaks (§13). Scanned frames/, feed.xml, card.json, public-notes.json.");
  } else {
    console.error(`bones-lint FAIL — ${findings.length} finding(s):`);
    for (const f of findings) console.error(`  [${f.rule}] ${f.file}: ${f.detail}  ~ ${JSON.stringify(f.sample)}`);
  }
}

process.exit(ok ? 0 : 1);
