/**
 * G16 — export-locking tests.
 */

import { describe, it, before, after, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { promises as fs, existsSync } from "node:fs";
import path from "node:path";
import os from "node:os";

import {
  acquireExportLock,
  withExportLock,
  inspectExportLock,
  getLockPath,
  lockExistsSync,
  ExportLockBusyError,
  DEFAULT_STALE_MS,
  type LockMetadata,
} from "../export-locking.js";

let tmpDir: string;

before(async () => {
  tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "g16-lock-"));
});

after(async () => {
  await fs.rm(tmpDir, { recursive: true, force: true });
});

beforeEach(async () => {
  // Clean tmp dir between tests.
  for (const f of await fs.readdir(tmpDir)) {
    await fs.unlink(path.join(tmpDir, f)).catch(() => {});
  }
});

describe("acquireExportLock — basic", () => {
  it("creates lock file at <output>.lock with mode 0600", async () => {
    const out = path.join(tmpDir, "archive.tar.gz");
    const h = await acquireExportLock(out);
    assert.equal(h.lockPath, out + ".lock");
    assert.equal(existsSync(h.lockPath), true);
    const st = await fs.stat(h.lockPath);
    // POSIX perm bits — on macOS/Linux this is 0o600 (0o100600 with type bits).
    if (process.platform !== "win32") {
      assert.equal((st.mode & 0o777) === 0o600, true);
    }
    await h.release();
    assert.equal(existsSync(h.lockPath), false);
  });

  it("getLockPath / lockExistsSync helpers", async () => {
    const out = path.join(tmpDir, "x.tar.gz");
    assert.equal(getLockPath(out), out + ".lock");
    assert.equal(lockExistsSync(out), false);
    const h = await acquireExportLock(out);
    assert.equal(lockExistsSync(out), true);
    await h.release();
  });

  it("lock metadata includes pid, hostname, op", async () => {
    const out = path.join(tmpDir, "meta.tar.gz");
    const h = await acquireExportLock(out, { op: "import" });
    const meta = await inspectExportLock(out);
    assert.equal(meta?.pid, process.pid);
    assert.equal(meta?.hostname, os.hostname());
    assert.equal(meta?.op, "import");
    assert.equal(meta?.v, 1);
    await h.release();
  });
});

describe("acquireExportLock — concurrent calls", () => {
  it("second concurrent call throws ExportLockBusyError", async () => {
    const out = path.join(tmpDir, "concurrent.tar.gz");
    const h1 = await acquireExportLock(out);
    await assert.rejects(
      async () => acquireExportLock(out),
      (err: Error) => {
        assert.equal(err instanceof ExportLockBusyError, true);
        assert.equal((err as ExportLockBusyError).status, 409);
        return true;
      },
    );
    await h1.release();
  });

  it("after release, lock can be re-acquired", async () => {
    const out = path.join(tmpDir, "reacquire.tar.gz");
    const h1 = await acquireExportLock(out);
    await h1.release();
    const h2 = await acquireExportLock(out);
    assert.equal(existsSync(h2.lockPath), true);
    await h2.release();
  });
});

describe("acquireExportLock — stale lock", () => {
  it("breaks lock when older than staleMs", async () => {
    const out = path.join(tmpDir, "stale.tar.gz");
    // Plant a stale lock manually.
    const stale: LockMetadata = {
      pid: process.pid,                          // alive PID (us)
      started_at_ms: Date.now() - 60 * 60 * 1000, // 1 hour ago — stale
      hostname: os.hostname(),
      op: "export",
      v: 1,
    };
    await fs.writeFile(getLockPath(out), JSON.stringify(stale), { mode: 0o600 });
    let warned = false;
    const h = await acquireExportLock(out, {
      staleMs: 30 * 60 * 1000,
      onWarn: () => { warned = true; },
    });
    assert.equal(warned, true);
    const meta = await inspectExportLock(out);
    assert.equal(meta?.started_at_ms !== stale.started_at_ms, true);
    await h.release();
  });

  it("breaks lock when PID is dead, even within stale window", async () => {
    const out = path.join(tmpDir, "deadpid.tar.gz");
    // PID 999999 is virtually guaranteed not to exist; if it does, test is no-op.
    const fake: LockMetadata = {
      pid: 999999,
      started_at_ms: Date.now() - 5 * 60 * 1000, // 5 min — within stale window
      hostname: "ghost",
      op: "export",
      v: 1,
    };
    await fs.writeFile(getLockPath(out), JSON.stringify(fake), { mode: 0o600 });
    let warned = false;
    const h = await acquireExportLock(out, { onWarn: () => { warned = true; } });
    assert.equal(warned, true);
    const meta = await inspectExportLock(out);
    assert.equal(meta?.pid, process.pid);
    await h.release();
  });

  it("rejects when alive PID + within stale window", async () => {
    const out = path.join(tmpDir, "alive.tar.gz");
    const meta: LockMetadata = {
      pid: process.pid, // ourselves — definitely alive
      started_at_ms: Date.now() - 1000, // 1s old
      hostname: os.hostname(),
      op: "export",
      v: 1,
    };
    await fs.writeFile(getLockPath(out), JSON.stringify(meta), { mode: 0o600 });
    await assert.rejects(
      async () => acquireExportLock(out, { staleMs: DEFAULT_STALE_MS }),
      ExportLockBusyError,
    );
  });
});

describe("acquireExportLock — malformed lock", () => {
  it("breaks lock when JSON is unparseable", async () => {
    const out = path.join(tmpDir, "malformed.tar.gz");
    await fs.writeFile(getLockPath(out), "not-valid-json{{{", { mode: 0o600 });
    let warned = false;
    const h = await acquireExportLock(out, { onWarn: () => { warned = true; } });
    assert.equal(warned, true);
    const meta = await inspectExportLock(out);
    assert.equal(meta?.pid, process.pid);
    await h.release();
  });
});

describe("withExportLock", () => {
  it("runs fn while holding lock + releases on success", async () => {
    const out = path.join(tmpDir, "with.tar.gz");
    let sawLock = false;
    const result = await withExportLock(out, async () => {
      sawLock = existsSync(getLockPath(out));
      return "ok";
    });
    assert.equal(sawLock, true);
    assert.equal(result, "ok");
    assert.equal(existsSync(getLockPath(out)), false);
  });

  it("releases lock even if fn throws", async () => {
    const out = path.join(tmpDir, "throws.tar.gz");
    await assert.rejects(
      withExportLock(out, async () => {
        throw new Error("boom");
      }),
      /boom/,
    );
    assert.equal(existsSync(getLockPath(out)), false);
  });
});

describe("release safety", () => {
  it("release does not delete lock that was broken + taken by another caller", async () => {
    const out = path.join(tmpDir, "safe-release.tar.gz");
    const h1 = await acquireExportLock(out);
    // Manually overwrite the lock file with a different started_at_ms.
    // This simulates: while we held the lock, someone else broke and took it.
    await fs.writeFile(
      getLockPath(out),
      JSON.stringify({
        pid: process.pid,
        started_at_ms: Date.now() + 100000, // future time → clearly different
        hostname: os.hostname(),
        op: "export",
        v: 1,
      }),
      { mode: 0o600 },
    );
    // h1.release() should detect the mismatch and NOT delete.
    await h1.release();
    assert.equal(existsSync(getLockPath(out)), true);
  });
});
