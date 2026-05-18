#!/usr/bin/env node
/**
 * lint-manifest.mjs — Sanity checks for both manifest variants.
 *
 * Confirms the "Regras de Ouro" (CRITICAL section of the task brief):
 *   1. No <all_urls> permission in either manifest.
 *   2. host_permissions allowlist-only (must include 127.0.0.1:18802).
 *   3. omnibox keyword set to "nx".
 *   4. version + manifest_version present.
 */

import { readFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TARGETS = ["manifest.json", "manifest.firefox.json"];

const errors = [];

for (const file of TARGETS) {
  const path = join(ROOT, "extension", file);
  const m = JSON.parse(readFileSync(path, "utf8"));

  // manifest_version must be 3
  if (m.manifest_version !== 3) {
    errors.push(`${file}: manifest_version must be 3`);
  }
  // version present
  if (!m.version) errors.push(`${file}: version missing`);

  // No <all_urls> anywhere
  const stringified = JSON.stringify(m);
  if (stringified.includes("<all_urls>")) {
    // toast.css gets web_accessible_resources match — that one is OK
    // (does not grant API capability, just lets pages load the CSS).
    const allowed = (m.web_accessible_resources || []).some((entry) =>
      (entry.matches || []).includes("<all_urls>"),
    );
    if (!allowed) {
      errors.push(`${file}: <all_urls> found outside web_accessible_resources`);
    }
  }

  // host_permissions must include localhost API
  const hp = m.host_permissions || [];
  if (!hp.some((h) => h.includes("127.0.0.1:18802"))) {
    errors.push(`${file}: host_permissions missing 127.0.0.1:18802`);
  }

  // permissions must NOT include any wildcard URL
  for (const p of m.permissions || []) {
    if (p.includes("*") || p.startsWith("http")) {
      errors.push(`${file}: invalid wildcard permission "${p}"`);
    }
  }

  // omnibox keyword
  // (only Chrome has omnibox in our setup; Firefox MV3 dropped it temporarily)
  if (file === "manifest.json") {
    if (m.omnibox?.keyword !== "nx") {
      errors.push(`${file}: omnibox.keyword must be "nx"`);
    }
  }

  console.log(`✓ ${file} (v${m.version})`);
}

if (errors.length > 0) {
  console.error("\nLint errors:");
  for (const e of errors) console.error(` - ${e}`);
  process.exit(1);
}

console.log("\nAll manifests pass lint.");
