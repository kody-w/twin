#!/usr/bin/env node
/**
 * Static Data Covenant harvester for agents/index.json.
 *
 * vbrainstem.html's Summon flow lists a summoned twin's agents/ directory.
 * For THIS repo (kody-w/twin) that listing now comes from committed
 * agents/index.json instead of a live, unauthenticated
 * api.github.com/repos/.../contents/agents call (RAR CONSTITUTION.md
 * Article XXIV). A summoned repo that hasn't published its own
 * agents/index.json yet still falls back to the live call in
 * vbrainstem.html — Summon can target ANY public repo, which a static
 * snapshot in this repo cannot pre-harvest on another repo's behalf. Any
 * RAPP twin/rappid repo that adopts this same convention (publish
 * agents/index.json in this shape) becomes covenant-compliant for anyone
 * summoning it, including this one.
 *
 * The shape mirrors the fields vbrainstem.html actually reads (name, type)
 * plus enough to be a genuinely useful directory listing (path, sha, size,
 * download_url — a raw.githubusercontent.com URL, itself an allowed
 * Covenant source). It deliberately drops the API response's `url` and
 * `_links` fields, which point back at api.github.com and would just
 * invite a future caller to use them.
 *
 * Usage:
 *   node scripts/harvest-agents-index.mjs [owner/repo] [agents-dir]
 *
 * Defaults to kody-w/twin and agents/. Set GH_TOKEN (or GITHUB_TOKEN) for a
 * higher rate limit; unauthenticated works too.
 */

import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(here, '..');

const repo = process.argv[2] || 'kody-w/twin';
const agentsDir = process.argv[3] || 'agents';
const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN || '';

async function main() {
  const headers = { Accept: 'application/vnd.github+json', 'User-Agent': 'twin-covenant-harvester' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`https://api.github.com/repos/${repo}/contents/${agentsDir}?ref=main`, { headers });
  if (!response.ok) {
    throw new Error(`GitHub returned ${response.status} listing ${agentsDir}/ in ${repo}`);
  }
  const entries = await response.json();
  if (!Array.isArray(entries)) {
    throw new Error(`Unexpected contents response for ${agentsDir}/ in ${repo} (not a directory?)`);
  }

  const trimmed = entries.map((item) => ({
    name: item.name,
    path: item.path,
    sha: item.sha,
    size: item.size,
    type: item.type,
    download_url: item.download_url,
  }));

  const outPath = path.join(repoRoot, agentsDir, 'index.json');
  writeFileSync(outPath, JSON.stringify(trimmed, null, 2) + '\n');
  console.log(`[harvest] wrote ${trimmed.length} entries to ${path.relative(repoRoot, outPath)}`);
}

main().catch((error) => {
  console.error(`[harvest] ERROR: ${error.message}`);
  process.exit(1);
});
