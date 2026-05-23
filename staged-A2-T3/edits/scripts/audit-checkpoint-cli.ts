#!/usr/bin/env node
// staged-A2-T3/edits/scripts/audit-checkpoint-cli.ts
//
// A2 Tier 3 / Phase 4 — Ed25519 signed audit-checkpoint CLI.
//
// Subcommands:
//   gen-key      → emit a fresh Ed25519 keypair to two files (public + private)
//   create       → create a checkpoint over <scope>_audit, sign with key
//   verify       → verify a single checkpoint by id
//   verify-chain → verify all checkpoints in a scope (or 'all')
//
// All commands resolve NOX_DB_PATH + NOX_DB_KEY from env (same convention as
// reads-audit-sweep). The DB schema bootstrap is idempotent.
//
// Usage:
//   audit-checkpoint gen-key --out-dir /var/lib/nox-mem/keys
//   audit-checkpoint create --scope ops --key-file /var/lib/nox-mem/keys/private.b64
//   audit-checkpoint verify --id 7 --key-file /var/lib/nox-mem/keys/public.b64
//   audit-checkpoint verify-chain --scope ops --key-file /etc/nox-mem/public.b64
//   audit-checkpoint verify-chain --scope all --key-file /etc/nox-mem/public.b64
//
// Files written by gen-key:
//   <out-dir>/audit-checkpoints-private-<fingerprint>.b64  (mode 0600)
//   <out-dir>/audit-checkpoints-public-<fingerprint>.b64   (mode 0644)
//   Each file contains exactly the base64 string (no trailing newline, no
//   header) for trivial parse-back via `readFileSync(path, 'utf8').trim()`.
//
// Exit codes:
//   0 — success / all checkpoints valid
//   1 — usage error (bad args, missing files)
//   2 — runtime failure (DB connection, etc)
//   3 — verification FAILED (chain broken, signature mismatch)

import { readFileSync, writeFileSync, mkdirSync, existsSync, chmodSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createCheckpoint,
  verifyCheckpoint,
  verifyChain,
  generateKeyPair,
  KNOWN_SCOPES,
  type CheckpointScope,
  type ChainResult,
} from '../src/lib/audit-checkpoints.js';

type Args = Record<string, string | boolean>;

function parseArgs(argv: string[]): { cmd: string; args: Args } {
  const args: Args = {};
  if (argv.length < 3) {
    throw new Error('missing subcommand — expected one of: gen-key, create, verify, verify-chain');
  }
  const cmd = argv[2]!;
  for (let i = 3; i < argv.length; i++) {
    const a = argv[i];
    if (!a) continue;
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next == null || next.startsWith('--')) {
        // Boolean flag
        args[key] = true;
      } else {
        args[key] = next;
        i++;
      }
    } else {
      throw new Error(`unexpected positional arg '${a}'`);
    }
  }
  return { cmd, args };
}

// ────────────────────────────────────────────────────────────────────────────
// Subcommand: gen-key
// ────────────────────────────────────────────────────────────────────────────

function cmdGenKey(args: Args): void {
  const outDir = args['out-dir'];
  if (typeof outDir !== 'string') {
    throw new Error('gen-key requires --out-dir <path>');
  }
  if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true, mode: 0o700 });

  const kp = generateKeyPair();
  const privPath = resolve(outDir, `audit-checkpoints-private-${kp.publicKeyFingerprint}.b64`);
  const pubPath = resolve(outDir, `audit-checkpoints-public-${kp.publicKeyFingerprint}.b64`);

  writeFileSync(privPath, kp.privateKey, { encoding: 'utf8', mode: 0o600 });
  writeFileSync(pubPath, kp.publicKey, { encoding: 'utf8', mode: 0o644 });
  // Defensive chmod (writeFileSync mode is best-effort on some platforms).
  try { chmodSync(privPath, 0o600); } catch { /* best-effort */ }
  try { chmodSync(pubPath, 0o644); } catch { /* best-effort */ }

  console.log(JSON.stringify({
    status: 'ok',
    public_key_fingerprint: kp.publicKeyFingerprint,
    private_key_path: privPath,
    public_key_path: pubPath,
    next_steps: [
      `Publish public key in docs/AUDIT-PUBKEY.md (fingerprint: ${kp.publicKeyFingerprint})`,
      `Move private key off-box (laptop + offline backup); never commit to git`,
      `Set NOX_AUDIT_CHECKPOINT_PUBKEY=<public_key_b64> in /root/.openclaw/.env for verifier reuse`,
    ],
  }, null, 2));
}

// ────────────────────────────────────────────────────────────────────────────
// Subcommand: create
// ────────────────────────────────────────────────────────────────────────────

function cmdCreate(args: Args): void {
  const scope = args['scope'];
  const keyFile = args['key-file'];
  if (scope !== 'ops' && scope !== 'reads') {
    throw new Error("create requires --scope (ops|reads)");
  }
  if (typeof keyFile !== 'string') {
    throw new Error('create requires --key-file <path> (Ed25519 private key, base64 raw 32 bytes)');
  }
  if (!process.env.NOX_DB_PATH) {
    throw new Error('NOX_DB_PATH env var is required');
  }

  const privateKey = readFileSync(keyFile, 'utf8').trim();
  if (privateKey.length === 0) {
    throw new Error(`empty private key file at ${keyFile}`);
  }

  const result = createCheckpoint(scope as CheckpointScope, privateKey);
  if (!result) {
    console.log(JSON.stringify({
      status: 'noop',
      reason: `no new ${scope}_audit rows since last checkpoint (or audit table empty)`,
    }, null, 2));
    return;
  }
  console.log(JSON.stringify({
    status: 'ok',
    ...result,
  }, null, 2));
}

