// tools/_frame.mjs — shared pulse primitives (zero npm deps, Node crypto only).
//
// A pulse frame is the atomic unit the public twin broadcasts. It is content-
// addressed (sha256 over its canonical form) and signed by the on-device twin
// (Ed25519). Edges verify integrity (sha) and authenticity (sig) before they
// assimilate — the exact `/resolver` hash-trust pattern, PKI-free for integrity.
//
//   frame = { sha, prevSha, ts, kind, cart|delta, sig, ... }
//
// canonical(frame\{sha,sig}) -> sha256 hex  (integrity: verify-before-act)
// Ed25519.sign(canonical bytes)             -> sig  (authenticity, optional L2)

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// REPO_ROOT is the twin's root. It defaults to the repo this file lives in, but
// TWIN_ROOT overrides it so a ceremony can run against a throwaway twin in a temp
// dir (estate-selftest) without ever touching the live bones or the real key.
export const REPO_ROOT = process.env.TWIN_ROOT
  ? path.resolve(process.env.TWIN_ROOT)
  : path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const KEYS_DIR = path.join(REPO_ROOT, "keys");
export const FRAMES_DIR = path.join(REPO_ROOT, "frames");
export const CARD_PATH = path.join(REPO_ROOT, "card.json");
export const PRIV_PATH = path.join(KEYS_DIR, "twin.key");
export const PUB_PATH = path.join(KEYS_DIR, "twin.pub");

// Deterministic JSON: recursively sort object keys. This is `canonical(frame)`
// from rapp-frame/2.0 — the same bytes on every machine, so the sha is stable.
export function canonicalize(v) {
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(canonicalize).join(",") + "]";
  const keys = Object.keys(v).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalize(v[k])).join(",") + "}";
}

// The signed/hashed core = every frame field EXCEPT sha and the signatures.
// Signatures (single `sig`, or the `sigs[]` multisig array on rotate frames)
// sign the canonical core, so they can never be inside it.
export function frameCore(frame) {
  const { sha, sig, sigs, ...core } = frame;
  return core;
}

// Returns { canonical, sha } for a frame object.
export function digestFrame(frame) {
  const canonical = canonicalize(frameCore(frame));
  const sha = crypto.createHash("sha256").update(canonical, "utf8").digest("hex");
  return { canonical, sha };
}

export function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

export function loadPrivateKey() {
  if (!fs.existsSync(PRIV_PATH)) {
    throw new Error(`missing private key ${PRIV_PATH} — run: node tools/keygen.mjs`);
  }
  return crypto.createPrivateKey(fs.readFileSync(PRIV_PATH, "utf8"));
}

// Load a private/public key from an arbitrary PEM file (device keys, heirs, new keys).
export function loadPrivateKeyFrom(p) {
  return crypto.createPrivateKey(fs.readFileSync(p, "utf8"));
}
export function loadPublicKeyFrom(p) {
  return crypto.createPublicKey(fs.readFileSync(p, "utf8"));
}

// A stable short fingerprint of a public key (sha256 of its raw SPKI DER, first 8 hex).
// Used to print human-readable key history without leaking anything private.
export function keyFingerprint(publicKey) {
  const ko = publicKey && publicKey.asymmetricKeyType ? publicKey : crypto.createPublicKey(publicKey);
  const der = ko.export({ type: "spki", format: "der" });
  return crypto.createHash("sha256").update(der).digest("hex").slice(0, 16);
}

// Normalize any public-key representation (PEM string, raw base64, KeyObject) to a KeyObject.
export function toPublicKey(rep) {
  if (rep && typeof rep === "object" && rep.asymmetricKeyType) return rep; // already a KeyObject
  const s = String(rep).trim();
  if (s.includes("BEGIN PUBLIC KEY")) return crypto.createPublicKey(s);
  // raw 32-byte Ed25519 public key, base64 -> wrap in SPKI DER.
  const raw = Buffer.from(s, "base64");
  if (raw.length === 32) {
    const spki = Buffer.concat([Buffer.from("302a300506032b6570032100", "hex"), raw]);
    return crypto.createPublicKey({ key: spki, format: "der", type: "spki" });
  }
  throw new Error("unrecognized public key representation");
}

// The public key ships in the bones: card.json is the source of truth, keys/twin.pub
// is a convenience mirror. Verify works from bones alone (no private key needed).
export function resolvePublicKey() {
  try {
    const card = JSON.parse(fs.readFileSync(CARD_PATH, "utf8"));
    const pem = card?.twin?.pubkey?.pem;
    if (pem) return crypto.createPublicKey(pem);
  } catch {}
  if (fs.existsSync(PUB_PATH)) return crypto.createPublicKey(fs.readFileSync(PUB_PATH, "utf8"));
  throw new Error("no public key found in card.json (twin.pubkey.pem) or keys/twin.pub");
}

export function signCanonical(canonical, privateKey) {
  return crypto.sign(null, Buffer.from(canonical, "utf8"), privateKey).toString("base64");
}

export function verifyCanonical(canonical, sigB64, publicKey) {
  try {
    return crypto.verify(null, Buffer.from(canonical, "utf8"), publicKey, Buffer.from(sigB64, "base64"));
  } catch {
    return false;
  }
}

export function sha8(sha) {
  return sha.slice(0, 8);
}

