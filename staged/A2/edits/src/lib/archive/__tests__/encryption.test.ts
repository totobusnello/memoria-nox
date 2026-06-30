/**
 * T7+T8 — encryption tests.
 *
 * Covers: round-trip, GCM tag tamper detection, AAD divergence, ciphertext
 * sha256 mismatch, passphrase source isolation (env vs argv refusal).
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createHash, randomBytes } from "node:crypto";
import {
  buildEncryptionMetadata,
  decryptArchiveFile,
  decryptBuffer,
  deriveKey,
  encryptBuffer,
  getPassphrase,
  KEY_LEN,
  SALT_LEN,
  verifyCiphertextSha256,
} from "../encryption.js";
import {
  BadPassphraseError,
  MissingAADError,
  TamperedArchiveError,
} from "../types.js";

describe("encryption / deriveKey + scrypt", () => {
  it("derives a 32-byte key from passphrase + salt", () => {
    const salt = randomBytes(SALT_LEN);
    const key = deriveKey("test-passphrase-16ch", salt);
    assert.equal(key.length, KEY_LEN);
  });

  it("is deterministic for same (passphrase, salt)", () => {
    const salt = Buffer.alloc(SALT_LEN, 7);
    const a = deriveKey("hello", salt);
    const b = deriveKey("hello", salt);
    assert.equal(a.toString("hex"), b.toString("hex"));
  });

  it("yields different keys for different salts", () => {
    const a = deriveKey("hello", Buffer.alloc(SALT_LEN, 1));
    const b = deriveKey("hello", Buffer.alloc(SALT_LEN, 2));
    assert.notEqual(a.toString("hex"), b.toString("hex"));
  });

  it("rejects empty passphrase", () => {
    assert.throws(() => deriveKey("", Buffer.alloc(SALT_LEN, 0)), /empty/);
  });
});

describe("encryption / encrypt + decrypt round-trip", () => {
  it("round-trips a plaintext buffer byte-identically", () => {
    const key = randomBytes(KEY_LEN);
    const aad = Buffer.from("aad bytes");
    const plaintext = Buffer.from("secret chunk content with PII", "utf8");
    const enc = encryptBuffer(plaintext, key, aad);
    const back = decryptBuffer(enc.ciphertext, key, enc.nonce, enc.tag, aad);
    assert.equal(back.toString("utf8"), plaintext.toString("utf8"));
  });

  it("rejects empty AAD on encrypt (encrypt-by-default invariant)", () => {
    const key = randomBytes(KEY_LEN);
    assert.throws(
      () => encryptBuffer(Buffer.from("x"), key, Buffer.alloc(0)),
      MissingAADError,
    );
  });

  it("rejects empty AAD on decrypt", () => {
    const key = randomBytes(KEY_LEN);
    const aad = Buffer.from("aad");
    const enc = encryptBuffer(Buffer.from("x"), key, aad);
    assert.throws(
      () => decryptBuffer(enc.ciphertext, key, enc.nonce, enc.tag, Buffer.alloc(0)),
      MissingAADError,
    );
  });
});

describe("encryption / tamper detection", () => {
  const aad = Buffer.from("aad-bytes-fixed");
  const key = Buffer.alloc(KEY_LEN, 7);
  const plaintext = Buffer.from("this is a chunk that must never leak", "utf8");

  it("detects ciphertext tamper via GCM tag", () => {
    const enc = encryptBuffer(plaintext, key, aad);
    // Flip one byte
    enc.ciphertext[5] = enc.ciphertext[5]! ^ 0xff;
    assert.throws(
      () => decryptBuffer(enc.ciphertext, key, enc.nonce, enc.tag, aad),
      TamperedArchiveError,
    );
  });

  it("detects AAD tamper via GCM tag", () => {
    const enc = encryptBuffer(plaintext, key, aad);
    const tamperedAAD = Buffer.from("aad-bytes-fixxed");
    assert.throws(
      () => decryptBuffer(enc.ciphertext, key, enc.nonce, enc.tag, tamperedAAD),
      TamperedArchiveError,
    );
  });

  it("detects tag tamper", () => {
    const enc = encryptBuffer(plaintext, key, aad);
    const badTag = Buffer.from(enc.tag);
    badTag[0] = badTag[0]! ^ 0xff;
    assert.throws(
      () => decryptBuffer(enc.ciphertext, key, enc.nonce, badTag, aad),
      TamperedArchiveError,
    );
  });

  it("strings ciphertext does not contain plaintext content", () => {
    // Smoke test for "encryption is real, not cosmetic". (DoD #3)
    const enc = encryptBuffer(plaintext, key, aad);
    const asString = enc.ciphertext.toString("latin1");
    assert.ok(!asString.includes("this is a chunk"),
      "ciphertext leaked plaintext substring");
    assert.ok(!asString.includes("never leak"),
      "ciphertext leaked plaintext tail");
  });
});

describe("encryption / verifyCiphertextSha256", () => {
  it("returns true for matching hash", () => {
    const ct = Buffer.from("hello");
    const hex = createHash("sha256").update(ct).digest("hex");
    assert.equal(verifyCiphertextSha256(ct, hex), true);
  });

  it("returns false for tampered ciphertext", () => {
    const ct = Buffer.from("hello");
    assert.equal(verifyCiphertextSha256(ct, "a".repeat(64)), false);
  });

  it("returns false for malformed expected hex", () => {
    assert.equal(verifyCiphertextSha256(Buffer.from("x"), "abc"), false);
  });
});

describe("encryption / decryptArchiveFile (full flow)", () => {
  it("end-to-end: encrypt → metadata → decryptArchiveFile", () => {
    const salt = Buffer.alloc(SALT_LEN, 3);
    const passphrase = "supersecret-passphrase-1234";
    const key = deriveKey(passphrase, salt);
    const aad = Buffer.from("manifest-aad-hash");
    const plaintext = Buffer.from("private chunk content", "utf8");
    const enc = encryptBuffer(plaintext, key, aad);
    const meta = buildEncryptionMetadata(
      salt.toString("base64"),
      { "chunks.jsonl.enc": enc },
    );
    const back = decryptArchiveFile({
      ciphertext: enc.ciphertext,
      fileName: "chunks.jsonl.enc",
      encryptionMetadata: meta,
      passphrase,
      aad,
    });
    assert.equal(back.toString("utf8"), plaintext.toString("utf8"));
  });

  it("BadPassphraseError when sha256 ok but key wrong", () => {
    const salt = Buffer.alloc(SALT_LEN, 3);
    const realPass = "good-passphrase-12345";
    const badPass = "wrong-passphrase-99999";
    const aad = Buffer.from("aad");
    const key = deriveKey(realPass, salt);
    const enc = encryptBuffer(Buffer.from("secret"), key, aad);
    const meta = buildEncryptionMetadata(salt.toString("base64"), {
      "chunks.jsonl.enc": enc,
    });
    assert.throws(
      () =>
        decryptArchiveFile({
          ciphertext: enc.ciphertext,
          fileName: "chunks.jsonl.enc",
          encryptionMetadata: meta,
          passphrase: badPass,
          aad,
        }),
      BadPassphraseError,
    );
  });

  it("TamperedArchiveError when ciphertext sha256 differs", () => {
    const salt = Buffer.alloc(SALT_LEN, 3);
    const passphrase = "p";
    const aad = Buffer.from("aad");
    const key = deriveKey(passphrase, salt);
    const enc = encryptBuffer(Buffer.from("secret"), key, aad);
    const meta = buildEncryptionMetadata(salt.toString("base64"), {
      "chunks.jsonl.enc": enc,
    });
    // Flip a byte AFTER metadata is built (manifest still references old sha256)
    const tampered = Buffer.from(enc.ciphertext);
    tampered[0] = tampered[0]! ^ 0xff;
    assert.throws(
      () =>
        decryptArchiveFile({
          ciphertext: tampered,
          fileName: "chunks.jsonl.enc",
          encryptionMetadata: meta,
          passphrase,
          aad,
        }),
      TamperedArchiveError,
    );
  });
});

describe("encryption / getPassphrase", () => {
  it("reads from NOX_EXPORT_PASSPHRASE env", async () => {
    const pw = await getPassphrase({
      envOverride: { NOX_EXPORT_PASSPHRASE: "from-env-12345" },
    });
    assert.equal(pw, "from-env-12345");
  });

  it("errors if no env and no TTY (never accepts argv)", async () => {
    await assert.rejects(
      () => getPassphrase({ envOverride: {}, isTTY: false }),
      /TTY/,
    );
  });

  it("uses injected prompt when TTY + env unset", async () => {
    const pw = await getPassphrase({
      envOverride: {},
      isTTY: true,
      interactivePrompt: async () => "interactive-pw-12345",
    });
    assert.equal(pw, "interactive-pw-12345");
  });

  it("rejects empty interactive passphrase", async () => {
    await assert.rejects(
      () =>
        getPassphrase({
          envOverride: {},
          isTTY: true,
          interactivePrompt: async () => "",
        }),
      /empty/,
    );
  });
});
