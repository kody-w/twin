# Summoning the Twin

> **Scan the QR. Open the link. The twin appears.**

A "summon" is the act of pulling this twin into a runtime so you can talk to it. The twin lives in this repo (and its private companion); summoning *materializes* it somewhere — most commonly the **vBrainstem** in your browser, on any device, in seconds.

## The summon URL

This is the canonical address for summoning this twin:

```
https://kody-w.github.io/wildhaven-ai-homes-twin/vbrainstem.html?summon=kody-w/wildhaven-ai-homes-twin
```

The QR code in [`summon.svg`](./summon.svg) encodes it. Scan it from any phone camera or QR app and your browser opens the vBrainstem with the twin auto-loading.

## What the URL means

The vBrainstem (`vbrainstem.html` at this repo's root) is a self-contained, browser-side simulator with a Pyodide sandbox and an in-browser agent runtime. It is hosted at `kody-w.github.io/wildhaven-ai-homes-twin/` via this repo's own GitHub Pages — no install, no auth required to load it. The simulator was originally inherited from [kody-w/RAPP](https://github.com/kody-w/RAPP) and now lives here as a sovereign copy, so the twin's URL surface does not depend on the upstream's hosting.

When the vBrainstem loads with `?summon=<owner>/<repo>`, it knows to fetch that twin's content (rappid.json → soul.md → agents/ → body_functions/) and boot it in the simulator. The convention:

```
?summon=kody-w/wildhaven-ai-homes-twin
        └─owner──┘ └────repo name───┘
```

The vBrainstem fetches files from:

```
https://raw.githubusercontent.com/<owner>/<repo>/main/<path>
```

Public twins are available to anyone. The vBrainstem will show what the twin says, with the full system prompt and agents the public repo defines.

## Authenticated escalation (private layer)

If you (the user opening the URL) are signed in to GitHub *and* have read access to the twin's private companion repo (per `rappid.json`'s `private_companion` field), the vBrainstem also pulls private layer access. Same URL — different observed twin depending on who's looking.

The escalation path:

1. Public visitor scans QR → sees the public twin (everything in this repo).
2. Authenticated operator scans the same QR → vBrainstem additionally fetches from `wildhaven-ai-homes-twin-private` via the operator's GitHub auth token. Private context (pipeline, financial model, hiring targets) informs the twin's reasoning, but per `soul.md` the twin still never quotes it verbatim in public-facing chat.

Anonymous requests to private content return 404 (GitHub does not reveal private-repo existence). The twin appears the same shape to a public scanner; the private layer is silently invisible.

## Hatching on device

The vBrainstem is a *simulator* — useful for trying the twin out, having a conversation, and showing it to someone. For a real, persistent organism you control on your own machine, you **hatch** the twin on device:

```bash
# Install the upstream brainstem (one-liner)
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash

# Point the brainstem at this twin's content
git clone https://github.com/kody-w/wildhaven-ai-homes-twin.git ~/wah-twin
SOUL_PATH=~/wah-twin/soul.md \
  AGENTS_PATH=~/wah-twin/agents \
  ~/.brainstem/start.sh
```

A future capability under development: a "hatch on device" button in the vBrainstem that streamlines this flow into a single tap, with optional install of the dedicated twin UI as an iOS PWA. See the [main RAPP repo](https://github.com/kody-w/RAPP) for progress.

## What the QR encodes — extended

For non-QR users, the same link works as a plain URL — pasteable, shareable, embeddable in emails / slides / business cards. The `summon.svg` file is checked into this repo so it renders inline in the README and on the GitHub Pages landing.

To regenerate the QR (e.g., after a rename), run:

```python
import qrcode
from qrcode.image.svg import SvgPathImage

URL = "https://kody-w.github.io/wildhaven-ai-homes-twin/vbrainstem.html?summon=kody-w/wildhaven-ai-homes-twin"
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
qr.add_data(URL)
qr.make(fit=True)
qr.make_image(image_factory=SvgPathImage).save("summon.svg")
```

## Forward-compatibility note

The `?summon=` URL convention is **shipped today** as a stable contract. The vBrainstem's handler for the parameter is rolling in to upstream RAPP — until that lands, scanning the QR opens the vBrainstem at its current default state. The QR continues to work without change once vBrainstem support is live; the contract is the URL, not the implementation.

## See also

- [`rappid.json`](./rappid.json) — the twin's lineage identity (parent_rappid → kody-w/RAPP species root)
- [`README.md`](./README.md) — the brand operating in public
- [`utils/private_layer.py`](./utils/private_layer.py) — bridge to private companion repo
- [vBrainstem architecture in the upstream vault](https://github.com/kody-w/RAPP/blob/main/pages/vault/Architecture/Boot%20Sidecar%20—%20Integrating%20Utils%20Without%20Modifying%20the%20Kernel.md)
