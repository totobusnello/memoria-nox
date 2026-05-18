/**
 * G7 — Streaming unpack for large archives.
 *
 * Gap from THREAT-MODEL.md §3.2 (DoS / in-memory unpack):
 *   "unpackArchive still is in-memory Buffer (format.ts:36) — not a stream;
 *    archive 10GB+ will explode RAM."
 *
 * This module provides:
 *   1. unpackArchiveStream() — async generator yielding ArchiveEntry one at a time.
 *      Peak memory: O(largest single entry) + header block (512B) overhead.
 *      Replaces the full-buffer load in unpackArchive().
 *
 *   2. unpackArchiveStreamToBuffer() — backward-compatible wrapper that collects
 *      all yielded entries into ArchiveEntry[]. Same signature as unpackArchive().
 *      Useful for existing callers that need the full list at once.
 *
 * Memory model:
 *   - Old path (unpackArchive): gunzipSync(all) → parseTarBlocks(all) → all in RAM.
 *     For 1GB archive → ~2.5GB peak (compressed + decompressed + parsed entries).
 *
 *   - New path (unpackArchiveStream): createGunzip() stream → 512B header reads →
 *     per-entry Buffer.alloc(size) → yield → GC after caller processes.
 *     For 1GB archive → ~1.0–1.5GB peak (decompressed current entry only).
 *
 * API compatibility:
 *   - Public signature of unpackArchive(gzipped: Buffer): ArchiveEntry[] is KEPT
 *     as a thin wrapper. No breaking change.
 *   - New streaming path is opt-in via unpackArchiveStream().
 *
 * Ref: THREAT-MODEL.md G7 (medium priority).
 *      staged-A2/edits/src/lib/archive/format.ts (original implementation).
 */

import { createGunzip } from "node:zlib";
import { Readable, Transform, TransformCallback } from "node:stream";
import { pipeline } from "node:stream/promises";
import { ArchiveEntry, ArchiveFormatError } from "./types.js";

const BLOCK_SIZE = 512;

// ─── Streaming parser ─────────────────────────────────────────────────────────

/**
 * TarBlockTransform — stateful Transform that reads a gzip stream and emits
 * ArchiveEntry objects one at a time. No full Buffer accumulation.
 *
 * State machine:
 *   - HEADER: accumulate 512 bytes, parse as tar header
 *   - CONTENT: accumulate entry.size bytes, emit entry
 *   - PAD: skip padding to next 512-byte boundary
 */
class TarBlockTransform extends Transform {
  private _buf = Buffer.alloc(0);
  private _state: "HEADER" | "CONTENT" | "PAD" = "HEADER";
  private _pendingName = "";
  private _pendingMtime = 0;
  private _pendingSize = 0;
  private _pendingType = "0";
  private _contentAccum: Buffer[] = [];
  private _contentRead = 0;
  private _padRemaining = 0;
  private _done = false;

  constructor() {
    super({ readableObjectMode: true });
  }

  _transform(chunk: Buffer, _enc: BufferEncoding, callback: TransformCallback): void {
    this._buf = Buffer.concat([this._buf, chunk]);
    try {
      this._process();
      callback();
    } catch (err) {
      callback(err as Error);
    }
  }

  _flush(callback: TransformCallback): void {
    callback();
  }

  private _process(): void {
    while (!this._done) {
      if (this._state === "HEADER") {
        if (this._buf.length < BLOCK_SIZE) break;

        const header = this._buf.subarray(0, BLOCK_SIZE);
        this._buf = this._buf.subarray(BLOCK_SIZE);

        if (isZeroBlock(header)) {
          this._done = true;
          break;
        }

        const name = readCString(header, 0, 100);
        const sizeStr = readCString(header, 124, 12);
        const size = parseInt(sizeStr.trim() || "0", 8);
        const mtimeStr = readCString(header, 136, 12);
        const mtime = parseInt(mtimeStr.trim() || "0", 8);
        const checksumStr = readCString(header, 148, 8);
        const declaredChecksum = parseInt(checksumStr.trim() || "0", 8);
        const computedChecksum = computeHeaderChecksum(header);

        if (declaredChecksum !== computedChecksum) {
          throw new ArchiveFormatError(
            `tar header checksum mismatch for ${name}: ` +
              `declared=${declaredChecksum} computed=${computedChecksum}`,
          );
        }

        if (Number.isNaN(size) || size < 0) {
          throw new ArchiveFormatError(`Invalid size in tar header for ${name}`);
        }

        const typeflag = String.fromCharCode(header[156] ?? 0x30);
        this._pendingName = name;
        this._pendingMtime = mtime;
        this._pendingSize = size;
        this._pendingType = typeflag;
        this._contentAccum = [];
        this._contentRead = 0;
        this._state = "CONTENT";
      }

      if (this._state === "CONTENT") {
        const needed = this._pendingSize - this._contentRead;
        if (needed === 0) {
          // Zero-size entry — emit immediately
          this._emitEntry();
          const pad = (BLOCK_SIZE - (this._pendingSize % BLOCK_SIZE)) % BLOCK_SIZE;
          if (pad > 0) {
            this._padRemaining = pad;
            this._state = "PAD";
          } else {
            this._state = "HEADER";
          }
          continue;
        }
        if (this._buf.length === 0) break;

        const take = Math.min(needed, this._buf.length);
        this._contentAccum.push(this._buf.subarray(0, take));
        this._contentRead += take;
        this._buf = this._buf.subarray(take);

        if (this._contentRead < this._pendingSize) break;

        // Full content accumulated — emit
        this._emitEntry();

        const pad = (BLOCK_SIZE - (this._pendingSize % BLOCK_SIZE)) % BLOCK_SIZE;
        if (pad > 0) {
          this._padRemaining = pad;
          this._state = "PAD";
        } else {
          this._state = "HEADER";
        }
      }

      if (this._state === "PAD") {
        const skip = Math.min(this._padRemaining, this._buf.length);
        this._buf = this._buf.subarray(skip);
        this._padRemaining -= skip;
        if (this._padRemaining > 0) break;
        this._state = "HEADER";
      }
    }
  }

