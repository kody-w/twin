// tools/_chain.mjs — resolve the EFFECTIVE signing key by walking the pulse chain (§15).
//
// The lead key is not eternal. §15: key loss ≠ twin death — the owner's enrolled
// devices ARE the recovery quorum, and a `rotate` frame signed by ≥k of them advances
// the twin to a new lead key. So "which key is authoritative right now?" is answered by
// replaying the public chain, never by trusting a single stored key:
//
//   effectiveKey  := card.json pubkey (genesis lead)
//   for each frame in order:
//     enroll      (sig by lead)              -> add device to the quorum
//     succession  (sig by lead)              -> set the recovery policy (k-of-n) — the public will
//     rotate      (sigs[] by ≥k quorum keys) -> effectiveKey := newKey   (the recovery event)
//     seed|delta  (sig by lead)              -> body change, no key change
//
// A rotate whose multisig does NOT clear the quorum threshold is REJECTED: the key does
// not advance, and the failure is recorded. Signature ≠ authority unless the quorum agrees.

import {
  FRAMES_DIR,
  listFrameFiles,
  readFrameFile,
  digestFrame,
  verifyCanonical,
  resolvePublicKey,
  toPublicKey,
  keyFingerprint,
  sha8,
} from "./_frame.mjs";
import path from "node:path";

// "2-of-3" | {k,n} -> {k,n}
export function parsePolicy(p) {
  if (p && typeof p === "object" && Number.isInteger(p.k)) return { k: p.k, n: p.n ?? null };
  const m = String(p).match(/^(\d+)\s*-?of-?\s*(\d+)$/i);
  if (!m) throw new Error(`unparseable policy: ${p} (expected "k-of-n")`);
  return { k: Number(m[1]), n: Number(m[2]) };
}

// Verify one frame's integrity + authenticity given the key context in force at its position.
// Returns { ok, errors[], keyChange? } and never throws.
function verifyFrameAt(frame, { effectiveKey, quorum, policy }) {
  const errors = [];
  const { canonical, sha } = digestFrame(frame);

  if (sha !== frame.sha) {
    errors.push(`integrity: recomputed sha ${sha8(sha)} != frame.sha ${sha8(frame.sha)} (tampered)`);
    return { ok: false, errors, canonical };
  }
  if (!(frame.prevSha === null || /^[0-9a-f]{64}$/.test(frame.prevSha || ""))) {
    errors.push(`chain: prevSha is neither null nor 64-hex: ${frame.prevSha}`);
  }

  if (frame.kind === "rotate") {
    if (!Array.isArray(frame.sigs) || frame.sigs.length === 0) {
      errors.push("rotate: missing multisig `sigs[]` — a rotation must be signed by the quorum");
      return { ok: false, errors, canonical };
    }
    const kRequired = policy ? policy.k : quorum.size; // no will yet => unanimous among enrolled
    if (quorum.size === 0) {
      errors.push("rotate: no devices enrolled — the quorum is empty, nothing can authorize a rotation");
      return { ok: false, errors, canonical };
    }
    const seen = new Set();
    let valid = 0;
    for (const entry of frame.sigs) {
      const dev = entry?.device;
      if (!dev || !quorum.has(dev)) {
        errors.push(`rotate: signer "${dev}" is not an enrolled device`);
        continue;
      }
      if (seen.has(dev)) continue; // no double-counting one device
      if (verifyCanonical(canonical, entry.sig, quorum.get(dev))) {
        seen.add(dev);
        valid++;
      } else {
        errors.push(`rotate: signature by "${dev}" does not verify`);
      }
    }
    if (valid < Math.max(1, kRequired)) {
      errors.push(`rotate: only ${valid} valid device signature(s), policy requires ${Math.max(1, kRequired)}`);
      return { ok: false, errors, canonical };
    }
    let newKey;
    try {
      newKey = toPublicKey(frame.delta?.newKey);
    } catch (e) {
      errors.push(`rotate: unusable newKey — ${e.message}`);
      return { ok: false, errors, canonical };
    }
    return { ok: errors.length === 0, errors, canonical, keyChange: { newKey, by: [...seen], kRequired } };
  }

  // Single-sig frames (seed, enroll, succession, body deltas) are signed by the lead key.
  if (typeof frame.sig !== "string") {
    errors.push(`${frame.kind}: missing single signature \`sig\``);
    return { ok: false, errors, canonical };
  }
  if (!verifyCanonical(canonical, frame.sig, effectiveKey)) {
    errors.push(`${frame.kind}: Ed25519 signature does not verify against the effective lead key`);
    return { ok: false, errors, canonical };
  }
  return { ok: errors.length === 0, errors, canonical };
}

