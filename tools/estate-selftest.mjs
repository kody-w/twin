// tools/estate-selftest.mjs — one command that proves the whole estate works (§13 + §15).
//
//   node tools/estate-selftest.mjs
//
// Everything runs on THROWAWAY keys in temp dirs (TWIN_ROOT) — the live bones and the real
// private key are never touched. Checks:
//   1. shamir  — split→combine roundtrip incl. wrong-shard failure (via shamir.selftest()).
//   2. estate  — keygen → seed → enroll×3 → succession(2-of-3) → rotate(2 devices) → verify-chain,
//                the reconstructed key MATCHES the rotated pubkey, and an under-quorum rotation is
//                REJECTED by verify-chain.
//   3. bones-lint — a clean coarse frame passes (green); a planted fine-grained/PII/burst frame
//                fails (red).
// Exit 0 only if every check passes.

import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { selftest as shamirSelftest } from "./shamir.mjs";
import { keyFingerprint } from "./_frame.mjs";

const TOOLS = path.dirname(fileURLToPath(import.meta.url));
const results = [];
const tmpDirs = [];
function check(name, pass, extra) {
  results.push({ name, pass: !!pass });
  console.log(`  ${pass ? "PASS" : "FAIL"}  ${name}${extra ? `  — ${extra}` : ""}`);
  return !!pass;
}

// Run a tool under a given TWIN_ROOT; returns { status, out, err }.
function run(script, args, root) {
  try {
    const out = execFileSync(process.execPath, [path.join(TOOLS, script), ...args], {
      env: { ...process.env, TWIN_ROOT: root },
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    return { status: 0, out, err: "" };
  } catch (e) {
    return { status: e.status ?? 1, out: e.stdout?.toString() || "", err: e.stderr?.toString() || "" };
  }
}

function mkTwin() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "estate-"));
  tmpDirs.push(dir);
  fs.mkdirSync(path.join(dir, "keys"), { recursive: true });
  return dir;
}
function newKeypair(dir, base) {
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  const pubPem = publicKey.export({ type: "spki", format: "pem" });
  const privPem = privateKey.export({ type: "pkcs8", format: "pem" });
  const pubFile = path.join(dir, `${base}.pub`);
  const privFile = path.join(dir, `${base}.key`);
  fs.writeFileSync(pubFile, pubPem);
  fs.writeFileSync(privFile, privPem, { mode: 0o600 });
  return { publicKey, privateKey, pubFile, privFile, fp: keyFingerprint(publicKey) };
}
function writeCard(dir, leadPub) {
  const pem = leadPub.export({ type: "spki", format: "pem" });
  fs.writeFileSync(
    path.join(dir, "card.json"),
    JSON.stringify({ twin: { who: "selftest twin", pubkey: { alg: "Ed25519", pem } }, name: "Selftest" }, null, 2)
  );
}

// --- 1. shamir --------------------------------------------------------------
console.log("shamir:");
{
  const { pass, results: rs } = shamirSelftest();
  for (const r of rs) console.log(`  ${r.pass ? "PASS" : "FAIL"}  shamir/${r.name}`);
  check("shamir: split→combine + wrong-shard failure", pass);
}

// --- 2. estate roundtrip ----------------------------------------------------
console.log("estate ceremony (temp twin):");
{
  const dir = mkTwin();
  // Lead key + card.
  const lead = newKeypair(dir, "lead");
  fs.copyFileSync(lead.privFile, path.join(dir, "keys", "twin.key"));
  fs.copyFileSync(lead.pubFile, path.join(dir, "keys", "twin.pub"));
  writeCard(dir, lead.publicKey);

  const seed = run("seed-frame.mjs", [], dir);
  check("estate: seed genesis frame", seed.status === 0, seed.err.trim() || seed.out.trim().split("\n")[0]);

  // Three enrolled devices.
  const devs = ["dev-alpha", "dev-bravo", "dev-charlie"].map((n) => ({ name: n, ...newKeypair(dir, n) }));
  let enrollOk = true;
  for (const d of devs) {
    const r = run("succession.mjs", ["enroll", d.name, d.pubFile], dir);
    enrollOk = enrollOk && r.status === 0;
  }
  check("estate: enroll 3 devices (signed enroll frames + quorum.json)", enrollOk);
  const quorum = JSON.parse(fs.readFileSync(path.join(dir, "keys", "quorum.json"), "utf8"));
  check("estate: quorum.json holds 3 device pubkeys", quorum.devices.length === 3);

  // Publish the will: 2-of-3.
  const will = run("succession.mjs", ["succession", "--heirs", devs[0].pubFile, devs[1].pubFile, devs[2].pubFile, "--policy", "2-of-3"], dir);
  check("estate: publish succession will (2-of-3)", will.status === 0, will.err.trim());

  // Recover: rotate to a new lead, co-signed by 2 of 3 devices.
  const newLead = newKeypair(dir, "newlead");
  const rot = run("succession.mjs", ["rotate", "--new", newLead.pubFile, "--sign-with", devs[0].privFile, devs[1].privFile], dir);
  check("estate: rotate lead key (2-of-3 multisig)", rot.status === 0, rot.err.trim());

  const vc = run("verify-chain.mjs", [], dir);
  const rotatedToNew = vc.out.includes(newLead.fp) && /VERDICT: OK/.test(vc.out);
  check("estate: verify-chain OK + effective key == new lead", vc.status === 0 && rotatedToNew, `eff fp ${newLead.fp}`);

  // Shard the (throwaway) key and reconstruct it; must match the CURRENT effective key.
  // (We shard newlead as the live key so reconstruct verifies against the rotated effective key.)
  fs.copyFileSync(newLead.privFile, path.join(dir, "keys", "twin.key"));
  const sh = run("succession.mjs", ["shard", "--k", "2", "--n", "3"], dir);
  const shardFiles = [1, 2, 3].map((x) => path.join(dir, "keys", "shards", `shard-${x}.txt`));
  const shardsWritten = sh.status === 0 && shardFiles.every((f) => fs.existsSync(f));
  check("estate: shard twin.key -> 3 sealed shards", shardsWritten);

  const rc = run("succession.mjs", ["reconstruct", shardFiles[0], shardFiles[2]], dir);
  check("estate: reconstruct from 2 shards MATCHES effective key", rc.status === 0 && /verify: MATCH/.test(rc.out), (rc.out.match(/verify: .*/) || [""])[0]);
}

