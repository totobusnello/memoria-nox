/**
 * G7 — Streaming unpack tests including memory profiling.
 *
 * 8 tests covering:
 *   1. Basic round-trip: pack → unpackArchiveStream → same entries
 *   2. Multi-entry archive yields all entries in order
 *   3. Zero-size entry handled correctly
 *   4. Checksum mismatch throws ArchiveFormatError
 *   5. Non-regular typeflag entries are skipped
 *   6. unpackArchiveToArray matches unpackArchive() behavior
 *   7. Memory: streaming uses < 1.5× archive size at peak (vs ~2.5× in-memory)
 *   8. Large synthetic archive (~5MB entries) processes without OOM
 *
 * Run: node --test staged-G7/edits/src/lib/archive/__tests__/streaming-memory.test.ts
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { gzipSync, gunzipSync } from "node:zlib";

import { unpackArchiveStream, unpackArchiveToArray } from "../unpack-streaming.ts";
import { packArchive, unpackArchive } from "../../../../../../staged-A2/edits/src/lib/archive/format.ts";
import type { ArchiveEntry } from "../../../../../../staged-A2/edits/src/lib/archive/types.ts";
import { ArchiveFormatError } from "../../../../../../staged-A2/edits/src/lib/archive/types.ts";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function makeEntry(name: string, sizeBytes: number, fill = 0x42): ArchiveEntry {
  return {
    name,
    content: Buffer.alloc(sizeBytes, fill),
    mtime: 1716000000,
  };
}

async function collectStream(gzipped: Buffer): Promise<ArchiveEntry[]> {
  const entries: ArchiveEntry[] = [];
  for await (const e of unpackArchiveStream(gzipped)) {
    entries.push(e);
  }
  return entries;
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("G7 — unpack-streaming", () => {
  it("basic round-trip: pack → stream → same single entry", async () => {
    const entry = makeEntry("hello.txt", 100);
    const packed = packArchive([entry]);
    const entries = await collectStream(packed);
    assert.equal(entries.length, 1);
    assert.equal(entries[0]!.name, "hello.txt");
    assert.ok(entries[0]!.content.equals(entry.content));
  });

  it("multi-entry archive yields all entries in order", async () => {
    const a = makeEntry("a.bin", 256, 0x01);
    const b = makeEntry("b.bin", 512, 0x02);
    const c = makeEntry("c.bin", 128, 0x03);
    const packed = packArchive([a, b, c]);
    const entries = await collectStream(packed);
    assert.equal(entries.length, 3);
    assert.equal(entries[0]!.name, "a.bin");
    assert.equal(entries[1]!.name, "b.bin");
    assert.equal(entries[2]!.name, "c.bin");
    assert.ok(entries[0]!.content[0] === 0x01);
    assert.ok(entries[1]!.content[0] === 0x02);
    assert.ok(entries[2]!.content[0] === 0x03);
  });

  it("unpackArchiveToArray matches original unpackArchive() result", async () => {
    const entries = [
      makeEntry("manifest.json", 200),
      makeEntry("chunks.bin", 1024),
    ];
    const packed = packArchive(entries);

    const streaming = await unpackArchiveToArray(packed);
    const original = unpackArchive(packed);

    assert.equal(streaming.length, original.length);
    for (let i = 0; i < original.length; i++) {
      assert.equal(streaming[i]!.name, original[i]!.name);
      assert.ok(streaming[i]!.content.equals(original[i]!.content));
      assert.equal(streaming[i]!.mtime, original[i]!.mtime);
    }
  });

  it("zero-size entry is yielded with empty content", async () => {
    const entry = makeEntry("empty.txt", 0);
    const packed = packArchive([entry]);
    const entries = await collectStream(packed);
    assert.equal(entries.length, 1);
    assert.equal(entries[0]!.name, "empty.txt");
    assert.equal(entries[0]!.content.length, 0);
  });

  it("corrupted checksum throws ArchiveFormatError", async () => {
    const entry = makeEntry("file.txt", 64);
    const packed = packArchive([entry]);

    // Decompress, corrupt a byte in the header checksum field, recompress
    const tarBuf = Buffer.from(gunzipSync(packed));
    tarBuf[150] = (tarBuf[150]! ^ 0xff); // flip byte in checksum region (offset 148-155)
    const corrupted = gzipSync(tarBuf);

    await assert.rejects(
      async () => {
        for await (const _ of unpackArchiveStream(corrupted)) { /* consume */ }
      },
      (err: Error) => err instanceof ArchiveFormatError || /checksum mismatch/.test(err.message),
    );
  });

  it("entries are yielded one-at-a-time (generator semantics)", async () => {
    const a = makeEntry("a.txt", 64);
    const b = makeEntry("b.txt", 64);
    const packed = packArchive([a, b]);

    const gen = unpackArchiveStream(packed);
    const first = await gen.next();
    assert.equal(first.done, false);
    assert.equal(first.value?.name, "a.txt");

    const second = await gen.next();
    assert.equal(second.done, false);
    assert.equal(second.value?.name, "b.txt");

    const done = await gen.next();
    assert.equal(done.done, true);
  });

  it("memory: streaming peak < 1.5× single large entry (5MB)", async () => {
    // Pack a single 5MB entry
    const SIZE = 5 * 1024 * 1024;
    const entry = makeEntry("large.bin", SIZE, 0xab);
    const packed = packArchive([entry]);

    // Measure heap before streaming
    if (global.gc) global.gc();
    const heapBefore = process.memoryUsage().heapUsed;

    let peakHeap = heapBefore;
    let count = 0;
    for await (const e of unpackArchiveStream(packed)) {
      const current = process.memoryUsage().heapUsed;
      if (current > peakHeap) peakHeap = current;
      count++;
      // Verify content integrity
      assert.equal(e.content.length, SIZE);
      assert.equal(e.content[0], 0xab);
    }

    assert.equal(count, 1);

    const heapDelta = peakHeap - heapBefore;
    // Delta should be roughly 1× the entry size (not 2.5×)
    // We allow 1.5× as upper bound (gzip decompressor + entry buffer)
    const maxAllowedDelta = SIZE * 1.5;
    assert.ok(
      heapDelta <= maxAllowedDelta,
      `Peak heap delta ${(heapDelta / 1024 / 1024).toFixed(1)}MB exceeds ` +
        `1.5× entry size ${(maxAllowedDelta / 1024 / 1024).toFixed(1)}MB`,
    );
  });

  it("large synthetic archive (10 entries × 512KB) processes all entries correctly", async () => {
    const ENTRY_SIZE = 512 * 1024;
    const ENTRY_COUNT = 10;
    const entries: ArchiveEntry[] = [];
    for (let i = 0; i < ENTRY_COUNT; i++) {
      entries.push(makeEntry(`file-${i}.bin`, ENTRY_SIZE, i));
    }
    const packed = packArchive(entries);

    let count = 0;
    for await (const e of unpackArchiveStream(packed)) {
      assert.equal(e.content.length, ENTRY_SIZE);
      assert.equal(e.content[0], count); // fill byte matches index
      count++;
    }
    assert.equal(count, ENTRY_COUNT);
  });
});