// ────────────────────────────────────────────────────────────────────────────
// Subcommand: verify
// ────────────────────────────────────────────────────────────────────────────

function cmdVerify(args: Args): number {
  const idStr = args['id'];
  const keyFile = args['key-file'];
  if (typeof idStr !== 'string') {
    throw new Error('verify requires --id <integer>');
  }
  if (typeof keyFile !== 'string') {
    throw new Error('verify requires --key-file <path> (Ed25519 public key, base64 raw 32 bytes)');
  }
  const id = Number(idStr);
  if (!Number.isFinite(id) || !Number.isInteger(id) || id <= 0) {
    throw new Error(`--id must be a positive integer, got '${idStr}'`);
  }
  if (!process.env.NOX_DB_PATH) {
    throw new Error('NOX_DB_PATH env var is required');
  }

  const publicKey = readFileSync(keyFile, 'utf8').trim();
  const result = verifyCheckpoint(id, publicKey);
  console.log(JSON.stringify({
    status: result.valid ? 'ok' : 'FAILED',
    id,
    ...result,
  }, null, 2));
  return result.valid ? 0 : 3;
}

// ────────────────────────────────────────────────────────────────────────────
// Subcommand: verify-chain
// ────────────────────────────────────────────────────────────────────────────

function cmdVerifyChain(args: Args): number {
  const scope = args['scope'];
  const keyFile = args['key-file'];
  if (scope !== 'ops' && scope !== 'reads' && scope !== 'all') {
    throw new Error("verify-chain requires --scope (ops|reads|all)");
  }
  if (typeof keyFile !== 'string') {
    throw new Error('verify-chain requires --key-file <path> (Ed25519 public key)');
  }
  if (!process.env.NOX_DB_PATH) {
    throw new Error('NOX_DB_PATH env var is required');
  }

  const publicKey = readFileSync(keyFile, 'utf8').trim();

  const scopes: CheckpointScope[] = scope === 'all'
    ? [...KNOWN_SCOPES]
    : [scope as CheckpointScope];
  const results: Record<string, ChainResult> = {};
  let allValid = true;
  for (const s of scopes) {
    const r = verifyChain(s, publicKey);
    results[s] = r;
    if (r.broken > 0) allValid = false;
  }
  console.log(JSON.stringify({
    status: allValid ? 'ok' : 'FAILED',
    scopes: results,
  }, null, 2));
  return allValid ? 0 : 3;
}

// ────────────────────────────────────────────────────────────────────────────
// Main dispatch
// ────────────────────────────────────────────────────────────────────────────

function main(): number {
  let parsed: { cmd: string; args: Args };
  try {
    parsed = parseArgs(process.argv);
  } catch (err) {
    console.error(`[audit-checkpoint] usage error: ${(err as Error).message}`);
    printHelp();
    return 1;
  }
  const { cmd, args } = parsed;
  try {
    switch (cmd) {
      case 'gen-key':
        cmdGenKey(args);
        return 0;
      case 'create':
        cmdCreate(args);
        return 0;
      case 'verify':
        return cmdVerify(args);
      case 'verify-chain':
        return cmdVerifyChain(args);
      case '--help':
      case '-h':
      case 'help':
        printHelp();
        return 0;
      default:
        console.error(`[audit-checkpoint] unknown subcommand '${cmd}'`);
        printHelp();
        return 1;
    }
  } catch (err) {
    console.error(`[audit-checkpoint] runtime error: ${(err as Error).message}`);
    return 2;
  }
}

function printHelp(): void {
  console.log(
    'audit-checkpoint — A2 Tier 3 / Phase 4 — Ed25519 signed forensic checkpoints\n' +
    '\n' +
    'Usage:\n' +
    '  audit-checkpoint gen-key      --out-dir <path>\n' +
    '  audit-checkpoint create       --scope <ops|reads>   --key-file <private.b64>\n' +
    '  audit-checkpoint verify       --id <int>            --key-file <public.b64>\n' +
    '  audit-checkpoint verify-chain --scope <ops|reads|all> --key-file <public.b64>\n' +
    '\n' +
    'Env:\n' +
    '  NOX_DB_PATH   — required for create / verify / verify-chain\n' +
    '  NOX_DB_KEY    — optional SQLCipher key for at-rest encrypted DB\n' +
    '\n' +
    'Exit codes:\n' +
    '  0 — success / all checkpoints valid\n' +
    '  1 — usage error\n' +
    '  2 — runtime failure (DB connection, key parse, etc)\n' +
    '  3 — verification FAILED (chain broken, signature mismatch)\n',
  );
}

// Entry-point guard — only run when executed directly (not when imported by
// tests). Classic ESM idiom (mirrors reads-audit-sweep.ts).
const isMain = (() => {
  try {
    return import.meta.url === `file://${process.argv[1]}` || import.meta.url.endsWith(process.argv[1] ?? '');
  } catch { return false; }
})();

if (isMain) {
  const code = main();
  process.exit(code);
}

// Exports for tests
export { parseArgs, main as runMain, cmdGenKey, cmdCreate, cmdVerify, cmdVerifyChain };
