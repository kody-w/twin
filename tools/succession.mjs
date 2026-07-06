// tools/succession.mjs — the estate key ceremony (§15). Zero deps.
//
//   node tools/succession.mjs enroll <device-name> <pubkey.pem>
//   node tools/succession.mjs succession --heirs <pubkey.pem...> --policy k-of-n
//   node tools/succession.mjs rotate --new <pubkey.pem> --sign-with <device.key...>
//   node tools/succession.mjs shard --k 2 --n 3 [--qr]
//   node tools/succession.mjs reconstruct <shard.txt...>
//
// §15: "If it can't be inherited, it isn't owned." Succession is designed while the owner lives.
// These ceremonies run between the owner's OWN devices — never a hosted recovery flow:
//   enroll      — register a device's pubkey into the recovery quorum (a signed public frame).
//   succession  — publish the will: heirs + a k-of-n recovery policy (a signed public frame).
//   rotate      — recover the lead key: ≥k enrolled devices co-sign a new lead key (multisig frame).
//   shard       — Shamir-split the private key into printable shards for a safe/will (SEALED, gitignored).
//   reconstruct — rebuild the private key from any k shards.
//
// Public frames (enroll/succession/rotate) carry only PUBLIC keys and are content-addressed and
// signed. Shards and reconstructed keys are SEALED: they only ever touch keys/shards/ (gitignored)
// or a temp dir. Nothing secret is ever committed or networked.

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import {
  KEYS_DIR,
  FRAMES_DIR,
  PRIV_PATH,
  buildSignedFrame,
  buildMultiSigFrame,
  persistFrame,
  loadPublicKeyFrom,
  loadPrivateKeyFrom,
  loadPrivateKey,
  resolvePublicKey,
  dayStamp,
  keyFingerprint,
  sha8,
} from "./_frame.mjs";
import { resolveChain, parsePolicy } from "./_chain.mjs";
import { split, combine, encodeShard, decodeShard } from "./shamir.mjs";
import { qrSvg } from "./_qr.mjs";

const QUORUM_PATH = path.join(KEYS_DIR, "quorum.json");
const SHARDS_DIR = path.join(KEYS_DIR, "shards");

function die(msg, code = 2) {
  console.error(msg);
  process.exit(code);
}

// Minimal flag parser: collects positionals and --flag values (1+ values until the next --flag).
function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const name = a.slice(2);
      const vals = [];
      while (i + 1 < argv.length && !argv[i + 1].startsWith("--")) vals.push(argv[++i]);
      flags[name] = vals.length === 0 ? true : vals.length === 1 ? vals[0] : vals;
    } else {
      positional.push(a);
    }
  }
  return { positional, flags };
}

function pubRawB64(pub) {
  const ko = pub && pub.asymmetricKeyType ? pub : crypto.createPublicKey(pub);
  const der = ko.export({ type: "spki", format: "der" });
  return der.subarray(der.length - 32).toString("base64");
}
function pubPem(pub) {
  const ko = pub && pub.asymmetricKeyType ? pub : crypto.createPublicKey(pub);
  return ko.export({ type: "spki", format: "pem" }).toString();
}

function readQuorum() {
  if (!fs.existsSync(QUORUM_PATH)) {
    return { schema: "rapp-twin-quorum/1.0", _note: "Enrolled-device pubkeys = the recovery quorum (§15). PUBLIC; mirrors enroll frames.", devices: [] };
  }
  return JSON.parse(fs.readFileSync(QUORUM_PATH, "utf8"));
}
function writeQuorum(q) {
  fs.mkdirSync(KEYS_DIR, { recursive: true });
  fs.writeFileSync(QUORUM_PATH, JSON.stringify(q, null, 2) + "\n");
}

// --- enroll -----------------------------------------------------------------
function cmdEnroll(argv) {
  const { positional } = parseArgs(argv);
  const [name, pubFile] = positional;
  if (!name || !pubFile) die("usage: succession enroll <device-name> <pubkey.pem>");
  if (!fs.existsSync(pubFile)) die(`no such pubkey file: ${pubFile}`);

  const pub = loadPublicKeyFrom(pubFile);
  const pem = pubPem(pub);
  const raw_b64 = pubRawB64(pub);

  // Signed public frame: the enrollment is part of the unforgeable biography.
  const built = buildSignedFrame({ kind: "enroll", delta: { device: name, pubkey: pem } });
  persistFrame(built);

  const q = readQuorum();
  q.devices = (q.devices || []).filter((d) => d.name !== name);
  q.devices.push({ name, alg: "Ed25519", pem, raw_b64, enrolled: dayStamp(), frame: sha8(built.sha) });
  writeQuorum(q);

  console.log(`enrolled device "${name}" into the quorum (${q.devices.length} device(s))`);
  console.log(`  pubkey fp: ${keyFingerprint(pub)}`);
  console.log(`  frame:     ${built.fileName}  (kind=enroll, signed by the lead key)`);
  console.log(`  quorum:    keys/quorum.json`);
}

