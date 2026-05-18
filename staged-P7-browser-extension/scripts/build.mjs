#!/usr/bin/env node
/**
 * build.mjs — esbuild-driven build for the memoria-nox extension.
 *
 * Flags:
 *   --target=chrome|firefox   default: build both
 *   --watch                   esbuild --watch on each entry
 *   --package                 after build, zip dist/<target>/ → dist/<target>.zip
 *
 * Why esbuild only: zero-config bundling of ESM (background SW + popup +
 * options) into single files, plus copy of static assets (HTML/CSS/icons).
 * No webpack, no rollup, no babel.
 *
 * In v0.1, our source is already plain JS — esbuild's main job is:
 *   1. Concatenate ESM imports into one .js per entry (popup, options).
 *   2. Strip dead code / minify in production builds.
 *   3. Emit Firefox + Chrome targets with the appropriate manifest.
 */

import * as esbuild from "esbuild";
import { existsSync, mkdirSync, cpSync, rmSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "extension");
const DIST = join(ROOT, "dist");

const args = new Set(process.argv.slice(2));
const isWatch = args.has("--watch");
const isPackage = args.has("--package");
const targetArg = [...args].find((a) => a.startsWith("--target="));
const targets = targetArg ? [targetArg.split("=")[1]] : ["chrome", "firefox"];

const ENTRIES = [
  "src/background.js",
  "src/popup/popup.js",
  "src/options/options.js",
  "src/content/content.js",
];

const STATIC_ASSETS = [
  "src/popup/popup.html",
  "src/popup/popup.css",
  "src/options/options.html",
  "src/options/options.css",
  "src/content/toast.css",
  "src/icons/icon-16.svg",
  "src/icons/icon-48.svg",
  "src/icons/icon-128.svg",
];

async function buildForTarget(target) {
  const outDir = join(DIST, target);
  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });

  // Copy static assets
  for (const asset of STATIC_ASSETS) {
    const from = join(SRC, asset);
    const to = join(outDir, asset);
    mkdirSync(dirname(to), { recursive: true });
    cpSync(from, to);
  }

  // Copy + adjust manifest
  const manifestSrc =
    target === "firefox"
      ? join(SRC, "manifest.firefox.json")
      : join(SRC, "manifest.json");
  const manifest = JSON.parse(readFileSync(manifestSrc, "utf8"));
  writeFileSync(
    join(outDir, "manifest.json"),
    JSON.stringify(manifest, null, 2),
  );

  // Build entries
  const buildOptions = {
    entryPoints: ENTRIES.map((e) => join(SRC, e)),
    outdir: outDir,
    outbase: SRC,
    bundle: true,
    format: "esm",
    target: target === "firefox" ? "firefox115" : "chrome114",
    platform: "browser",
    minify: !isWatch,
    sourcemap: isWatch ? "inline" : false,
    logLevel: "info",
    legalComments: "none",
  };

  // Firefox MV3 SW is still `scripts:[...]` (not ESM module); we emit IIFE
  // for background.js when target=firefox, ESM for chrome.
  if (target === "firefox") {
    // Build background as IIFE
    await esbuild.build({
      ...buildOptions,
      entryPoints: [join(SRC, "src/background.js")],
      format: "iife",
    });
    // Build the rest as ESM
    await esbuild.build({
      ...buildOptions,
      entryPoints: ENTRIES.filter((e) => e !== "src/background.js").map((e) =>
        join(SRC, e),
      ),
    });
  } else {
    if (isWatch) {
      const ctx = await esbuild.context(buildOptions);
      await ctx.watch();
      console.log(`[${target}] watching for changes…`);
      // Keep process alive
      await new Promise(() => {});
    } else {
      await esbuild.build(buildOptions);
    }
  }

  console.log(`[${target}] built → ${outDir}`);

  if (isPackage && !isWatch) {
    await packageZip(outDir, target);
  }
}

async function packageZip(outDir, target) {
  const { execSync } = await import("node:child_process");
  const zipPath = join(DIST, `${target}.zip`);
  rmSync(zipPath, { force: true });
  // Use system `zip` if available; else node tarball as fallback.
  try {
    execSync(`cd "${outDir}" && zip -qr "${zipPath}" .`, { stdio: "inherit" });
    console.log(`[${target}] packaged → ${zipPath}`);
  } catch {
    console.warn(`[${target}] zip command unavailable; skipping package`);
  }
}

for (const target of targets) {
  await buildForTarget(target);
}
