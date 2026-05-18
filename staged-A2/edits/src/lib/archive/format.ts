/**
 * T1 — Archive format module (TAR + gzip).
 *
 * Pure-Node ustar implementation. No external tar dep — keeps staged-A2 buildable
 * without npm install. tar produced here is `tar -tzf` compatible (validated in tests).
 *
 * Streaming surface area is implemented via async iterables + Node Streams. We
 * deliberately keep public APIs Buffer-based for in-memory tests; the real CLI
 * (T10) will wrap these with `fs.createReadStream`/`createWriteStream` pipes.
 */

import { createGzip, gunzipSync, gzipSync } from "node:zlib";
import { Readable } from "node:stream";
import { ArchiveEntry, ArchiveFormatError } from "./types.js";

const BLOCK_SIZE = 512;
const ZERO_BLOCK = Buffer.alloc(BLOCK_SIZE);

/** Pack archive entries into a single gzipped tar Buffer. */
export function packArchive(entries: ArchiveEntry[]): Buffer {
  if (entries.length === 0) {
    throw new ArchiveFormatError("packArchive: refuse to pack empty archive");
  }
  const parts: Buffer[] = [];
  for (const entry of entries) {
    parts.push(buildTarBlock(entry));
  }
  // Two trailing zero blocks terminate the tar stream (POSIX).
  parts.push(ZERO_BLOCK, ZERO_BLOCK);
  const tarBuf = Buffer.concat(parts);
  return gzipSync(tarBuf);
}

/** Unpack a gzipped tar Buffer into a list of entries. */
export function unpackArchive(gzipped: Buffer): ArchiveEntry[] {
  const tarBuf = gunzipSync(gzipped);
  return parseTarBlocks(tarBuf);
}

/** List entry names without materializing contents. */
export function listArchive(gzipped: Buffer): string[] {
  const entries = unpackArchive(gzipped);
  return entries.map((e) => e.name);
}

/** Streaming pack — for very large archives. Returns a Readable of gzip bytes. */
export function packArchiveStream(
  entries: AsyncIterable<ArchiveEntry>,
): Readable {
  let emitted = false;
  const reader = Readable.from(
    (async function* () {
      for await (const e of entries) {
        emitted = true;
        yield buildTarBlock(e);
      }
      if (!emitted) {
        throw new ArchiveFormatError("packArchiveStream: empty");
      }
      yield ZERO_BLOCK;
      yield ZERO_BLOCK;
    })(),
  );
  const gzip = createGzip();
  return reader.pipe(gzip);
}

// -- internals ---------------------------------------------------------------

function buildTarBlock(entry: ArchiveEntry): Buffer {
  const name = entry.name;
  if (name.length === 0) {
    throw new ArchiveFormatError("Empty entry name");
  }
  if (name.length > 100) {
    throw new ArchiveFormatError(
      `Entry name too long for ustar (${name.length} > 100): ${name}. ` +
        `Long-name extension not implemented in v1; rename or shorten paths.`,
    );
  }
  const content = entry.content;
  if (content.length > 0o77777777777) {
    throw new ArchiveFormatError(`Entry too large for ustar: ${entry.name}`);
  }
  const mtime = entry.mtime ?? Math.floor(Date.now() / 1000);
  const mode = entry.mode ?? 0o644;

  const header = Buffer.alloc(BLOCK_SIZE);
  // name (100)
  header.write(name, 0, 100, "utf8");
  // mode (8) — octal, null+space terminated per POSIX
  header.write(padOctal(mode, 7) + "\0", 100, 8, "ascii");
  // uid (8), gid (8)
  header.write(padOctal(0, 7) + "\0", 108, 8, "ascii");
  header.write(padOctal(0, 7) + "\0", 116, 8, "ascii");
  // size (12)
  header.write(padOctal(content.length, 11) + "\0", 124, 12, "ascii");
  // mtime (12)
  header.write(padOctal(mtime, 11) + "\0", 136, 12, "ascii");
  // checksum placeholder (8 spaces)
  header.write("        ", 148, 8, "ascii");
  // typeflag '0' (regular file)
  header.write("0", 156, 1, "ascii");
  // linkname (100) — empty
  // magic + version "ustar\000" + "00"
  header.write("ustar\0", 257, 6, "ascii");
  header.write("00", 263, 2, "ascii");
  // uname/gname empty

  // Compute checksum
  let sum = 0;
  for (let i = 0; i < BLOCK_SIZE; i++) sum += header[i]!;
  const checksum = padOctal(sum, 6) + "\0 ";
  header.write(checksum, 148, 8, "ascii");

  // Pad content to 512
  const padLen = (BLOCK_SIZE - (content.length % BLOCK_SIZE)) % BLOCK_SIZE;
  const padding = Buffer.alloc(padLen);
  return Buffer.concat([header, content, padding]);
}

function parseTarBlocks(tar: Buffer): ArchiveEntry[] {
  const out: ArchiveEntry[] = [];
  let offset = 0;
  while (offset + BLOCK_SIZE <= tar.length) {
    const header = tar.subarray(offset, offset + BLOCK_SIZE);
    if (isZeroBlock(header)) {
      // POSIX: two trailing zero blocks. Either way, stop.
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
        `tar header checksum mismatch for ${name}: declared=${declaredChecksum} computed=${computedChecksum}`,
      );
    }
    const typeflag = String.fromCharCode(header[156] ?? 0x30);
    offset += BLOCK_SIZE;
    if (Number.isNaN(size) || size < 0) {
      throw new ArchiveFormatError(`Invalid size in tar header for ${name}`);
    }
    if (typeflag === "0" || typeflag === "\0") {
      const content = Buffer.from(tar.subarray(offset, offset + size));
      out.push({ name, content, mtime });
      offset += size;
      const pad = (BLOCK_SIZE - (size % BLOCK_SIZE)) % BLOCK_SIZE;
      offset += pad;
    } else {
      // Skip unknown types (directories, links). Still advance.
      offset += size;
      const pad = (BLOCK_SIZE - (size % BLOCK_SIZE)) % BLOCK_SIZE;
      offset += pad;
    }
  }
  return out;
}

function computeHeaderChecksum(header: Buffer): number {
  let sum = 0;
  for (let i = 0; i < BLOCK_SIZE; i++) {
    if (i >= 148 && i < 156) sum += 0x20; // checksum field treated as spaces
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

function padOctal(n: number, width: number): string {
  let s = n.toString(8);
  while (s.length < width) s = "0" + s;
  return s;
}
