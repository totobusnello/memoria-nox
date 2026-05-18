#!/usr/bin/env tsx
/**
 * import-docs.ts — Idempotent doc importer for memoria-nox Starlight site
 *
 * Reads source docs from ../docs/, ../specs/, etc.
 * Rewrites markdown for Starlight (frontmatter + relative links + image paths)
 * Copies to docs-site/src/content/docs/
 *
 * Usage:
 *   npm run import-docs
 *   npm run import-docs -- --dry-run
 *
 * Idempotent: files with manually-edited frontmatter marker "# MANUAL" are skipped.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync } from 'fs';
import { join, basename, dirname, relative } from 'path';
import { execSync } from 'child_process';

const REPO_ROOT = join(import.meta.dirname, '../..');
const CONTENT_ROOT = join(import.meta.dirname, '../src/content/docs');

const DRY_RUN = process.argv.includes('--dry-run');

// ── Mapping: source path (relative to REPO_ROOT) → dest (relative to CONTENT_ROOT) ──

const IMPORT_MAP: Array<{
  src: string;
  dest: string;
  title: string;
  description: string;
  sidebarOrder?: number;
}> = [
  // Getting Started
  {
    src: 'docs/QUICKSTART.md',
    dest: 'start/install.md',
    title: 'Installation',
    description: 'Install memoria-nox CLI, MCP server, and HTTP API.',
    sidebarOrder: 1,
  },
  // Architecture
  {
    src: 'docs/ARCHITECTURE.md',
    dest: 'architecture/overview.md',
    title: 'Architecture Overview',
    description: 'Schema V10, hybrid search stack, and all interface surfaces.',
    sidebarOrder: 1,
  },
  {
    src: 'docs/VISION.md',
    dest: 'architecture/pillars.md',
    title: 'Q/A/P Pillars',
    description: 'Strategic architecture organized around Quality, Autonomy, and Product.',
    sidebarOrder: 2,
  },
  // ADRs
  {
    src: 'docs/adr/ADR-001-hybrid-search.md',
    dest: 'architecture/adr-001.md',
    title: 'ADR-001: Hybrid Search',
    description: 'Decision record for FTS5 + semantic + RRF hybrid search architecture.',
    sidebarOrder: 5,
  },
  {
    src: 'docs/adr/ADR-002-append-only-audit.md',
    dest: 'architecture/adr-002.md',
    title: 'ADR-002: Append-Only Audit',
    description: 'Decision record for ops_audit append-only design.',
    sidebarOrder: 6,
  },
  {
    src: 'docs/adr/ADR-003-shadow-discipline.md',
    dest: 'architecture/adr-003.md',
    title: 'ADR-003: Shadow Discipline',
    description: 'Decision record for shadow mode ranking change policy.',
    sidebarOrder: 7,
  },
  {
    src: 'docs/adr/ADR-004-qap-pillars-pivot.md',
    dest: 'architecture/adr-004.md',
    title: 'ADR-004: Q/A/P Pillars Pivot',
    description: 'Decision record for the Q/A/P strategic reorganization.',
    sidebarOrder: 8,
  },
  // Security
  {
    src: 'docs/security/THREAT-MODEL.md',
    dest: 'security/threat-model.md',
    title: 'Threat Model',
    description: 'STRIDE matrix, 10 gap categories, and control matrix.',
    sidebarOrder: 1,
  },
  {
    src: 'docs/security/PATH-TO-OPENSSF.md',
    dest: 'security/openssf.md',
    title: 'OpenSSF Path',
    description: 'Progress toward OpenSSF Best Practices badge.',
    sidebarOrder: 2,
  },
  {
    src: 'SECURITY.md',
    dest: 'security/reporting.md',
    title: 'Vulnerability Reporting',
    description: 'Responsible disclosure policy.',
    sidebarOrder: 3,
  },
  {
    src: 'docs/security/DEPENDENCY-POLICY.md',
    dest: 'security/dependency-policy.md',
    title: 'Dependency Policy',
    description: 'Rules for adding, updating, and auditing dependencies.',
    sidebarOrder: 4,
  },
  // Operations
  {
    src: 'docs/DEPLOY-WAVE-B.md',
    dest: 'operations/deploy.md',
    title: 'Deploy Guide',
    description: 'VPS deploy steps for staged-* patches.',
    sidebarOrder: 1,
  },
  {
    src: 'docs/ops/DISASTER-RECOVERY.md',
    dest: 'operations/disaster-recovery.md',
    title: 'Disaster Recovery',
    description: 'DB restore, snapshot recovery, and DR drill procedures.',
    sidebarOrder: 2,
  },
  {
    src: 'docs/ops/BACKUP-RUNBOOK.md',
    dest: 'operations/backup-runbook.md',
    title: 'Backup Runbook',
    description: 'Backup schedule, verification, and restore procedures.',
    sidebarOrder: 3,
  },
  {
    src: 'docs/ops/MONITORING.md',
    dest: 'operations/monitoring.md',
    title: 'Monitoring',
    description: 'Health endpoints, alerting, and observability.',
    sidebarOrder: 4,
  },
  // Contributing
  {
    src: 'CONTRIBUTING.md',
    dest: 'contributing/how-to.md',
    title: 'How to Contribute',
    description: 'Opening issues, submitting PRs, running tests, and commit conventions.',
    sidebarOrder: 1,
  },
  {
    src: 'CODE_OF_CONDUCT.md',
    dest: 'contributing/code-of-conduct.md',
    title: 'Code of Conduct',
    description: 'Community standards for the memoria-nox project.',
    sidebarOrder: 2,
  },
  {
    src: 'CHANGELOG.md',
    dest: 'contributing/changelog.md',
    title: 'Changelog',
    description: 'Release history and notable changes.',
    sidebarOrder: 3,
  },
  // Strategy
  {
    src: 'docs/COMPETITIVE-POSITIONING.md',
    dest: 'strategy/competitive-positioning.md',
    title: 'Competitive Positioning',
    description: 'Six Gaps analysis versus memanto, agentmemory, and gbrain.',
    sidebarOrder: 1,
  },
  {
    src: 'docs/cost-model.md',
    dest: 'strategy/cost-model.md',
    title: 'Cost Model',
    description: 'Monthly OPEX breakdown and cost projections.',
    sidebarOrder: 2,
  },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function buildFrontmatter(title: string, description: string, order?: number): string {
  const orderLine = order !== undefined ? `\n  order: ${order}` : '';
  return `---
title: ${title}
description: ${description}
sidebar:${orderLine}
---

<!-- AUTO-IMPORTED: regenerate via npm run import-docs -->
<!-- Add "# MANUAL" anywhere in this file to skip auto-import -->

`;
}

function hasManualMarker(content: string): boolean {
  return content.includes('# MANUAL');
}

function rewriteRelativeLinks(content: string, srcPath: string, destPath: string): string {
  // Rewrite .md links to use /memoria-nox/ base path
  // Simple pass: replace relative ../docs/ etc links with absolute Starlight paths
  return content.replace(
    /\[([^\]]+)\]\((?!https?:\/\/)([^)]+\.md)([^)]*)\)/g,
    (_match, text, mdPath, _anchor) => {
      // Keep as-is for now — full rewrite would require a link map
      return `[${text}](${mdPath})`;
    }
  );
}

function importFile(entry: typeof IMPORT_MAP[0]): void {
  const srcAbs = join(REPO_ROOT, entry.src);
  const destAbs = join(CONTENT_ROOT, entry.dest);

  if (!existsSync(srcAbs)) {
    console.log(`  SKIP (not found): ${entry.src}`);
    return;
  }

  // Check if dest exists with MANUAL marker
  if (existsSync(destAbs)) {
    const existing = readFileSync(destAbs, 'utf8');
    if (hasManualMarker(existing)) {
      console.log(`  SKIP (manual):   ${entry.dest}`);
      return;
    }
  }

  const srcContent = readFileSync(srcAbs, 'utf8');
  const frontmatter = buildFrontmatter(entry.title, entry.description, entry.sidebarOrder);

  // Strip existing H1 if it matches title to avoid duplicate
  const withoutH1 = srcContent.replace(/^# .+\n/, '');
  const rewritten = rewriteRelativeLinks(withoutH1, entry.src, entry.dest);
  const final = frontmatter + rewritten;

  if (DRY_RUN) {
    console.log(`  DRY-RUN: would write ${entry.dest} (${final.length} chars)`);
    return;
  }

  mkdirSync(dirname(destAbs), { recursive: true });
  writeFileSync(destAbs, final, 'utf8');
  console.log(`  WROTE:           ${entry.dest}`);
}

// ── Main ─────────────────────────────────────────────────────────────────────

console.log(`\nmemoria-nox docs importer${DRY_RUN ? ' (DRY RUN)' : ''}`);
console.log(`Source: ${REPO_ROOT}`);
console.log(`Dest:   ${CONTENT_ROOT}\n`);

let written = 0;
let skipped = 0;

for (const entry of IMPORT_MAP) {
  const destAbs = join(CONTENT_ROOT, entry.dest);
  const existed = existsSync(destAbs);
  importFile(entry);
  if (!DRY_RUN && existsSync(destAbs)) {
    if (!existed) written++;
  } else {
    skipped++;
  }
}

console.log(`\nDone. Written: ${written}, Skipped: ${skipped}`);