// Negative: an under-quorum rotation must be REJECTED by verify-chain.
console.log("estate negative (under-quorum rotation rejected):");
{
  const dir = mkTwin();
  const lead = newKeypair(dir, "lead");
  fs.copyFileSync(lead.privFile, path.join(dir, "keys", "twin.key"));
  writeCard(dir, lead.publicKey);
  run("seed-frame.mjs", [], dir);
  const devs = ["d1", "d2", "d3"].map((n) => ({ name: n, ...newKeypair(dir, n) }));
  for (const d of devs) run("succession.mjs", ["enroll", d.name, d.pubFile], dir);
  run("succession.mjs", ["succession", "--heirs", devs[0].pubFile, devs[1].pubFile, devs[2].pubFile, "--policy", "2-of-3"], dir);
  const newLead = newKeypair(dir, "newlead");
  // Only ONE device signs — below the 2-of-3 threshold.
  run("succession.mjs", ["rotate", "--new", newLead.pubFile, "--sign-with", devs[0].privFile], dir);
  const vc = run("verify-chain.mjs", [], dir);
  check("estate: verify-chain REJECTS a 1-of-3 rotation", vc.status !== 0 && /FAIL/.test(vc.out + vc.err));
}

// --- 3. bones-lint red/green ------------------------------------------------
console.log("bones-lint fixtures:");
{
  // GREEN: a real coarse (day-precision) seed frame passes.
  const green = mkTwin();
  const lead = newKeypair(green, "lead");
  fs.copyFileSync(lead.privFile, path.join(green, "keys", "twin.key"));
  writeCard(green, lead.publicKey);
  run("seed-frame.mjs", [], green);
  run("pulse.mjs", [], green);
  const g = run("bones-lint.mjs", [], green);
  check("bones-lint: GREEN clean coarse frame passes (exit 0)", g.status === 0, g.out.trim().split("\n").pop());

  // RED: a planted frame that leaks pattern-of-life on every value rule + non-whitelisted keys.
  const red = mkTwin();
  writeCard(red, newKeypair(red, "lead").publicKey);
  fs.mkdirSync(path.join(red, "frames"), { recursive: true });
  const bad = {
    sha: "0".repeat(64),
    prevSha: null,
    ts: "2026-07-06T13:45:12.512Z", // finer than day precision
    kind: "delta",
    delta: { email: "kody@example.com", geo: "9q8yyk8ytpxr", note: "reach me at +1 415-555-0134" },
    sig: "x",
  };
  fs.writeFileSync(path.join(red, "frames", "0-00000000.json"), JSON.stringify(bad, null, 2));
  const r = run("bones-lint.mjs", ["--json"], red);
  let rules = [];
  try {
    rules = JSON.parse(r.out).findings.map((f) => f.rule);
  } catch {}
  const wanted = ["ts-precision", "geohash", "pii-email", "pii-phone", "key-whitelist"];
  const caughtAll = wanted.every((w) => rules.includes(w));
  check("bones-lint: RED planted leak fails (exit non-zero)", r.status !== 0);
  check("bones-lint: RED catches ts/geohash/email/phone/key rules", caughtAll, `caught: ${[...new Set(rules)].join(",")}`);

  // RED burst: >3 frames sharing one calendar day.
  const burst = mkTwin();
  writeCard(burst, newKeypair(burst, "lead").publicKey);
  fs.mkdirSync(path.join(burst, "frames"), { recursive: true });
  for (let i = 0; i < 4; i++) {
    const fr = { sha: String(i).repeat(64).slice(0, 64), prevSha: null, ts: "2026-07-06", kind: "delta", delta: { note: "ok" }, sig: "x" };
    fs.writeFileSync(path.join(burst, "frames", `${i}-0000000${i}.json`), JSON.stringify(fr, null, 2));
  }
  const b = run("bones-lint.mjs", ["--json"], burst);
  let burstCaught = false;
  try {
    burstCaught = JSON.parse(b.out).findings.some((f) => f.rule === "burst");
  } catch {}
  check("bones-lint: RED catches >3-frames-per-day burst", b.status !== 0 && burstCaught);
}

// --- teardown + verdict -----------------------------------------------------
for (const d of tmpDirs) fs.rmSync(d, { recursive: true, force: true });

const pass = results.every((r) => r.pass);
console.log("");
console.log(pass ? `estate-selftest: ALL PASS (${results.length} checks)` : `estate-selftest: FAIL (${results.filter((r) => !r.pass).length}/${results.length})`);
process.exit(pass ? 0 : 1);
