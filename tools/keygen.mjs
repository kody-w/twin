// tools/keygen.mjs — mint the twin's Ed25519 keypair (§2/§4).
//
//   node tools/keygen.mjs [--force]
//
// Writes keys/twin.key (PKCS8 private, NEVER committed — gitignored) and
// keys/twin.pub (SPKI public, ships in the bones). Prints the SPKI PEM +
// raw base64 so you can paste the public key into card.json (twin.pubkey).
//
// The private half is the on-device twin's signing key: it never travels in
// the bones. The public half is what edges use to verify broadcast frames.

import crypto from "node:crypto";
import fs from "node:fs";
import { KEYS_DIR, PRIV_PATH, PUB_PATH } from "./_frame.mjs";

const force = process.argv.includes("--force");

if (fs.existsSync(PRIV_PATH) && !force) {
  console.error(`refusing to overwrite existing ${PRIV_PATH} (pass --force to regenerate)`);
  process.exit(2);
}

fs.mkdirSync(KEYS_DIR, { recursive: true });

const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");

const privPem = privateKey.export({ type: "pkcs8", format: "pem" });
const pubPem = publicKey.export({ type: "spki", format: "pem" });
// Raw 32-byte Ed25519 public key = last 32 bytes of the DER SPKI structure.
const pubDer = publicKey.export({ type: "spki", format: "der" });
const rawPub = pubDer.subarray(pubDer.length - 32);

fs.writeFileSync(PRIV_PATH, privPem, { mode: 0o600 });
fs.writeFileSync(PUB_PATH, pubPem);

console.log(`wrote ${PRIV_PATH} (private — gitignored, mode 600)`);
console.log(`wrote ${PUB_PATH} (public — ships in bones)`);
console.log("");
console.log("card.json twin.pubkey block:");
console.log(
  JSON.stringify(
    {
      alg: "Ed25519",
      raw_b64: rawPub.toString("base64"),
      pem: pubPem,
    },
    null,
    2
  )
);
