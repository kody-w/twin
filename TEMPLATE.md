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

1. **Generate a fresh rappid** for your variant (a new UUID).
2. **Update `rappid.json`** — set `rappid` to the fresh value, `parent_rappid` to either:
   - this twin's rappid (`37ad22f5-ed6d-48b1-b8b4-61019f58a42b`) if you want the wildhaven-style ancestry, or
   - rapp's species root rappid (`0b635450-c042-49fb-b4b1-bdb571044dec`) if you want to skip the wildhaven step in your lineage chain. The script asks.
3. **Update `parent_repo`** and **`parent_commit`** to record where you forked from.
4. **Reset brand content** — `soul.md`, `MANIFEST.md`, and the agent files become placeholder versions you'll fill in. Existing wildhaven-specific content is replaced with `<TODO: your variant>` markers so you can't accidentally ship wildhaven's voice as your own.
5. **Drop the wildhaven private companion pointer** from `rappid.json` (it's not yours; create your own private companion separately if you want one).
6. **Print the summon URL** for your new variant so you can update the QR.

### 4. Customize

Open the marked files and fill in your variant's content:

- `soul.md` — the system prompt that defines your twin's voice.
- `MANIFEST.md` — your variant's vision document.
- `agents/*.py` — adjust the existing agent files for your context, or replace them entirely.
- `utils/body_functions/manifest_body_function.py` — update the manifest endpoints.
- `README.md` — your variant's public-facing intro.
- `LICENSE` — the script leaves it as All Rights Reserved by default; update if you want a different posture.
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

If you used the `--parent rapp` option in the script, your `parent_rappid` points directly at rapp instead. Your variant is then a *sibling* of wildhaven, not a descendant. Both are valid; pick the relationship that matches what your twin actually inherits.

## What you get for free

By templating from this repo, your variant starts with:

- ✓ The Pre-Founder twin pattern (soul, agents, body_functions structure)
- ✓ A working GitHub Pages landing page with QR code
- ✓ A summon URL convention compatible with the upstream vBrainstem
- ✓ The rappid lineage protocol wired up
- ✓ The private companion pattern documented (you create your own private repo)
- ✓ A LICENSE file you can replace with whatever fits your variant
- ✓ The `installer/initialize-variant.sh` script for any future templates of your own

## When NOT to use this template

If your variant is structurally very different from a Pre-Founder twin — for example, if you're building a memorial twin, a place twin, or a project twin — consider templating from [kody-w/RAPP](https://github.com/kody-w/RAPP) directly when that template exists, or starting from scratch with a fresh `rappid.json` carrying `parent_rappid` → rapp's species root. The Pre-Founder twin pattern is opinionated about what content goes where; other twin shapes have different needs.

## See also

- [Constitution Article XXXIV](https://github.com/kody-w/RAPP/blob/main/CONSTITUTION.md) — variant lineage protocol.
- [SUMMON.md](./SUMMON.md) — the URL convention scanning the QR uses.
- [rappid.json](./rappid.json) — this twin's lineage anchor; your variant's will look the same shape.
