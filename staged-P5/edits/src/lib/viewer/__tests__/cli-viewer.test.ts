import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  buildViewerUrl,
  runViewerCli,
  type ViewerCliLauncher,
} from "../../../cli/viewer.js";

describe("T12 — CLI viewer", () => {
  it("buildViewerUrl honors env", () => {
    const url = buildViewerUrl({
      NOX_API_PORT: "18888",
      NOX_VIEWER_BIND: "192.168.0.10",
    });
    assert.equal(url, "http://192.168.0.10:18888/viewer/");
  });

  it("buildViewerUrl rewrites 0.0.0.0 to 127.0.0.1", () => {
    const url = buildViewerUrl({ NOX_VIEWER_BIND: "0.0.0.0" });
    assert.equal(url, "http://127.0.0.1:18802/viewer/");
  });

  it("runViewerCli --print writes URL and returns 0", async () => {
    const lines: string[] = [];
    const rc = await runViewerCli(["--print"], {
      env: { NOX_API_PORT: "1234" },
      stdout: { write: (l) => lines.push(l) },
    });
    assert.equal(rc, 0);
    assert.match(lines[0]!, /:1234\/viewer\//);
  });

  it("runViewerCli launches browser when available", async () => {
    const lines: string[] = [];
    const launcher: ViewerCliLauncher = {
      async open() {
        return { launched: true, reason: "fake" };
      },
    };
    const rc = await runViewerCli([], {
      env: {} as NodeJS.ProcessEnv,
      launcher,
      stdout: { write: (l) => lines.push(l) },
    });
    assert.equal(rc, 0);
    assert.match(lines[0]!, /Opening viewer/);
  });
});
