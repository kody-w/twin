# Using This Repo as a Template

This repository is set up as a **GitHub template**. Anyone can spawn a new Pre-Founder twin (or any build-in-public brand-twin variant) from it in one click — no manual scaffolding required.

## How GitHub templates work

GitHub's "Use this template" feature creates a fresh repository with the template's contents but **without** the template's commit history. Your new repo's first commit is its initial state; the lineage to the parent is conceptual (recorded in your `rappid.json`), not a literal git fork relationship.

This matters because variant lineage in RAPP is **rappid-based**, not git-based. The chain is in `rappid.json` files, not in GitHub fork pointers.

## The flow

### 1. Click "Use this template"

On the [GitHub page](https://github.com/kody-w/wildhaven-ai-homes-twin), click the green **"Use this template"** button (top right) → **Create a new repository**.

Or use the direct link: <https://github.com/kody-w/wildhaven-ai-homes-twin/generate>

Choose:
- **Owner** — your GitHub user / org
- **Repository name** — your variant's name (e.g., `my-startup-twin`, `family-memorial-twin`, `project-shepherd`)
- **Visibility** — Public (for build-in-public twins) or Private (for personal / unreleased work)
- **Include all branches** — leave unchecked unless you want history

Click **Create repository from template**.

### 2. Clone your new repo

```bash
git clone https://github.com/<your-user>/<your-repo-name>.git
cd <your-repo-name>
```

### 3. Run the initialization script

```bash
bash installer/initialize-variant.sh
```

This is the one-step setup. The script will:

1. **Run `lineage_check.py`** to verify this is an uninitialized template clone (refuses to run on the wildhaven repo itself, or on an already-initialized variant without explicit confirmation).
2. **Generate a fresh rappid** for your variant (a new UUID).
3. **Update lineage fields in `rappid.json`** — set `rappid` to the fresh value and `parent_rappid` to wildhaven's rappid (`37ad22f5-ed6d-48b1-b8b4-61019f58a42b`). Per the **single-parent rule** (Constitution Article XXXIV), every variant created from this template ALWAYS lists wildhaven as its parent, because that is the code it actually inherited. There is no "skip wildhaven and claim rapp" option — to be a direct child of rapp, template from [kody-w/RAPP](https://github.com/kody-w/RAPP) instead.
4. **Update `parent_repo`** and **`parent_commit`** to record where you forked from.
5. **Print the summon URL** for your new variant so you can update the QR.

### What the installer does NOT do

**Rule: never overwrite local data.** A twin will need to change locally after it hatches, and an installer that wipes content would erase that work on every re-run. So the script:

- **Does not touch `soul.md`, `MANIFEST.md`, `README.md`, `LICENSE`, or any other content file.** They still hold the parent's content as a starting point — edit them yourself to give your variant its voice.
- **Does not delete the inherited `private_companion` block.** It currently points at wildhaven's private repo (which you don't have access to); you can repoint or remove it manually.
- **Does not change `kind` / `description`** in `rappid.json`. Edit those when your variant has its own answers.
- **Is safe to re-run.** Even if you re-run after customizing, only lineage fields move. Nothing local is destroyed.

### 4. Customize

The installer left every content file alone. Edit them in place to make the variant yours — they currently hold the parent's content as a starting point:

- `soul.md` — the system prompt that defines your twin's voice. Currently wildhaven's; rewrite for your twin.
- `MANIFEST.md` — your variant's vision document. Currently wildhaven's; rewrite.
- `agents/*.py` — adjust the existing agent files for your context, or replace them entirely.
- `utils/body_functions/manifest_body_function.py` — update the manifest endpoints.
- `README.md` — your variant's public-facing intro.
- `LICENSE` — the inherited LICENSE is the parent's. Replace with whatever fits your variant.
- `rappid.json` — repoint or remove the inherited `private_companion` block (you don't have access to wildhaven's private repo); edit `kind` / `description` to describe your variant.
- `summon.svg` — regenerate with your new URL (see SUMMON.md for the snippet).
- `index.html` — the GitHub Pages landing page; update the brand text to your variant.

### 5. Commit and push

```bash
git add -A
git commit -m "init: <your variant name> — variant of wildhaven-ai-homes-twin"
git push origin main
```

### 6. Enable GitHub Pages (optional but recommended)

Visit your repo's Settings → Pages → Source: `main` branch, root folder. Within a minute or so, your variant has its own URL at `https://<your-user>.github.io/<your-repo>/`.

### 7. Optional: create your own private companion