// --- succession (the will) --------------------------------------------------
function cmdSuccession(argv) {
  const { flags } = parseArgs(argv);
  const heirFiles = flags.heirs ? [].concat(flags.heirs) : [];
  const policyStr = flags.policy;
  if (heirFiles.length === 0 || !policyStr) die("usage: succession succession --heirs <pubkey.pem...> --policy k-of-n");
  let policy;
  try {
    policy = parsePolicy(policyStr);
  } catch (e) {
    die(e.message);
  }

  const heirs = heirFiles.map((f) => {
    if (!fs.existsSync(f)) die(`no such heir pubkey file: ${f}`);
    return pubPem(loadPublicKeyFrom(f));
  });

  const built = buildSignedFrame({ kind: "succession", delta: { heirs, policy: `${policy.k}-of-${policy.n}` } });
  persistFrame(built);

  console.log(`published the will — succession frame ${built.fileName}`);
  console.log(`  heirs:  ${heirs.length}`);
  console.log(`  policy: ${policy.k}-of-${policy.n} (≥${policy.k} enrolled devices may recover the lead key)`);
  console.log(`  signed by the current lead key; this is the PUBLIC will (no private data).`);
}

// --- rotate (recover the lead key) ------------------------------------------
function cmdRotate(argv) {
  const { flags } = parseArgs(argv);
  const newFile = flags.new;
  const signWith = flags["sign-with"] ? [].concat(flags["sign-with"]) : [];
  if (!newFile || signWith.length === 0) die("usage: succession rotate --new <pubkey.pem> --sign-with <device.key...>");
  if (!fs.existsSync(newFile)) die(`no such new pubkey file: ${newFile}`);

  const newPem = pubPem(loadPublicKeyFrom(newFile));

  const q = readQuorum();
  const byRaw = new Map((q.devices || []).map((d) => [d.raw_b64, d]));

  const signers = signWith.map((keyFile) => {
    if (!fs.existsSync(keyFile)) die(`no such device key file: ${keyFile}`);
    const key = loadPrivateKeyFrom(keyFile);
    const raw = pubRawB64(crypto.createPublicKey(key));
    const dev = byRaw.get(raw);
    if (!dev) die(`device key ${keyFile} is not enrolled in the quorum — enroll it first`);
    return { device: dev.name, key };
  });

  // Warn (don't block) if below policy — verify-chain is the real gate.
  const chain = resolveChain();
  const k = chain.policy ? chain.policy.k : (q.devices || []).length;
  if (signers.length < k) console.error(`warning: ${signers.length} signer(s) < policy k=${k}; verify-chain will reject this rotation`);

  const built = buildMultiSigFrame({ kind: "rotate", delta: { newKey: newPem } }, signers);
  persistFrame(built);

  console.log(`rotated the lead key — rotate frame ${built.fileName}`);
  console.log(`  new lead fp: ${keyFingerprint(loadPublicKeyFrom(newFile))}`);
  console.log(`  co-signed by: ${signers.map((s) => s.device).join(", ")} (${signers.length} device(s))`);
  console.log(`  verify with: node tools/verify-chain.mjs`);
}

