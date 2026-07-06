// tools/shamir.mjs — Shamir k-of-n secret sharing over GF(256). Zero deps (§15).
//
//   import { split, combine, encodeShard, decodeShard, selftest } from "./shamir.mjs";
//   node tools/shamir.mjs --selftest
//
// The estate's recovery math. The twin's private key is split into n shards such that ANY k
// reconstruct it and any k-1 reveal NOTHING (information-theoretic, not merely hard). This is
// the mechanism behind §15: the key can live in a safe, a will, and a trusted heir's hands at
// once, and no single custodian — or thief — holds the twin.
//
// GF(256) with the AES reducing polynomial 0x11b. CRITICAL: the sharing polynomial's secret
// coefficients come from crypto.randomBytes — never Math.random — or the secrecy is a fiction.

import crypto from "node:crypto";

// --- GF(256) arithmetic (AES field, reducing poly 0x11b, generator 3) -------
const EXP = new Uint8Array(512);
const LOG = new Uint8Array(256);
(function buildTables() {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP[i] = x;
    LOG[x] = i;
    // multiply x by the generator 3 = (x<<1) ^ x, reduce by 0x11b if it overflows GF(256).
    let hi = x & 0x80;
    x = (x << 1) & 0xff;
    if (hi) x ^= 0x1b;
    x ^= EXP[i]; // times (1) — makes the generator 3 rather than 2
  }
  for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
})();

function gfMul(a, b) {
  if (a === 0 || b === 0) return 0;
  return EXP[LOG[a] + LOG[b]];
}
function gfDiv(a, b) {
  if (b === 0) throw new Error("gfDiv by zero");
  if (a === 0) return 0;
  return EXP[LOG[a] + 255 - LOG[b]];
}

// Evaluate polynomial (coeffs low->high) at x in GF(256) via Horner.
function gfEval(coeffs, x) {
  let acc = 0;
  for (let i = coeffs.length - 1; i >= 0; i--) acc = gfMul(acc, x) ^ coeffs[i];
  return acc;
}

// --- split / combine --------------------------------------------------------

// split(secret: Buffer|Uint8Array, n, k) -> [{ x, y: Buffer }] (n shards; any k reconstruct).
export function split(secret, n, k) {
  secret = Buffer.from(secret);
  if (!Number.isInteger(k) || !Number.isInteger(n)) throw new Error("n and k must be integers");
  if (k < 1) throw new Error("k must be >= 1");
  if (n < k) throw new Error("n must be >= k");
  if (n > 255) throw new Error("n must be <= 255 (GF(256) has 255 nonzero points)");

  const shards = [];
  for (let i = 1; i <= n; i++) shards.push({ x: i, y: Buffer.alloc(secret.length) });

  for (let b = 0; b < secret.length; b++) {
    // Random degree-(k-1) polynomial: constant term = secret byte, rest are SECRET randomness.
    const coeffs = Buffer.alloc(k);
    coeffs[0] = secret[b];
    if (k > 1) crypto.randomBytes(k - 1).copy(coeffs, 1);
    for (let i = 0; i < n; i++) shards[i].y[b] = gfEval(coeffs, shards[i].x);
  }
  return shards;
}

// combine(shards: [{x,y}]) -> Buffer. Uses Lagrange interpolation at x=0. Needs >= k distinct
// shards; supplying fewer, or a corrupted/foreign shard, yields the WRONG secret (by design —
// there is no "partially right"). Callers that can verify the result (e.g. a re-derived pubkey)
// should always do so.
export function combine(shards) {
  if (!shards || shards.length === 0) throw new Error("no shards");
  const len = shards[0].y.length;
  const xs = shards.map((s) => s.x);
  if (new Set(xs).size !== xs.length) throw new Error("duplicate shard x-coordinates");

  const out = Buffer.alloc(len);
  for (let b = 0; b < len; b++) {
    let acc = 0;
    for (let j = 0; j < shards.length; j++) {
      // Lagrange basis_j at x=0 = Π_{m!=j} x_m / (x_j - x_m)   (subtraction is xor in GF).
      let basis = 1;
      for (let m = 0; m < shards.length; m++) {
        if (m === j) continue;
        basis = gfMul(basis, gfDiv(xs[m], xs[j] ^ xs[m]));
      }
      acc ^= gfMul(shards[j].y[b], basis);
    }
    out[b] = acc;
  }
  return out;
}

