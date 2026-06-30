/**
 * T4 — Embeddings serializer.
 *
 * Binary layout for embeddings.bin:
 *
 *   bytes  0..7   magic "NOXEMBED" (ASCII)
 *   bytes  8..11  format version (uint32 LE) = 1
 *   bytes 12..15  embedding_dim (uint32 LE)
 *   bytes 16+     raw concatenated Float32Array, little-endian
 *
 * embeddings.idx is JSONL: one EmbeddingIndexEntry per line, mapping chunk_id
 * to its (offset, length) inside embeddings.bin. length is in BYTES, not floats.
 *
 * CRITICAL — Buffer pool aliasing (memory feedback
 * `feedback_buffer_pool_aliasing_in_typed_arrays`): when reading floats back
 * out of the bin, we MUST copy through a Uint8Array intermediate. A direct
 * `new Float32Array(buf.buffer, byteOffset, dim)` would share Node's internal
 * Buffer pool memory and silently corrupt under GC. Tests assert byte-identity
 * after a full round-trip + a forced allocation.
 */

import { EmbeddingIndexEntry } from "../types.js";

const MAGIC = Buffer.from("NOXEMBED", "ascii");
const FORMAT_VERSION = 1;
const HEADER_SIZE = 16;
const FLOAT_BYTES = 4;

export interface EmbeddingInput {
  chunk_id: number;
  vector: Float32Array;
  model_name: string;
  embedded_at: string;
}

export interface EmbeddingsBundle {
  bin: Buffer;
  idx: Buffer;
  dim: number;
  count: number;
}

/** Serialize embeddings to a packed bin + idx JSONL. */
export function serializeEmbeddings(rows: EmbeddingInput[]): EmbeddingsBundle {
  if (rows.length === 0) {
    const bin = buildHeader(0);
    return { bin, idx: Buffer.alloc(0), dim: 0, count: 0 };
  }
  const dim = rows[0]!.vector.length;
  for (const row of rows) {
    if (row.vector.length !== dim) {
      throw new Error(
        `Embedding dim mismatch: chunk_id=${row.chunk_id} has ${row.vector.length}, expected ${dim}`,
      );
    }
  }
  const header = buildHeader(dim);
  const idxLines: string[] = [];
  const dataParts: Buffer[] = [header];
  let byteOffset = HEADER_SIZE;
  for (const row of rows) {
    // CRITICAL: copy through Uint8Array — never share Float32Array.buffer.
    const view = new Uint8Array(dim * FLOAT_BYTES);
    const f32 = new Float32Array(view.buffer);
    f32.set(row.vector);
    const chunk = Buffer.from(view); // independent allocation
    dataParts.push(chunk);
    const entry: EmbeddingIndexEntry = {
      chunk_id: row.chunk_id,
      offset: byteOffset,
      length: chunk.length,
      model_name: row.model_name,
      embedded_at: row.embedded_at,
    };
    idxLines.push(JSON.stringify(entry));
    byteOffset += chunk.length;
  }
  return {
    bin: Buffer.concat(dataParts),
    idx: Buffer.from(idxLines.join("\n") + "\n", "utf8"),
    dim,
    count: rows.length,
  };
}

/** Parse embeddings.bin back into a map keyed by chunk_id. */
export function parseEmbeddings(
  bin: Buffer,
  idx: Buffer,
): Map<number, EmbeddingInput> {
  validateHeader(bin);
  const dim = bin.readUInt32LE(12);
  const out = new Map<number, EmbeddingInput>();
  const idxText = idx.toString("utf8");
  if (idxText.length === 0) return out;
  for (const line of idxText.split("\n")) {
    if (line.length === 0) continue;
    const entry = JSON.parse(line) as EmbeddingIndexEntry;
    if (entry.length !== dim * FLOAT_BYTES) {
      throw new Error(
        `Embedding length mismatch for chunk_id=${entry.chunk_id}: idx says ${entry.length}, header dim implies ${dim * FLOAT_BYTES}`,
      );
    }
    if (entry.offset + entry.length > bin.length) {
      throw new Error(
        `Embedding offset out of range for chunk_id=${entry.chunk_id}`,
      );
    }
    // CRITICAL: copy through Uint8Array — see file header comment.
    const slice = bin.subarray(entry.offset, entry.offset + entry.length);
    const copy = new Uint8Array(slice.length);
    copy.set(slice);
    const f32 = new Float32Array(copy.buffer);
    out.set(entry.chunk_id, {
      chunk_id: entry.chunk_id,
      vector: f32,
      model_name: entry.model_name,
      embedded_at: entry.embedded_at,
    });
  }
  return out;
}

function buildHeader(dim: number): Buffer {
  const buf = Buffer.alloc(HEADER_SIZE);
  MAGIC.copy(buf, 0);
  buf.writeUInt32LE(FORMAT_VERSION, 8);
  buf.writeUInt32LE(dim, 12);
  return buf;
}

function validateHeader(bin: Buffer): void {
  if (bin.length < HEADER_SIZE) {
    throw new Error(`embeddings.bin too short: ${bin.length} bytes`);
  }
  if (!bin.subarray(0, 8).equals(MAGIC)) {
    throw new Error(
      `embeddings.bin bad magic: expected NOXEMBED, got ${bin.subarray(0, 8).toString("ascii")}`,
    );
  }
  const version = bin.readUInt32LE(8);
  if (version !== FORMAT_VERSION) {
    throw new Error(`embeddings.bin unsupported version: ${version}`);
  }
}
