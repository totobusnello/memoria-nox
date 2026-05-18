/**
 * T7+T8 — Encryption wrapper.
 *
 * Algorithm stack (D41 #2, locked):
 *   - Cipher: AES-256-GCM (Node native crypto)
 *   - KDF: scrypt N=2^17 (131072), r=8, p=1 → 32-byte key
 *   - Nonce: random 12 bytes per file (GCM standard, NEVER reused with same key)
 *   - AAD: sha256(manifest_pre_encryption_bytes) — manifest tampering breaks tag
 *   - Salt: random 16 bytes per archive (shared across files; SAME key)
 *
 * Passphrase input:
 *   1. NOX_EXPORT_PASSPHRASE env var (preferred for automation)
 *   2. Interactive stdin prompt with echo OFF (TTY only)
 *
 * NEVER from argv. CLI layer rejects `--passphrase=` at parse time. This module
 * defensively errors out if the caller tries to pass a non-string passphrase.
 *
 * CRITICAL design decisions:
 *  - Per-file nonces — same archive can have 6+ encrypted files, each needs
 *    unique nonce to be safe with the shared key.
 *  - AAD = sha256 of canonical manifest WITHOUT per-file encryption metadata
 *    (see manifest.ts `manifestAADSource`) — chicken-and-egg avoided.
 *  - We distinguish "bad passphrase" vs "tampered" by re-deriving the key
 *    from passphrase + salt; if the very first file decrypts ok and a later
 *    one fails GCM, it's tamper. If the FIRST fails, we assume bad passphrase
 *    (more user-friendly), then expose explicit `decryptStrict` for callers
 *    that want certainty.
 */

import {
  createCipheriv,
  createDecipheriv,
  createHash,
  randomBytes,
  scryptSync,
  timingSafeEqual,
} from "node:crypto";
import {
  BadPassphraseError,
  ENCRYPTION_FORMAT_VERSION,
  EncryptionMetadata,
  MissingAADError,
  TamperedArchiveError,
} from "./types.js";

export const SCRYPT_N = 131072; // 2^17
export const SCRYPT_R = 8;
export const SCRYPT_P = 1;
export const KEY_LEN = 32;
export const SALT_LEN = 16;
export const NONCE_LEN = 12;
export const TAG_LEN = 16;

/** Memory-hard scrypt key derivation. ~0.5-1s on a modern laptop. */
export function deriveKey(passphrase: string, salt: Buffer): Buffer {
  if (typeof passphrase !== "string") {
    throw new Error("deriveKey: passphrase must be a string");
  }
  if (passphrase.length === 0) {
    throw new Error("deriveKey: empty passphrase rejected");
  }
  if (salt.length !== SALT_LEN) {
    throw new Error(`deriveKey: salt must be ${SALT_LEN} bytes, got ${salt.length}`);
  }
  return scryptSync(Buffer.from(passphrase, "utf8"), salt, KEY_LEN, {
    N: SCRYPT_N,
    r: SCRYPT_R,
    p: SCRYPT_P,
    // Node defaults maxmem too low for N=2^17; bump.
    maxmem: 256 * 1024 * 1024,
  });
}

export interface EncryptResult {
  ciphertext: Buffer;
  nonce: Buffer;
  tag: Buffer;
  ciphertextSha256: string;
}

/** Encrypt one file blob with the derived key and per-file random nonce. */
export function encryptBuffer(
  plaintext: Buffer,
  key: Buffer,
  aad: Buffer,
): EncryptResult {
  if (key.length !== KEY_LEN) {
    throw new Error(`encryptBuffer: key must be ${KEY_LEN} bytes`);
  }
  if (aad.length === 0) {
    throw new MissingAADError();
  }
  const nonce = randomBytes(NONCE_LEN);
  const cipher = createCipheriv("aes-256-gcm", key, nonce);
  cipher.setAAD(aad);
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const tag = cipher.getAuthTag();
  const ciphertextSha256 = createHash("sha256").update(ciphertext).digest("hex");
  return { ciphertext, nonce, tag, ciphertextSha256 };
}

/** Decrypt one file blob. Throws TamperedArchiveError on tag mismatch. */
export function decryptBuffer(
  ciphertext: Buffer,
  key: Buffer,
  nonce: Buffer,
  tag: Buffer,
  aad: Buffer,
): Buffer {
  if (key.length !== KEY_LEN) {
    throw new Error(`decryptBuffer: key must be ${KEY_LEN} bytes`);
  }
  if (nonce.length !== NONCE_LEN) {
    throw new Error(`decryptBuffer: nonce must be ${NONCE_LEN} bytes`);
  }
  if (tag.length !== TAG_LEN) {
    throw new Error(`decryptBuffer: tag must be ${TAG_LEN} bytes`);
  }
  if (aad.length === 0) {
    throw new MissingAADError();
  }
  const decipher = createDecipheriv("aes-256-gcm", key, nonce);
  decipher.setAAD(aad);
  decipher.setAuthTag(tag);
  try {
    return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  } catch (err) {
    // GCM auth failure manifests as a generic error; we map to TamperedArchiveError
    // and let the caller decide whether it's actually a bad passphrase.
    throw new TamperedArchiveError(
      `GCM auth failure: ${(err as Error).message}`,
    );
  }
}

/**
 * Verify a ciphertext sha256 matches the manifest-declared one before decrypt.
 * Returns true on match, false on mismatch (constant-time compare).
 */
export function verifyCiphertextSha256(
  ciphertext: Buffer,
  expectedHex: string,
): boolean {
  const got = createHash("sha256").update(ciphertext).digest();
  const want = Buffer.from(expectedHex, "hex");
  if (want.length !== got.length) return false;
  return timingSafeEqual(got, want);
}