// --- shard (Shamir-split the private key) -----------------------------------
function cmdShard(argv) {
  const { flags } = parseArgs(argv);
  const k = Number(flags.k);
  const n = Number(flags.n);
  const withQr = !!flags.qr;
  if (!Number.isInteger(k) || !Number.isInteger(n)) die("usage: succession shard --k <k> --n <n> [--qr]");
  if (!fs.existsSync(PRIV_PATH)) die(`no private key at ${PRIV_PATH} — nothing to shard`);

  const secret = fs.readFileSync(PRIV_PATH);
  let shards;
  try {
    shards = split(secret, n, k);
  } catch (e) {
    die(e.message);
  }

  fs.mkdirSync(SHARDS_DIR, { recursive: true });
  const written = [];
  for (const shard of shards) {
    const line = encodeShard(shard, k, n);
    const txt =
      `# twin key shard ${shard.x} of ${n} — need ${k} to reconstruct (Shamir GF(256), §15)\n` +
      `# KEEP SEALED. Distribute by hand: safe / will / trusted heir. Any ${k} of ${n} rebuild the twin.\n` +
      `# Do not photograph ${k} shards together. Reconstruct: node tools/succession.mjs reconstruct <files...>\n` +
      `${line}\n`;
    const txtPath = path.join(SHARDS_DIR, `shard-${shard.x}.txt`);
    fs.writeFileSync(txtPath, txt, { mode: 0o600 });
    written.push(txtPath);
    if (withQr) {
      const svgPath = path.join(SHARDS_DIR, `shard-${shard.x}.svg`);
      fs.writeFileSync(svgPath, qrSvg(line, { ecl: "M", scale: 6 }));
      written.push(svgPath);
    }
  }

  console.log(`sharded keys/twin.key -> ${n} shard(s), any ${k} reconstruct (keys/shards/, gitignored)`);
  for (const w of written) console.log(`  ${path.relative(process.cwd(), w)}`);
  console.log("");
  console.log("CEREMONY (§15):");
  console.log(`  1. Print each shard-*.txt${withQr ? " (or its shard-*.svg QR)" : ""} on paper.`);
  console.log("  2. Distribute to separate places of trust: a home safe, your will/estate lawyer,");
  console.log("     a trusted heir. No single place holds enough to raise the twin.");
  console.log(`  3. Any ${k} reunited (on inheritance, or if you lose a device) rebuild the key:`);
  console.log("       node tools/succession.mjs reconstruct keys/shards/shard-1.txt keys/shards/shard-2.txt");
  console.log("  4. Then DELETE the digital shards; the paper is the heirloom.");
  console.log("");
  console.log("These files are SEALED — gitignored, never networked. Prove: git check-ignore keys/shards/shard-1.txt");
}

// --- reconstruct ------------------------------------------------------------
function cmdReconstruct(argv) {
  const { positional } = parseArgs(argv);
  if (positional.length === 0) die("usage: succession reconstruct <shard.txt...>");

  const shards = positional.map((f) => {
    if (!fs.existsSync(f)) die(`no such shard file: ${f}`);
    const line = fs
      .readFileSync(f, "utf8")
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith("#"))
      .pop();
    if (!line) die(`no shard payload line in ${f}`);
    try {
      return decodeShard(line);
    } catch (e) {
      die(`${f}: ${e.message}`);
    }
  });

  const ks = new Set(shards.map((s) => s.k));
  const kNeeded = shards[0].k;
  if (shards.length < kNeeded) console.error(`warning: shards declare k=${kNeeded} but only ${shards.length} provided — result will be wrong`);

  const secret = combine(shards);

  // Verify: does the reconstructed private key match the twin's effective published pubkey?
  let verdict = "unknown";
  try {
    const priv = crypto.createPrivateKey(secret);
    const gotFp = keyFingerprint(crypto.createPublicKey(priv));
    let wantFp = null;
    try {
      wantFp = resolveChain().effectiveKeyFp;
    } catch {
      wantFp = keyFingerprint(resolvePublicKey());
    }
    verdict = gotFp === wantFp ? `MATCH (fp ${gotFp})` : `NO MATCH (got ${gotFp}, published ${wantFp})`;
  } catch (e) {
    verdict = `not a valid private key (${e.message}) — wrong or insufficient shards`;
  }

  // Never clobber an existing key; write recovery output to a sealed, gitignored path.
  fs.mkdirSync(KEYS_DIR, { recursive: true });
  let outPath = PRIV_PATH;
  if (fs.existsSync(PRIV_PATH)) outPath = path.join(KEYS_DIR, "twin.reconstructed.key");
  fs.writeFileSync(outPath, secret, { mode: 0o600 });

  console.log(`reconstructed the private key from ${shards.length} shard(s)`);
  console.log(`  wrote:  ${path.relative(process.cwd(), outPath)}  (SEALED — gitignored)`);
  console.log(`  verify: ${verdict}`);
  if (outPath !== PRIV_PATH) console.log(`  note:   ${path.relative(process.cwd(), PRIV_PATH)} already exists — did not overwrite. Move the reconstructed key in yourself if intended.`);
}

// --- dispatch ---------------------------------------------------------------
const [cmd, ...rest] = process.argv.slice(2);
switch (cmd) {
  case "enroll": cmdEnroll(rest); break;
  case "succession": cmdSuccession(rest); break;
  case "rotate": cmdRotate(rest); break;
  case "shard": cmdShard(rest); break;
  case "reconstruct": cmdReconstruct(rest); break;
  default:
    console.error("usage: node tools/succession.mjs <enroll|succession|rotate|shard|reconstruct> ...");
    process.exit(2);
}