// §13 pattern-of-life guard: public frame timestamps are DAY-precision only —
// a years-long history must not reconstruct a life. A day stamp is the bare
// calendar date `YYYY-MM-DD` (no time-of-day, self-evidently coarse). The feed
// renders it as a valid RFC3339 instant (midnight UTC) at broadcast time.
export function quantizeDay(ts) {
  const d = ts ? new Date(ts) : new Date();
  if (Number.isNaN(d.getTime())) {
    // Already a bare YYYY-MM-DD (or garbage we won't touch) — keep first 10 chars if date-shaped.
    return /^\d{4}-\d{2}-\d{2}/.test(String(ts)) ? String(ts).slice(0, 10) : String(ts);
  }
  return d.toISOString().slice(0, 10);
}

export function dayStamp() {
  return quantizeDay(new Date());
}

// frames/HEAD is the pointer at the latest frame (self-describing JSON).
export function readHead() {
  const p = path.join(FRAMES_DIR, "HEAD");
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch {
    return null;
  }
}

export function writeHead(head) {
  fs.writeFileSync(path.join(FRAMES_DIR, "HEAD"), JSON.stringify(head, null, 2) + "\n");
}

// List frame files (excluding HEAD), sorted by numeric <seq> prefix ascending.
export function listFrameFiles() {
  if (!fs.existsSync(FRAMES_DIR)) return [];
  return fs
    .readdirSync(FRAMES_DIR)
    .filter((f) => /^\d+-[0-9a-f]{8}\.json$/.test(f))
    .sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
}

export function readFrameFile(fp) {
  return JSON.parse(fs.readFileSync(fp, "utf8"));
}

// Assemble the unsigned core of a frame from a draft { kind, cart|delta, prevSha?, ts? }.
// Links to frames/HEAD unless the draft pins prevSha. §13: ts is always quantized to
// DAY precision. Returns everything needed to sign — single-sig or multisig — without
// requiring any private key, so multi-device rotate frames can share this path.
export function buildFrameCore(draft) {
  if (!draft.kind) throw new Error("draft is missing required field: kind");
  if (draft.cart === undefined && draft.delta === undefined) {
    throw new Error("draft must carry either `cart` (a bones snapshot) or `delta` (a change)");
  }
  const head = readHead();
  const seq = head ? head.seq + 1 : 0;
  const prevSha = Object.prototype.hasOwnProperty.call(draft, "prevSha")
    ? draft.prevSha
    : head
    ? head.sha
    : null;
  const ts = quantizeDay(draft.ts);

  // Frame shape (brief §3): { sha, prevSha, ts, kind, cart|delta, sig }.
  const core = { prevSha, ts, kind: draft.kind };
  if (draft.cart !== undefined) core.cart = draft.cart;
  if (draft.delta !== undefined) core.delta = draft.delta;

  const { canonical, sha } = digestFrame(core);
  return { core, canonical, sha, seq, prevSha, ts, fileName: `${seq}-${sha8(sha)}.json` };
}

// Build a signed frame object from a draft { kind, cart|delta, prevSha?, ts? }.
// Links to frames/HEAD unless the draft pins prevSha. Requires the private key.
export function buildSignedFrame(draft) {
  const built = buildFrameCore(draft);
  const sig = signCanonical(built.canonical, loadPrivateKey());
  const frame = { sha: built.sha, ...built.core, sig };
  return { frame, seq: built.seq, sha: built.sha, canonical: built.canonical, fileName: built.fileName };
}

// Build a rotate/multisig frame: the core is signed by an array of device keys.
// `signers` = [{ device, key }] where key is a Node KeyObject (private). The frame
// carries `sigs: [{ device, sig }]` and NO single `sig` — its authority is the quorum
// (§15: the owner's enrolled devices ARE the recovery quorum), not the (lost) lead key.
export function buildMultiSigFrame(draft, signers) {
  const built = buildFrameCore(draft);
  const sigs = signers.map(({ device, key }) => ({
    device,
    sig: signCanonical(built.canonical, key),
  }));
  const frame = { sha: built.sha, ...built.core, sigs };
  return { frame, seq: built.seq, sha: built.sha, canonical: built.canonical, fileName: built.fileName };
}

// Persist a built frame to frames/<seq>-<sha8>.json and re-point frames/HEAD.
export function persistFrame(built) {
  fs.mkdirSync(FRAMES_DIR, { recursive: true });
  const outPath = path.join(FRAMES_DIR, built.fileName);
  fs.writeFileSync(outPath, JSON.stringify(built.frame, null, 2) + "\n");
  writeHead({ seq: built.seq, sha: built.sha, frame: built.fileName, ts: built.frame.ts });
  return outPath;
}

// Snapshot the twin's current bones (published, PII-free) as a content-addressed
// manifest — the payload of the seed frame. Generic: hashes whichever bone files
// exist in the repo root.
export function snapshotBones() {
  const boneNames = ["card.json", "facets.json", "holo.svg", "holo.md", "members.json", "soul.md", "public-notes.json"];
  const bones = {};
  for (const name of boneNames) {
    const p = path.join(REPO_ROOT, name);
    if (fs.existsSync(p)) bones[name] = sha256Hex(fs.readFileSync(p));
  }
  let twinId = null;
  let rappid = null;
  try {
    const card = JSON.parse(fs.readFileSync(CARD_PATH, "utf8"));
    twinId = card?.twin?.twinId ?? null;
    rappid = card?.twin?.rappid ?? card?.meta?.rappid ?? null;
  } catch {}
  return { twinId, rappid, bones };
}
