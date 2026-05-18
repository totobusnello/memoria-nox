/**
 * T1 — format.ts tests. tar/gzip pack/unpack round-trips.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { gunzipSync, gzipSync } from "node:zlib";
import {
  packArchive,
  unpackArchive,
  listArchive,
} from "../format.js";

describe("format / packArchive + unpackArchive", () => {
  it("round-trips a single entry byte-identically", () => {
    const content = Buffer.from("hello world\n", "utf8");
    const gz = packArchive([{ name: "greeting.txt", content }]);
    const back = unpackArchive(gz);
    assert.equal(back.length, 1);
    assert.equal(back[0]!.name, "greeting.txt");
    assert.ok(Buffer.compare(back[0]!.content, content) === 0);
  });

  it("round-trips multiple entries preserving order", () => {
    const entries = [
      { name: "a.json", content: Buffer.from('{"a":1}', "utf8") },
      { name: "b.bin", content: Buffer.from([0xde, 0xad, 0xbe, 0xef]) },
      { name: "c.txt", content: Buffer.from("line1\nline2\n", "utf8") },
    ];
    const gz = packArchive(entries);
    const back = unpackArchive(gz);
    assert.equal(back.length, 3);
    for (let i = 0; i < 3; i++) {
      assert.equal(back[i]!.name, entries[i]!.name);
      assert.ok(Buffer.compare(back[i]!.content, entries[i]!.content) === 0);
    }
  });

  it("listArchive returns just names without materializing content elsewhere", () => {
    const gz = packArchive([
      { name: "manifest.json", content: Buffer.from("{}") },
      { name: "chunks.jsonl", content: Buffer.from("{}\n") },
    ]);
    assert.deepEqual(listArchive(gz), ["manifest.json", "chunks.jsonl"]);
  });

  it("round-trips a 5MB synthetic blob with random bytes", () => {
    const size = 5 * 1024 * 1024;
    const content = Buffer.alloc(size);
    for (let i = 0; i < size; i++) content[i] = (i * 31) & 0xff;
    const gz = packArchive([{ name: "blob.bin", content }]);
    const back = unpackArchive(gz);
    assert.equal(back.length, 1);
    assert.equal(back[0]!.content.length, size);
    assert.ok(Buffer.compare(back[0]!.content, content) === 0);
  });

  it("produces a tarball that gunzip can decompress to valid ustar magic", () => {
    const gz = packArchive([
      { name: "manifest.json", content: Buffer.from("{}", "utf8") },
    ]);
    const tar = gunzipSync(gz);
    // ustar magic at byte 257 of the first header block
    const magic = tar.toString("ascii", 257, 263);
    assert.equal(magic, "ustar\0");
  });

  it("rejects empty entries array", () => {
    assert.throws(() => packArchive([]), /empty/);
  });

  it("rejects entry names too long for ustar (>100 bytes)", () => {
    const longName = "a/".repeat(80) + "file.txt";
    assert.throws(
      () =>
        packArchive([{ name: longName, content: Buffer.from("x") }]),
      /too long/,
    );
  });

  it("detects header checksum corruption", () => {
    const gz = packArchive([
      { name: "x.txt", content: Buffer.from("xxxxxxxxxx", "utf8") },
    ]);
    // Flip a byte in the gunzipped tar header (offset ~10 — inside name area)
    const tar = gunzipSync(gz);
    tar[10] = tar[10]! ^ 0xff;
    const corrupted = gzipSync(tar);
    assert.throws(() => unpackArchive(corrupted), /checksum mismatch/);
  });
});
