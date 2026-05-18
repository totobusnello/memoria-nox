import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  serveViewerFile,
  resolveViewerPath,
} from "../../../api/viewer-static.js";

function makeFixture(): { root: string } {
  const root = mkdtempSync(join(tmpdir(), "viewer-test-"));
  writeFileSync(join(root, "index.html"), "<html><body>hi</body></html>");
  writeFileSync(join(root, "app.js"), "console.log('p5');");
  writeFileSync(join(root, "style.css"), "body { color: red; }");
  mkdirSync(join(root, "sub"), { recursive: true });
  writeFileSync(join(root, "sub", "nested.html"), "nested");
  return { root };
}

describe("T7 — viewer-static", () => {
  it("serves /viewer/ → index.html", () => {
    const { root } = makeFixture();
    const r = serveViewerFile("/viewer/", { root });
    assert.equal(r.status, 200);
    assert.match(r.headers["Content-Type"]!, /text\/html/);
    assert.equal(String(r.body), "<html><body>hi</body></html>");
  });

  it("serves /viewer → index.html", () => {
    const { root } = makeFixture();
    const r = serveViewerFile("/viewer", { root });
    assert.equal(r.status, 200);
  });

  it("serves js with javascript content type", () => {
    const { root } = makeFixture();
    const r = serveViewerFile("/viewer/app.js", { root });
    assert.equal(r.status, 200);
    assert.match(r.headers["Content-Type"]!, /application\/javascript/);
  });

  it("serves css with css content type", () => {
    const { root } = makeFixture();
    const r = serveViewerFile("/viewer/style.css", { root });
    assert.equal(r.status, 200);
    assert.match(r.headers["Content-Type"]!, /text\/css/);
  });

  it("rejects path traversal", () => {
    const { root } = makeFixture();
    const r = serveViewerFile("/viewer/../../etc/passwd", { root });
    assert.equal(r.status, 404);
  });

  it("includes short cache header", () => {
    const { root } = makeFixture();
    const r = serveViewerFile("/viewer/app.js", { root });
    assert.match(r.headers["Cache-Control"]!, /max-age=300/);
  });

  it("resolveViewerPath returns null on traversal", () => {
    assert.equal(resolveViewerPath("/viewer/../secret"), null);
  });

  it("returns 404 for missing file", () => {
    const { root } = makeFixture();
    const r = serveViewerFile("/viewer/missing.png", { root });
    assert.equal(r.status, 404);
  });
});