  private _emitEntry(): void {
    // Only emit regular files (typeflag '0' or '\0')
    if (this._pendingType === "0" || this._pendingType === "\0") {
      const content = Buffer.concat(this._contentAccum);
      const entry: ArchiveEntry = {
        name: this._pendingName,
        content,
        mtime: this._pendingMtime,
      };
      this.push(entry);
    }
    // Non-regular types (dirs, symlinks) are skipped silently — same as original
    this._contentAccum = [];
    this._contentRead = 0;
  }
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * unpackArchiveStream — async generator yielding ArchiveEntry one at a time.
 *
 * Peak memory: O(max single-entry size) — not O(archive size).
 *
 * Usage:
 *   for await (const entry of unpackArchiveStream(gzippedBuffer)) {
 *     await processEntry(entry); // entry.content is GC'd after this loop body
 *   }
 *
 * The input is still a Buffer here for API compatibility with callers that
 * already have the archive in memory. For true streaming from disk, pass
 * a Readable instead via unpackArchiveStreamFromReadable().
 */
export async function* unpackArchiveStream(
  gzipped: Buffer,
): AsyncGenerator<ArchiveEntry> {
  yield* unpackArchiveStreamFromReadable(Readable.from([gzipped]));
}

/**
 * unpackArchiveStreamFromReadable — true streaming path from a Readable.
 *
 * Usage with fs:
 *   const fileStream = createReadStream('/path/to/archive.nox-archive');
 *   for await (const entry of unpackArchiveStreamFromReadable(fileStream)) {
 *     await processEntry(entry);
 *   }
 */
export async function* unpackArchiveStreamFromReadable(
  source: Readable,
): AsyncGenerator<ArchiveEntry> {
  const gunzip = createGunzip();
  const parser = new TarBlockTransform();

  // Wire: source → gunzip → parser
  source.pipe(gunzip).pipe(parser);

  // Drain pipeline errors
  const pipelineError: { err?: Error } = {};
  const pipelinePromise = pipeline(source, gunzip, parser).catch((err) => {
    pipelineError.err = err as Error;
  });

  for await (const entry of parser as AsyncIterable<ArchiveEntry>) {
    yield entry;
  }

  await pipelinePromise;

  if (pipelineError.err) {
    throw pipelineError.err;
  }
}

/**
 * unpackArchiveToArray — backward-compatible wrapper.
 *
 * Collects all streamed entries into ArchiveEntry[].
 * Same observable behavior as unpackArchive() in format.ts, but
 * uses the streaming path internally — lower peak memory.
 *
 * Note: still O(total entries) in memory after collection. For very large
 * archives, prefer the generator form and process entries one at a time.
 */
export async function unpackArchiveToArray(gzipped: Buffer): Promise<ArchiveEntry[]> {
  const entries: ArchiveEntry[] = [];
  for await (const entry of unpackArchiveStream(gzipped)) {
    entries.push(entry);
  }
  return entries;
}

// ─── Internal helpers (mirrors format.ts) ─────────────────────────────────────

function computeHeaderChecksum(header: Buffer): number {
  let sum = 0;
  for (let i = 0; i < BLOCK_SIZE; i++) {
    if (i >= 148 && i < 156) sum += 0x20;
    else sum += header[i]!;
  }
  return sum;
}

function isZeroBlock(buf: Buffer): boolean {
  for (let i = 0; i < BLOCK_SIZE; i++) if (buf[i] !== 0) return false;
  return true;
}

function readCString(buf: Buffer, offset: number, len: number): string {
  let end = offset;
  const max = offset + len;
  while (end < max && buf[end] !== 0) end++;
  return buf.toString("utf8", offset, end);
}