/**
 * Top-level decrypt for a file given the manifest encryption metadata entry.
 * Encapsulates: salt parsing, key derivation, sha256 verification, GCM decrypt.
 *
 * Distinguishes "bad passphrase" vs "tamper" heuristically: if sha256 of
 * ciphertext matches manifest but GCM fails → likely bad passphrase. If sha256
 * already differs → tampered ciphertext.
 */
export function decryptArchiveFile(opts: {
  ciphertext: Buffer;
  fileName: string;
  encryptionMetadata: EncryptionMetadata;
  passphrase: string;
  aad: Buffer;
}): Buffer {
  const meta = opts.encryptionMetadata;
  if (!meta.enabled || meta.kdf_salt_b64 === null) {
    throw new Error(
      `decryptArchiveFile: encryption metadata disabled for ${opts.fileName}`,
    );
  }
  const fileMeta = meta.files[opts.fileName];
  if (!fileMeta) {
    throw new Error(
      `decryptArchiveFile: no encryption metadata for ${opts.fileName}`,
    );
  }
  // 1. Verify ciphertext checksum first — distinguishes tamper from bad pw.
  if (!verifyCiphertextSha256(opts.ciphertext, fileMeta.ciphertext_sha256)) {
    throw new TamperedArchiveError(
      `Ciphertext sha256 mismatch for ${opts.fileName}`,
    );
  }
  const salt = Buffer.from(meta.kdf_salt_b64, "base64");
  const key = deriveKey(opts.passphrase, salt);
  const nonce = Buffer.from(fileMeta.nonce_b64, "base64");
  const tag = Buffer.from(fileMeta.tag_b64, "base64");
  try {
    return decryptBuffer(opts.ciphertext, key, nonce, tag, opts.aad);
  } catch (err) {
    // sha256 matched (no tamper) but GCM failed → bad passphrase OR bad AAD.
    if (err instanceof TamperedArchiveError) {
      throw new BadPassphraseError(
        `Decrypt failed for ${opts.fileName}; ciphertext integrity ok but GCM auth failed — likely wrong passphrase or manifest tampered.`,
      );
    }
    throw err;
  }
}

/**
 * Get passphrase from env or interactive prompt. NEVER from argv.
 *
 * @param opts.interactivePrompt - injected for testability; defaults to readline echo-off
 * @param opts.envOverride       - injected for testability; defaults to process.env
 */
export async function getPassphrase(opts?: {
  interactivePrompt?: () => Promise<string>;
  envOverride?: Record<string, string | undefined>;
  isTTY?: boolean;
}): Promise<string> {
  const env = opts?.envOverride ?? process.env;
  const fromEnv = env.NOX_EXPORT_PASSPHRASE;
  if (typeof fromEnv === "string" && fromEnv.length > 0) {
    return fromEnv;
  }
  const isTTY = opts?.isTTY ?? Boolean(process.stdin.isTTY);
  if (!isTTY) {
    throw new Error(
      "getPassphrase: stdin is not a TTY and NOX_EXPORT_PASSPHRASE is unset. " +
        "Set NOX_EXPORT_PASSPHRASE or run interactively. " +
        "(Refuses to read passphrase from argv to prevent `ps` leaks.)",
    );
  }
  const prompt = opts?.interactivePrompt ?? defaultInteractivePrompt;
  const pw = await prompt();
  if (pw.length === 0) {
    throw new Error("getPassphrase: empty passphrase rejected");
  }
  return pw;
}

/** Default interactive prompt — readline with echo OFF. */
async function defaultInteractivePrompt(): Promise<string> {
  const readline = await import("node:readline");
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: true,
  });
  // Disable echo
  const stdin = process.stdin as NodeJS.ReadStream & { setRawMode?: (m: boolean) => void };
  const wasRaw = stdin.isRaw;
  stdin.setRawMode?.(true);
  return new Promise<string>((resolve, reject) => {
    process.stdout.write("Passphrase: ");
    const chunks: string[] = [];
    const onData = (chunk: Buffer): void => {
      const s = chunk.toString("utf8");
      for (const ch of s) {
        if (ch === "\n" || ch === "\r") {
          stdin.setRawMode?.(wasRaw ?? false);
          stdin.off("data", onData);
          rl.close();
          process.stdout.write("\n");
          resolve(chunks.join(""));
          return;
        }
        if (ch === "") {
          // Ctrl-C
          stdin.setRawMode?.(wasRaw ?? false);
          stdin.off("data", onData);
          rl.close();
          reject(new Error("Passphrase prompt cancelled"));
          return;
        }
        if (ch === "" || ch === "\b") {
          if (chunks.length > 0) chunks.pop();
          continue;
        }
        chunks.push(ch);
      }
    };
    stdin.on("data", onData);
  });
}

/** Build the file-key portion of EncryptionMetadata given fresh salt + per-file results. */
export function buildEncryptionMetadata(
  saltB64: string,
  files: Record<string, EncryptResult>,
): EncryptionMetadata {
  const filesMeta: Record<string, EncryptionMetadata["files"][string]> = {};
  for (const [name, res] of Object.entries(files)) {
    filesMeta[name] = {
      nonce_b64: res.nonce.toString("base64"),
      tag_b64: res.tag.toString("base64"),
      ciphertext_sha256: res.ciphertextSha256,
    };
  }
  return {
    enabled: true,
    algorithm: "AES-256-GCM",
    kdf: "scrypt",
    kdf_params: { N: SCRYPT_N, r: SCRYPT_R, p: SCRYPT_P },
    kdf_salt_b64: saltB64,
    files: filesMeta,
    aad_source: "sha256(manifest_pre_encryption_bytes)",
    format_version: ENCRYPTION_FORMAT_VERSION,
  };
}