// --- shard text encoding (QR- and print-friendly) ---------------------------
// tks1.<k>.<n>.<x>.<hexY>   — magic "tks1" = twin key shard, version 1.
const MAGIC = "tks1";

export function encodeShard(shard, k, n) {
  return `${MAGIC}.${k}.${n}.${shard.x}.${shard.y.toString("hex")}`;
}

export function decodeShard(line) {
  const parts = String(line).trim().split(".");
  if (parts[0] !== MAGIC || parts.length !== 5) throw new Error(`not a ${MAGIC} shard line`);
  const [, kk, nn, xx, hex] = parts;
  if (!/^[0-9a-f]*$/.test(hex) || hex.length % 2 !== 0) throw new Error("bad shard hex payload");
  return { k: Number(kk), n: Number(nn), x: Number(xx), y: Buffer.from(hex, "hex") };
}

// --- self-test --------------------------------------------------------------
export function selftest() {
  const results = [];
  const check = (name, cond) => {
    results.push({ name, pass: !!cond });
    return !!cond;
  };

  // GF sanity — classic AES-field vector 0x53 * 0xCA = 0x01, plus identities.
  check("gf: 0x53*0xCA==0x01", gfMul(0x53, 0xca) === 0x01);
  check("gf: a*1==a", gfMul(0xab, 1) === 0xab);
  check("gf: a*0==0", gfMul(0xab, 0) === 0);
  check("gf: div inverts mul", gfDiv(gfMul(0x2f, 0x77), 0x77) === 0x2f);

  // Deterministic Lagrange vector (fixed shares, no randomness): secret=0x42, k=2, a1=0x1b.
  {
    const s0 = 0x42, a1 = 0x1b;
    const pts = [1, 2, 3].map((x) => ({ x, y: Buffer.from([s0 ^ gfMul(a1, x)]) }));
    check("lagrange: any 2 of 3 recover 0x42", combine([pts[0], pts[2]])[0] === 0x42 && combine([pts[1], pts[2]])[0] === 0x42);
  }

  // Roundtrip on a real-sized secret with randomness.
  {
    const secret = crypto.randomBytes(48);
    const shards = split(secret, 5, 3);
    check("roundtrip: exactly k=3 shards", combine([shards[0], shards[2], shards[4]]).equals(secret));
    check("roundtrip: a different k-subset", combine([shards[1], shards[3], shards[4]]).equals(secret));
    check("roundtrip: all n shards", combine(shards).equals(secret));
    // Fewer than k reconstructs the WRONG value (not the secret).
    check("safety: k-1 shards do NOT recover", !combine([shards[0], shards[1]]).equals(secret));
    // A corrupted/foreign shard poisons the result (distinct x, tampered payload).
    const corrupted = { x: shards[2].x, y: Buffer.from(shards[2].y) };
    corrupted.y[0] ^= 0xff;
    check("safety: a corrupted shard yields wrong secret", !combine([shards[0], shards[1], corrupted]).equals(secret));
    // Encode/decode roundtrip.
    const line = encodeShard(shards[0], 3, 5);
    const dec = decodeShard(line);
    check("encode/decode: shard survives text form", dec.x === shards[0].x && dec.y.equals(shards[0].y));
  }

  const pass = results.every((r) => r.pass);
  return { pass, results };
}

// CLI: --selftest
if (import.meta.url === `file://${process.argv[1]}`) {
  if (process.argv.includes("--selftest")) {
    const { pass, results } = selftest();
    for (const r of results) console.log(`  ${r.pass ? "PASS" : "FAIL"}  ${r.name}`);
    console.log(pass ? "shamir selftest: ALL PASS" : "shamir selftest: FAIL");
    process.exit(pass ? 0 : 1);
  } else {
    console.log("usage: node tools/shamir.mjs --selftest");
  }
}
