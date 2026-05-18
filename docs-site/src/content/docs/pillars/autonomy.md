---
title: Autonomy Pillar (A)
description: Data portability, provider abstraction, privacy, and zero-vendor validation.
sidebar:
  order: 2
---

> Your data stays on your disk. Your provider is your choice. Zero lock-in is a hard constraint, not a marketing claim.

## A1 — Privacy filter

13 regex patterns covering PII categories: email, phone, CPF/CNPJ (BR), credit card, API keys, passwords, JWT tokens, AWS credentials, and more.

- 68 test cases
- False positive rate: 1.7%
- Strips PII before storage; original content never written to DB

```typescript
import { filterPII } from './src/lib/privacy-filter';
const safe = filterPII(rawContent);  // returns redacted string
```

## A1.1 — Brazilian PII extension

Extended pattern set for Brazilian documents: RG, RENAVAM, PIS/PASEP, NIS, CEI, voter ID. Ships as additive layer on top of A1 base patterns.

## A2 — Export / import

Portable archive format: AES-256-GCM encryption + scrypt key derivation + AAD binding the archive to its intended destination.

```bash
# Export entire memory store to portable archive
nox-mem export ~/my-memory-backup.noxarchive --passphrase "..."

# Import on a different machine
nox-mem import ~/my-memory-backup.noxarchive --target ~/new-memory
```

The archive is self-contained: schema version, all chunks, all vectors, all KG data. No re-embedding required after import (vectors are included).

## A3 — Provider abstraction

Swappable embedding provider interface. Switch from Gemini to OpenAI to local without migrating data — vectors stay in the DB, new chunks use the new provider.

```bash
# Gemini (default)
export NOX_EMBEDDING_PROVIDER=gemini
export GEMINI_API_KEY=...

# OpenAI
export NOX_EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY=...

# Local (Ollama)
export NOX_EMBEDDING_PROVIDER=local
export NOX_EMBEDDING_BASE_URL=http://localhost:11434
```

:::caution[Dimension mismatch]
If you switch providers, new embeddings will be a different dimension than existing ones (Gemini=3072d, OpenAI-large=3072d, OpenAI-small=1536d). Mixed-dimension stores require re-embedding all chunks. Use `nox-mem re-embed --all` after switching.
:::

## A4 — Zero-vendor validation

8 invariants validated in CI in <1s:

1. No hardcoded API keys in source
2. All API calls use env vars
3. No external network calls at import time
4. Provider interface fully swappable
5. Export archive self-contained (no external references)
6. DB accessible without any API key
7. CLI commands work without network (except embed/kg commands)
8. No telemetry opt-out required (telemetry is off by default)

```bash
cd validation/zero-vendor
npm test
```
