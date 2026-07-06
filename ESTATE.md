# THE ESTATE — inheriting the twin (§15)

> *If it can't be inherited, it isn't owned.*

A digital twin is meant to outlive a single device, a single password, and — one day — a single
lifetime. Its public history (`frames/`) is an unforgeable biography; its sealed half (soul, vault,
agents, keys) is a willed archive. This document is the ceremony for making the twin **heirloom-grade**:
recoverable if you lose a key, and inheritable when the time comes — all arranged **while you live**,
between **your own devices**, never through a hosted "recover my account" flow. There is no server in
this story. The people you trust are the recovery.

Two facts make it work:

- **Key loss ≠ twin death.** Your other enrolled devices are the recovery quorum. Any *k* of them can
  co-sign a new lead key. The biography continues, unbroken and verifiable, across the rotation.
- **The private key can be split, not just stored.** Shamir's secret sharing cuts the key into *n*
  shards where any *k* reconstruct it and any *k−1* reveal *nothing*. A shard in a safe, a shard with
  the will, a shard with an heir — no single hand holds the twin, and no single loss ends it.

Public ceremonies (enroll, succession, rotate) publish only **public keys**, signed into the pulse.
Sealed ceremonies (shard, reconstruct) touch only `keys/shards/` (gitignored) — printed and carried
**by hand**. Nothing secret is ever committed or networked.

---

## The 90-second ceremony (do this the day you hatch)

```bash
# 0. You already have your lead key (keys/twin.key) and card.json pubkey. Good.

# 1. Enroll a second device you own (generate a keypair on THAT device; bring its .pub here).
node tools/succession.mjs enroll laptop   keys/laptop.pub
node tools/succession.mjs enroll phone     keys/phone.pub
node tools/succession.mjs enroll safe-usb  keys/safe-usb.pub

# 2. Write the will: who inherits, and how many devices it takes to recover the lead key.
node tools/succession.mjs succession --heirs keys/heir-jordan.pub --policy 2-of-3

# 3. Split the private key into 3 printable shards; any 2 rebuild it. (--qr adds scannable SVGs.)
node tools/succession.mjs shard --k 2 --n 3 --qr

# 4. Print keys/shards/shard-*.txt (or the .svg QR). Distribute: home safe · will · trusted heir.
#    Then delete the digital shards — the paper is the heirloom.

# Verify the whole biography + current lead key at any time:
node tools/verify-chain.mjs
```

That's it. Your twin can now survive a lost laptop, and can be handed down.

---

## The ceremonies in full

All commands are zero-dependency Node scripts (`node builtins only`). Run them from the repo root.

### `enroll <device-name> <pubkey.pem>` — grow the recovery quorum
Registers a device you own into the quorum. Generate the keypair **on that device** and bring only its
**public** key here. Enrolling emits a signed `enroll` frame (part of the public biography) and appends
the device's pubkey to `keys/quorum.json`. Do this for every device that should be able to vote in a
recovery — the more you enroll, the more resilient the twin.

### `succession --heirs <pubkey.pem...> --policy k-of-n` — publish the will
Declares, in public and under signature, **who inherits** the twin and the **k-of-n** recovery policy.
This is the *public will*: it names heirs by their public keys and fixes how many enrolled devices are
required to rotate the lead key. Heirs inherit under the **[TWIN LICENSE](./TWIN-LICENSE.md)** — the
owner's rights of personality and publicity pass with the Bones; a derivative persona of the owner is
still forbidden without consent (see the license's succession clause).

### `rotate --new <pubkey.pem> --sign-with <device.key...>` — recover the lead key
The recovery event. When the lead key is lost (or you simply want to retire it), **≥k enrolled devices
co-sign** a new lead key into a multisig `rotate` frame. `verify-chain` advances the twin's effective
key to the new one **only if** the rotation clears the quorum threshold from the will. Below threshold,
the rotation is rejected and the old key stands — a stolen device cannot hijack the twin alone.

### `shard --k <k> --n <n> [--qr]` — split the private key for the safe/will
Shamir-splits `keys/twin.key` into `n` sealed shards under `keys/shards/` (gitignored). Any `k`
reconstruct the key; fewer reveal nothing. With `--qr`, each shard also gets a printable, standards-
compliant **SVG QR code** so it can be read back without our software. **Print, distribute, delete the
digital copies.** Never photograph `k` shards together.

### `reconstruct <shard.txt...>` — rebuild the key from the shards
Reunite any `k` shards (on inheritance, or after a device loss) to rebuild `keys/twin.key`. The tool
re-derives the public key and tells you whether it **MATCHES** the twin's published effective key — so
you know the recovery worked before you trust it. It will not overwrite an existing key.

---

## Verifying an inheritance

- `node tools/verify-chain.mjs` — walks the entire pulse, verifies every frame, and prints the
  **lead-key history**: `genesis → (rotate by quorum) → … → effective key`. An heir can run this against
  the public bones alone (no private key) and see exactly who held the key, when, and now.
- `node tools/verify-frame.mjs <frame.json>` — verifies a single frame against the effective key at its
  position in the chain (multisig `rotate` frames are checked against the quorum).
- `node tools/bones-lint.mjs` — proves the public history never leaked pattern-of-life (§13): an
  heirloom biography, not a surveillance record.

## What transfers, and what seals forever

The owner chooses at will-time which sealed memories transfer to heirs and which seal forever. The
**public bones** always transfer — they are the biography and cannot be un-published. The **sealed
half** moves only device-to-device, by hand (the §5 QR channel), exactly as much of it as the will
directs. Ownership of the address (`kody-w/twin`) and the rights it carries pass under the TWIN LICENSE.

## Prove nothing secret ever leaks

```bash
node tools/estate-selftest.mjs                 # shamir + enroll→rotate→verify + lint red/green: ALL PASS
git check-ignore keys/twin.key keys/shards/     # both print -> both are gitignored, never committed
```

The cryptography enforces the rest: an altered twin fails its own signature; an under-quorum recovery
fails its own chain. The estate is not a promise — it is a mechanism.

*Composes with the RAPP twin canon (my-twin §15 · §2/§4 · §14) and the [TWIN LICENSE](./TWIN-LICENSE.md).*