// Walk the whole chain. Returns a full report; verifies every frame as it goes.
// Operates on FRAMES_DIR / card.json, both of which honor TWIN_ROOT — so a ceremony
// in a throwaway temp twin resolves against that twin, never the live bones.
export function resolveChain() {
  const framesDir = FRAMES_DIR;
  const files = listFrameFiles();

  let effectiveKey;
  try {
    effectiveKey = resolvePublicKey();
  } catch (e) {
    return { ok: false, fatal: `cannot resolve genesis key: ${e.message}`, history: [], errors: [] };
  }
  const genesisFp = keyFingerprint(effectiveKey);

  const quorum = new Map();
  let policy = null;
  const history = [];
  const errors = [];
  const keyEvents = [{ seq: -1, kind: "genesis", sha: null, fp: genesisFp, detail: "card.json pubkey" }];
  let prevSha = null;
  let ok = true;

  files.forEach((file, seq) => {
    let frame;
    try {
      frame = readFrameFile(path.join(framesDir, file));
    } catch (e) {
      ok = false;
      errors.push({ file, msg: `unreadable/invalid JSON: ${e.message}` });
      return;
    }

    const res = verifyFrameAt(frame, { effectiveKey, quorum, policy });
    const entry = {
      seq,
      file,
      kind: frame.kind,
      sha8: sha8(frame.sha),
      ok: res.ok,
      keyFp: keyFingerprint(effectiveKey),
      errors: res.errors,
    };

    // chain linkage check
    if (frame.prevSha !== prevSha) {
      entry.ok = false;
      res.errors.push(`chain: prevSha ${frame.prevSha ? sha8(frame.prevSha) : "null"} != expected ${prevSha ? sha8(prevSha) : "null"}`);
    }

    if (!entry.ok) ok = false;

    // Apply state transitions only for frames that verified.
    if (res.ok) {
      if (frame.kind === "enroll") {
        try {
          quorum.set(frame.delta.device, toPublicKey(frame.delta.pubkey));
          entry.detail = `enrolled device "${frame.delta.device}" (quorum size ${quorum.size})`;
        } catch (e) {
          entry.ok = false;
          ok = false;
          res.errors.push(`enroll: unusable device pubkey — ${e.message}`);
        }
      } else if (frame.kind === "succession") {
        try {
          policy = parsePolicy(frame.delta.policy);
          entry.detail = `will set: recovery policy ${policy.k}-of-${policy.n}, heirs=${(frame.delta.heirs || []).length}`;
        } catch (e) {
          entry.ok = false;
          ok = false;
          res.errors.push(`succession: ${e.message}`);
        }
      } else if (frame.kind === "rotate" && res.keyChange) {
        effectiveKey = res.keyChange.newKey;
        const fp = keyFingerprint(effectiveKey);
        entry.detail = `ROTATED lead key -> ${fp} (${res.keyChange.by.length}-of-${quorum.size} by ${res.keyChange.by.join(", ")})`;
        keyEvents.push({ seq, kind: "rotate", sha: frame.sha, fp, detail: entry.detail });
      }
    }

    for (const m of res.errors) errors.push({ file, msg: m });
    history.push(entry);
    prevSha = frame.sha;
  });

  return {
    ok,
    history,
    keyEvents,
    errors,
    effectiveKey,
    effectiveKeyFp: keyFingerprint(effectiveKey),
    quorum,
    policy,
    frameCount: files.length,
  };
}
