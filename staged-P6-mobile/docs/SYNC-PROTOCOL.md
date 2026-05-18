# P6 Sync Protocol — delta bidirecional via A2

> **Status:** design doc (Phase 1 kickoff, P6 spec PR #82).
> **Implementação:** Phase 3 (deferred).
> **Princípio:** zero SaaS, Tailscale tunnel + A2 archive format reaproveitado.

---

## 1. Visão geral

O sync mobile reusa o formato **A2 archive** (manifest.json + chunks.jsonl) já implementado em `staged-A2/edits/src/lib/archive/`. Não há novo binary format — somos consumidores de A2 com filtros mobile-friendly.

```
┌────────────┐        Tailscale            ┌──────────────┐
│  iPhone    │ ←─────────────────────────→ │  VPS         │
│            │   100.x.y.z:18802           │  nox-mem-api │
│  Phase 3   │                             │              │
│  SyncEngine│                             │  /api/mobile │
│            │                             │  /sync/*     │
│  SQLCipher │                             │  endpoints   │
│  local DB  │                             │              │
└────────────┘                             └──────────────┘
```

---

## 2. State machine

```
        OFFLINE ──── tunnel up ────┐
            ↑                      ▼
       disconnect              CONNECTING
            │                      │
            │                      │ health check ok
            │                      ▼
            └────── disconnect ── ONLINE
                                   │
                                   │ pending > 0 OR last_sync_ts > 1h
                                   ▼
                                SYNCING ── done ── ONLINE
                                   │
                                   └── error ── OFFLINE (retry backoff)
```

Backoff: 1s → 5s → 30s → 2min → 10min (capped). Reset ao voltar pra ONLINE limpo.

---

## 3. Endpoints VPS (espelha §7 do spec)

| Método | Path | Uso mobile |
|--------|------|------------|
| `POST` | `/api/mobile/sessions` | Registra device (one-time pairing via QR) |
| `DELETE` | `/api/mobile/sessions/<device_id>` | Revoga acesso (remote wipe) |
| `GET` | `/api/mobile/sync/export?since=...&device_id=...` | Download delta (A2 archive) |
| `POST` | `/api/mobile/sync/import` | Upload chunks pendentes |
| `GET` | `/api/health` | Liveness probe (Tailscale state machine) |
| `POST` | `/api/kg/conflicts/check` | L2 conflict check no merge |

Autenticação: `Authorization: Bearer <NOX_API_TOKEN>` em todos endpoints `/api/mobile/*`.

---

## 4. Delta sync — VPS → mobile (download)

```
GET /api/mobile/sync/export?since=2026-05-18T00:00:00Z&device_id=d7e3...&types=decision,lesson,project,person,feedback&max_pain=0.3
Authorization: Bearer <NOX_API_TOKEN>
```

Filtros (espelha schema mobile, §4 do spec):

| Param | Default | Cap |
|-------|---------|-----|
| `since` | epoch | required |
| `types` | all | `decision,lesson,project,person,feedback` típico |
| `min_pain` | 0.0 | — |
| `max_pain` | — | 1.0 |
| `max_chunks` | 5000 | 10000 hard cap |

Resposta: `application/octet-stream` com A2 archive (header + chunks.jsonl gzip).

### Algoritmo mobile-side

1. Streamar response em chunks de 64KB pra disco temp (evitar OOM).
2. Validar header A2 (magic bytes + version).
3. Descompactar chunks.jsonl streaming.
4. Para cada linha:
   - Parse JSON → MobileChunkPayload.
   - Verificar se já existe localmente via `vps_id`:
     - Não existe → INSERT.
     - Existe + `vps.updated_at > local.updated_at` → UPDATE (VPS wins).
     - Existe + `local.updated_at > vps.updated_at` → conflict (ver §6).
5. Após drain, rebuild FTS5 index local (`INSERT INTO mobile_chunks_fts(mobile_chunks_fts) VALUES('rebuild')`).
6. Atualizar `_meta.last_sync_ts` para timestamp atômico do server response header.
7. Inserir log em `mobile_sync_log` com `direction='download'` + counts + duration.

---

## 5. Delta sync — mobile → VPS (upload)

```
POST /api/mobile/sync/import
Content-Type: application/json
Authorization: Bearer <NOX_API_TOKEN>

{
  "device_id": "d7e3...",
  "chunks": [
    {
      "local_id": "uuid-1",
      "text": "...",
      "type": "lesson",
      "created_at": "2026-05-18T09:23:00Z",
      "pain": 0.6
    }
  ]
}
```

Resposta:

```json
{
  "accepted": 5,
  "rejected": 0,
  "id_map": { "uuid-1": 70001 },
  "conflicts": []
}
```

### Algoritmo mobile-side

1. SELECT pending de `mobile_pending_uploads` LIMIT 100 (batch size).
2. Para cada, JOIN com `mobile_chunks` pegar texto/type/pain/created_at.
3. POST batch. Timeout 30s.
4. Para cada `id_map[local_id]`:
   - UPDATE mobile_chunks SET vps_id=<id>, sync_status='synced', last_sync_ts=now() WHERE id=...
   - DELETE FROM mobile_pending_uploads WHERE local_id=...
5. Para cada `conflicts`: marcar `sync_status='conflict'` e surfacear na UI.
6. Em caso de erro de rede: incrementar `attempts` e retentativa via backoff.
7. Inserir log `mobile_sync_log` com `direction='upload'`.

---

## 6. Resolução de conflitos

Espelha §5 do spec; resumo executável:

### N1 — chunk texto divergente

| Caso | Ação |
|------|------|
| `vps.updated_at > local.updated_at` | VPS wins (UPDATE local) |
| `local.updated_at > vps.updated_at` | Local wins (push no próximo upload) |
| `abs(diff) < 5min` | mark `conflict`, surface UI |

### N2 — KG conflict via L2

Ao inserir chunk que mencione entidades, mobile faz:

```
POST /api/kg/conflicts/check
Body: { entity_ids: [...], text: "..." }
```

Retorno `KgConflict[]`:
- `severity >= 0.7` → mark `needs_review`
- `severity < 0.7` → accept silently com flag

### N3 — three-way diff (texto editado offline + VPS editou)

Mobile mantém `base_text` (texto na VPS no momento do último sync ok) em `mobile_chunks.base_text`. Ao detectar update VPS-side de chunk que tem edição local:

```
mine = local.text (editado offline)
theirs = vps.text (editado online)
base = mobile_chunks.base_text (ancestor)
```

Tentar merge linha-a-linha. Se sem overlap → auto-merge. Senão → conflict UI com 3-pane diff.

---

## 7. Encryption

| Layer | Mecanismo | Notas |
|-------|-----------|-------|
| In transit | Tailscale WireGuard (ChaCha20-Poly1305) | Mutual auth via Tailscale identity |
| At rest (device) | SQLCipher AES-256-CBC | Passphrase via scrypt(N=2^14) de device-unlock + salt |
| Token | Bearer no Authorization header | Storage no Keychain/Keystore (flutter_secure_storage) |

**Não há cifra app-level adicional** sobre payload HTTP. O WireGuard tunnel já fornece e2e crypto entre device e VPS. Camadas extras só adicionam complexity sem ganho real.

---

## 8. Pairing (one-time)

Setup do device usa **QR code** gerado na VPS:

```
nox-mem generate-mobile-token --device "Toto iPhone 16 Pro" > /tmp/token.json
qrencode -t ANSIUTF8 -r /tmp/token.json
```

QR encode contém:

```json
{
  "vps_url": "http://100.x.y.z:18802",
  "bearer_token": "<NOX_API_TOKEN>",
  "device_id_hint": "d7e3..."
}
```

App lê via câmera, POST em `/api/mobile/sessions`, recebe `device_id` canônico, armazena tudo no Keychain. Done.

---

## 9. Métricas de sucesso

| Métrica | Target |
|---------|--------|
| Delta sync 500 chunks p95 | ≤ 10s |
| Captura offline → primeiro upload no reconectar | ≤ 30s |
| Zero data loss em 100 sessões offline simuladas | 100% |
| Conflicts detectados manualmente | < 1% do total syncs |
| FTS5 rebuild p95 (5k chunks) | ≤ 2s |

---

## 10. Notas de implementação Phase 3

- Worker isolate dedicado pra sync engine — evita jank na UI thread.
- `mobile_pending_uploads.attempts` incrementa a cada falha; após 5 attempts, mark `failed` + surface UI.
- Retentativas usam `Connectivity().onConnectivityChanged` como trigger, não polling burro.
- Log `mobile_sync_log` é append-only mas NÃO precisa de trigger DB-level — UI controla.
- Para futuras vec_chunks sync (v2+), o A2 archive já suporta embeddings; basta toggle de flag `include_embeddings=1` no export endpoint.

---

## Cross-links

- Spec P6: [`specs/2026-05-18-P6-mobile-sync.md`](../../specs/2026-05-18-P6-mobile-sync.md)
- A2 archive format: [`staged-A2/edits/src/lib/archive/format.ts`](../../staged-A2/edits/src/lib/archive/format.ts)
- L2 conflict detection: [`specs/2026-05-17-L2-conflict-detection.md`](../../specs/2026-05-17-L2-conflict-detection.md)
- P1 answer primitive: [`specs/2026-05-17-P1-answer-primitive.md`](../../specs/2026-05-17-P1-answer-primitive.md)
