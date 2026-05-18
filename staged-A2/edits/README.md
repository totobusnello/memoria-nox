# staged-A2 — Archive Primitives (T1-T9)

**Status:** T1-T9 of A2 implementation kickoff. Format + serializers + encryption + migration core, no CLI/HTTP/MCP integration yet.

**Branch:** `overnight/2026-05-19/A2-impl-T1-T9`
**Spec:** `specs/2026-05-17-A2-export-import.md` (PR #9, merged)
**Kickoff:** `specs/2026-05-18-A2-implementation-kickoff.md` (PR merged)
**D41 #2:** Encryption is opt-out (encrypt by default).

---

## What lives here

```
staged-A2/
├── package.json
├── tsconfig.json
└── edits/
    ├── README.md
    └── src/lib/archive/
        ├── index.ts                  # Public API
        ├── types.ts                  # Shared TypeScript types
        ├── format.ts                 # T1 — TAR.gz pack/unpack/list (streaming)
        ├── manifest.ts               # T2 — Manifest schema, writer, parser
        ├── encryption.ts             # T7+T8 — AES-256-GCM + scrypt KDF + AAD
        ├── migration.ts              # T9 — Forward-only schema migration logic
        ├── migrations/
        │   └── v18_to_v19.ts         # Placeholder migration (no-op)
        ├── serializers/
        │   ├── chunks.ts             # T3 — chunks.jsonl
        │   ├── embeddings.ts         # T4 — packed float32 + idx
        │   ├── kg.ts                 # T5 — kg_entities + kg_relations JSONL
        │   └── ops_audit.ts          # T6 — append-only preservation
        └── __tests__/
            ├── format.test.ts        # T1 round-trips
            ├── manifest.test.ts      # T2 canonicalization + parse
            ├── serializers.test.ts   # T3-T6 JSONL/binary round-trip
            ├── encryption.test.ts    # T7-T8 GCM tag, scrypt, tamper, AAD
            └── migration.test.ts     # T9 forward/backward/same
```

---

## Design Decisions (Encryption — D41 #2)

1. **AES-256-GCM + scrypt(N=2^17, r=8, p=1).** Pure Node `crypto` — zero external crypto deps. GCM tag is the only tamper detector — failing decrypt is a tamper signal, not a soft fail.
2. **AAD = sha256(manifest plaintext bytes).** Manifest stays unencrypted (counts/version/hostname inspectable via `tar -xzf manifest.json && jq .`), but tampering it breaks the AAD chain → all encrypted files fail decrypt with a single tag mismatch.
3. **Passphrase only via `NOX_EXPORT_PASSPHRASE` env or interactive stdin prompt.** Never argv (`ps` leak). The CLI layer (T10, deferred) rejects `--passphrase=` flags at parse time. This primitive `getPassphrase()` errors out if `process.stdin.isTTY` is false and env is unset.

---

## Run tests locally

```bash
cd staged-A2
npm install
npm test
```

Zero credentials, zero network calls. Synthetic test fixtures only.