If your variant needs a private operational layer (real customer pipeline, founder negotiations, etc.):

```bash
gh repo create <your-user>/<your-repo>-private --private --clone --description "Private companion for <your-repo>"
```

Then update your variant's `rappid.json` to add the `private_companion` block pointing at the new private repo. See this twin's `rappid.json` for the schema.

## Lineage you've created

After running the script, your variant's `rappid.json` looks like:

```json
{
  "schema": "rapp-rappid/1.1",
  "rappid": "<your fresh UUID>",
  "parent_rappid": "37ad22f5-ed6d-48b1-b8b4-61019f58a42b",
  "parent_repo": "https://github.com/kody-w/wildhaven-ai-homes-twin.git",
  "parent_commit": "<the wildhaven commit you forked from>",
  ...
}
```

The chain walks back: your variant → wildhaven-ai-homes-twin → rapp species root. Anyone walking from your repo via `parent_rappid` lands at rapp eventually.

### Why no "claim rapp directly" option?

A variant's `parent_rappid` declares its **code ancestor** — the repo whose contents it inherited at template time. If you templated from this repo, your code ancestor is wildhaven, not rapp. Letting you claim rapp as your parent would corrupt the lineage chain: the next person walking the tree would expect to find rapp's code in your repo, but they'd find wildhaven's.

The single-parent rule keeps the chain trustworthy. If you want to be a direct child of rapp, template from `kody-w/RAPP` — your code will then be rapp's, and `parent_rappid` will correctly say so.

## Repository layout

The root carries only the **kernel** (`brainstem.py`) and the variant's **identity / content** files. Everything else is sorted into `utils/` (code) and `installer/` (run + setup scripts):

```
<repo>/
├── brainstem.py                ← the canonical kernel (Article XXXIII — do not modify)
├── rappid.json                 ← lineage anchor + brainstem version pin
├── soul.md / MANIFEST.md / README.md / LICENSE / SUMMON.md / TEMPLATE.md
├── index.html / vbrainstem.html / summon.svg
├── agents/                     ← variant's agents (subclasses of BasicAgent)
├── app/                        ← static web app (icons, PWA manifest, sw.js)
├── installer/
│   ├── initialize-variant.sh   ← variant init (single-parent, non-destructive)
│   ├── start.sh / start.ps1    ← launch the brainstem locally
│   ├── requirements.txt        ← Python deps for the kernel
│   └── VERSION                 ← bundled kernel version
└── utils/
    ├── boot.py                 ← kernel-sibling launcher
    ├── body_functions_loader.py
    ├── senses_loader.py
    ├── lineage_check.py        ← boot guard (refuses uninitialized clones)
    ├── local_storage.py / twin.py / llm.py / workspace.py / ...
    ├── body_functions/         ← variant's body_functions (REST endpoints)
    ├── senses/                 ← variant's senses (chat-stream contributors)
    └── web/                    ← static assets served at /web/
```

To run locally: `bash installer/start.sh` (only after `bash installer/initialize-variant.sh` has given the repo its own rappid).

## What you get for free

By templating from this repo, your variant starts with:

- ✓ The Pre-Founder twin pattern (soul, agents, body_functions structure)
- ✓ **A self-contained, runnable brainstem** — `bash installer/start.sh` works without any separate `~/.brainstem` install. The kernel is bundled and pinned in `rappid.json` under the `brainstem` block.
- ✓ A working GitHub Pages landing page with QR code
- ✓ A summon URL convention compatible with the upstream vBrainstem
- ✓ The rappid lineage protocol wired up + boot guard that refuses uninitialized clones
- ✓ The private companion pattern documented (you create your own private repo)
- ✓ A LICENSE file you can replace with whatever fits your variant
- ✓ The `installer/initialize-variant.sh` script for any future templates of your own

## When NOT to use this template

If your variant is structurally very different from a Pre-Founder twin — for example, if you're building a memorial twin, a place twin, or a project twin — template from [kody-w/RAPP](https://github.com/kody-w/RAPP) directly. That gives you `parent_rappid = rapp` (correctly, because you'd inherit rapp's code), and you skip the wildhaven step entirely. The Pre-Founder twin pattern this repo encodes is opinionated about what content goes where; other twin shapes have different needs.

## See also

- [Constitution Article XXXIV](https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md) — variant lineage protocol.
- [SUMMON.md](./SUMMON.md) — the URL convention scanning the QR uses.
- [rappid.json](./rappid.json) — this twin's lineage anchor; your variant's will look the same shape.
