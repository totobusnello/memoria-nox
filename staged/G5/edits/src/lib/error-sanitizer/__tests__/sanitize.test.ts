/**
 * G5 T4 — Error sanitizer tests (24 cases).
 *
 * Coverage:
 *   - stack stripped by default                            (1)
 *   - stack included if exposeStack=true + non-prod        (1)
 *   - stack STILL stripped in production even if opt-in    (1)
 *   - internal paths /Users/ /root/ /home/ stripped        (3)
 *   - secrets (Gemini, OpenAI, Bearer, JWT) redacted       (4)
 *   - env vars redacted                                    (1)
 *   - requestId always present                             (2)
 *   - requestId passes through when caller supplies        (1)
 *   - known error → status mapping                         (5)
 *   - unknown error → 500 + generic msg                    (1)
 *   - non-Error input coerced                              (2)
 *   - details sanitized + safe pass-through                (2)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  sanitizeErrorForHttp,
  ERROR_STATUS_MAP,
  newRequestId,
} from "../sanitize.js";
import {
  errorToResponse,
  sanitizerWrap,
  expressErrorMiddleware,
} from "../middleware.js";

class WeakPassphraseError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = "WeakPassphraseError";
  }
}
class BadPassphraseError extends Error {
  constructor(msg = "bad passphrase") {
    super(msg);
    this.name = "BadPassphraseError";
  }
}
class TamperedArchiveError extends Error {
  constructor(msg = "tampered") {
    super(msg);
    this.name = "TamperedArchiveError";
  }
}
class LLMTimeoutError extends Error {
  constructor() {
    super("timeout");
    this.name = "LLMTimeoutError";
  }
}
class UnauthorizedError extends Error {
  constructor() {
    super("no token");
    this.name = "UnauthorizedError";
  }
}

describe("sanitizeErrorForHttp", () => {
  // — stack handling —
  it("strips stack by default", () => {
    const err = new Error("boom");
    const { body } = sanitizeErrorForHttp(err, { nodeEnv: "development" });
    assert.equal(body.stack, undefined);
  });

  it("includes stack when exposeStack=true AND NODE_ENV=development", () => {
    const err = new Error("boom");
    const { body } = sanitizeErrorForHttp(err, {
      exposeStack: true,
      nodeEnv: "development",
    });
    assert.equal(typeof body.stack, "string");
    assert.match(body.stack!, /Error: boom/);
  });

  it("STILL strips stack in production even with exposeStack=true", () => {
    const err = new Error("boom");
    const { body } = sanitizeErrorForHttp(err, {
      exposeStack: true,
      nodeEnv: "production",
    });
    assert.equal(body.stack, undefined);
  });

  // — internal paths —
  it("strips /Users/lab/... path from message", () => {
    const err = new (class extends Error {
      constructor() {
        super(
          "ENOENT, open '/Users/lab/Claude/Projetos/memoria-nox/.env'",
        );
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.doesNotMatch(body.error, /\/Users\/lab/);
    assert.equal(body.error, "request failed (details redacted)");
  });

  it("strips /root/... path from message", () => {
    const err = new (class extends Error {
      constructor() {
        super("cannot read /root/.openclaw/.env");
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.doesNotMatch(body.error, /\/root\//);
  });

  it("strips /home/foo/... path from message", () => {
    const err = new (class extends Error {
      constructor() {
        super("loading /home/foo/.config/nox/secret");
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.doesNotMatch(body.error, /\/home\//);
  });

  // — secret redaction —
  it("redacts Gemini API key from message", () => {
    const err = new (class extends Error {
      constructor() {
        super(
          "HTTP 401: API key invalid AIzaSyABCDEFGHIJKLMNOPQRSTUVWX1234567",
        );
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.doesNotMatch(body.error, /AIzaSyABC/);
    assert.match(body.error, /\[REDACTED\]/);
  });

  it("redacts OpenAI-style sk- key", () => {
    const err = new (class extends Error {
      constructor() {
        super("rejected with sk-abcDEFghiJKLmnoPQRstuVWXyzABCDEFghIJKlmNOpQr");
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.doesNotMatch(body.error, /sk-abc/);
  });

  it("redacts Bearer tokens", () => {
    const err = new (class extends Error {
      constructor() {
        super("upstream said Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.foo");
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.doesNotMatch(body.error, /eyJh/);
  });

  it("redacts JWT-shaped tokens", () => {
    // Synthesise a 3-segment string matching the JWT pattern at runtime so the
    // test fixture itself isn't a recognisable secret in source (gitleaks-safe).
    const seg1 = "eyJ" + "a".repeat(33);
    const seg2 = "b".repeat(24);
    const seg3 = "c".repeat(43);
    const fakeJwt = `${seg1}.${seg2}.${seg3}`;
    const err = new (class extends Error {
      constructor() {
        super(`validate ${fakeJwt}`);
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.match(body.error, /\[REDACTED\]/);
  });

  // — env var redaction —
  it("redacts env-var assignments (NOX_*=, GEMINI_API_KEY=)", () => {
    const err = new (class extends Error {
      constructor() {
        super("env NOX_API_TOKEN=hunter2 GEMINI_API_KEY=AIzaXX failed");
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.doesNotMatch(body.error, /hunter2/);
    assert.doesNotMatch(body.error, /AIzaXX/);
  });

  // — requestId —
  it("always emits a requestId (uuid v4 format)", () => {
    const { body } = sanitizeErrorForHttp(new Error("x"));
    assert.match(
      body.requestId,
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });

  it("emits a unique requestId per call when not supplied", () => {
    const a = sanitizeErrorForHttp(new Error("x"));
    const b = sanitizeErrorForHttp(new Error("x"));
    assert.notEqual(a.body.requestId, b.body.requestId);
  });

  it("passes through caller-supplied requestId", () => {
    const { body } = sanitizeErrorForHttp(new Error("x"), {
      requestId: "abc-123",
    });
    assert.equal(body.requestId, "abc-123");
  });

  // — known error → status mapping —
  it("WeakPassphraseError → 400 + WEAK_PASSPHRASE code", () => {
    const r = sanitizeErrorForHttp(new WeakPassphraseError("too weak"));
    assert.equal(r.status, 400);
    assert.equal(r.body.code, "WEAK_PASSPHRASE");
  });

  it("BadPassphraseError → 422 + BAD_PASSPHRASE code + canned safe msg", () => {
    const r = sanitizeErrorForHttp(new BadPassphraseError("wrong pass"));
    assert.equal(r.status, 422);
    assert.equal(r.body.code, "BAD_PASSPHRASE");
    assert.equal(r.body.error, "bad passphrase or wrong key");
  });

  it("TamperedArchiveError → 422 + TAMPERED_ARCHIVE + canned safe msg", () => {
    const r = sanitizeErrorForHttp(new TamperedArchiveError());
    assert.equal(r.status, 422);
    assert.equal(r.body.code, "TAMPERED_ARCHIVE");
    assert.equal(r.body.error, "archive integrity check failed");
  });

  it("LLMTimeoutError → 504 + LLM_TIMEOUT", () => {
    const r = sanitizeErrorForHttp(new LLMTimeoutError());
    assert.equal(r.status, 504);
    assert.equal(r.body.code, "LLM_TIMEOUT");
  });

  it("UnauthorizedError → 401 + canned msg (no leak of caller's reason)", () => {
    const r = sanitizeErrorForHttp(new UnauthorizedError());
    assert.equal(r.status, 401);
    assert.equal(r.body.error, "missing or invalid auth token");
    assert.doesNotMatch(r.body.error, /no token/);
  });

  // — unknown error mapping —
  it("unknown Error name → 500 + INTERNAL_ERROR + generic msg (no raw .message)", () => {
    const err = new Error("SQL syntax error near 'SELECT * FROM secrets'");
    const r = sanitizeErrorForHttp(err);
    assert.equal(r.status, 500);
    assert.equal(r.body.code, "INTERNAL_ERROR");
    assert.equal(r.body.error, "internal error");
    assert.doesNotMatch(r.body.error, /SELECT/);
  });

  // — non-Error inputs —
  it("string input is coerced to Error", () => {
    const r = sanitizeErrorForHttp("oops");
    assert.equal(r.status, 500);
    assert.equal(r.body.error, "internal error");
  });

  it("null input is coerced to Error", () => {
    const r = sanitizeErrorForHttp(null);
    assert.equal(r.status, 500);
    assert.ok(typeof r.body.requestId === "string");
  });

  // — details sanitization —
  it("details object: drops forbidden keys (stack, env, __proto__)", () => {
    const err = new (class extends Error {
      details = {
        safe: "yes",
        stack: "Error at /Users/lab/...",
        env: { GEMINI_API_KEY: "AIzaXX" },
        nested: { ok: 1 },
      };
      constructor() {
        super("err");
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    const d = body.details as Record<string, unknown>;
    assert.equal(d.safe, "yes");
    assert.equal(d.stack, undefined);
    assert.equal(d.env, undefined);
    assert.deepEqual(d.nested, { ok: 1 });
  });

  it("details string with internal path → dropped", () => {
    const err = new (class extends Error {
      details = "open /Users/lab/.env failed";
      constructor() {
        super("err");
        this.name = "ValidationError";
      }
    })();
    const { body } = sanitizeErrorForHttp(err);
    assert.equal(body.details, undefined);
  });

  // — Logger is called when provided —
  it("calls opts.log with a redacted line (no plaintext leak)", () => {
    const lines: string[] = [];
    sanitizeErrorForHttp(new WeakPassphraseError("hunter2-leaked"), {
      log: (m) => lines.push(m),
    });
    assert.equal(lines.length, 1);
    assert.doesNotMatch(lines[0]!, /hunter2/);
    assert.match(lines[0]!, /status=400/);
    assert.match(lines[0]!, /code=WEAK_PASSPHRASE/);
  });
});

describe("middleware: errorToResponse + sanitizerWrap", () => {
  it("errorToResponse returns the sanitized shape with headers", () => {
    const r = errorToResponse(new BadPassphraseError(), {
      requestId: "req-1",
    });
    assert.equal(r.status, 422);
    assert.equal(r.headers!["Content-Type"], "application/json");
    assert.equal(r.headers!["X-Request-ID"], "req-1");
    const b = r.body as { code: string; requestId: string };
    assert.equal(b.code, "BAD_PASSPHRASE");
    assert.equal(b.requestId, "req-1");
  });

  it("sanitizerWrap catches throws and converts to sanitized response", async () => {
    const inner = async (): Promise<{ status: number; body: unknown }> => {
      throw new TamperedArchiveError();
    };
    const wrapped = sanitizerWrap(inner);
    const out = await wrapped({ headers: { "x-request-id": "req-X" } });
    assert.equal(out.status, 422);
    const b = out.body as { code: string; requestId: string };
    assert.equal(b.code, "TAMPERED_ARCHIVE");
    assert.equal(b.requestId, "req-X");
  });

  it("sanitizerWrap preserves happy-path outputs but injects X-Request-ID", async () => {
    const inner = async (): Promise<{ status: number; headers: Record<string, string>; body: unknown }> => ({
      status: 200,
      headers: { "Content-Type": "text/plain" },
      body: "ok",
    });
    const wrapped = sanitizerWrap(inner);
    const out = await wrapped({ headers: { "x-request-id": "req-Y" } });
    assert.equal(out.status, 200);
    assert.equal(out.headers!["X-Request-ID"], "req-Y");
    assert.equal(out.body, "ok");
  });

  it("expressErrorMiddleware writes sanitized JSON + sets X-Request-ID", () => {
    const calls = { status: 0, header: {} as Record<string, string>, json: null as unknown };
    const res = {
      status(n: number) {
        calls.status = n;
        return this;
      },
      setHeader(name: string, value: string) {
        calls.header[name] = value;
      },
      json(body: unknown) {
        calls.json = body;
      },
    };
    const mw = expressErrorMiddleware();
    mw(new BadPassphraseError(), { headers: { "x-request-id": "req-Z" } }, res, () => undefined);
    assert.equal(calls.status, 422);
    assert.equal(calls.header["X-Request-ID"], "req-Z");
    const b = calls.json as { code: string };
    assert.equal(b.code, "BAD_PASSPHRASE");
  });
});

describe("ERROR_STATUS_MAP completeness", () => {
  it("contains all critical archive + answer + auth error classes", () => {
    for (const name of [
      "WeakPassphraseError",
      "BadPassphraseError",
      "TamperedArchiveError",
      "LLMTimeoutError",
      "LLMUnreachableError",
      "RetrievalEmptyError",
      "UnauthorizedError",
      "RateLimitError",
      "ValidationError",
    ]) {
      assert.ok(
        ERROR_STATUS_MAP.has(name),
        `missing entry for ${name}`,
      );
    }
  });

  it("newRequestId returns a uuid v4 string", () => {
    const id = newRequestId();
    assert.match(
      id,
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });
});
