# P6 — Mobile Sync Architecture Spec

> **Status:** Spec (2026-05-18) — P6 candidate (pillar P, Roadmap §5)
> **Tagline:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*
> **Pillar:** P — Product UX
> **Dependências diretas:** A2 (export/import portátil), P2 (hooks auto-capture), L2 (conflict detection KG)
> **Gate:** P1+P2+A2 merged e estáveis em prod ≥ 2 semanas antes de iniciar P6

---

## Sumário

1. [Casos de uso](#1-casos-de-uso)
2. [Opções de arquitetura](#2-opções-de-arquitetura)
3. [Abordagem recomendada: Híbrido B+C](#3-abordagem-recomendada-híbrido-bc)
4. [Considerações de schema](#4-considerações-de-schema)
5. [Resolução de conflitos](#5-resolução-de-conflitos)
6. [Modelo de segurança](#6-modelo-de-segurança)
7. [Superfície de API (lado VPS)](#7-superfície-de-api-lado-vps)
8. [Arquitetura do app mobile](#8-arquitetura-do-app-mobile)
9. [Escopo MVP](#9-escopo-mvp)
10. [Roadmap de fases](#10-roadmap-de-fases)

---

## 1. Casos de uso

### Primários

| ID | Cenário | Frequência | Criticidade |
|----|---------|------------|-------------|
| UC-1 | **Captura mobile** — usuário lê artigo no iPhone, seleciona parágrafo, adiciona memória com contexto rápido | Daily | Alta |
| UC-2 | **Query mobile** — usuário está em reunião, pergunta "o que eu decidi sobre X em abril?" diretamente do telefone | Several/day | Alta |
| UC-3 | **Sync de contexto** — ao abrir app mobile, último corpus relevante (chunks recentes + KG do usuário) já está disponível offline | Several/week | Média |
| UC-4 | **Captura de voz** — usuário grava nota de voz de 30s; app transcreve e ingere como chunk com `type=voice_note` | Daily | Média |
| UC-5 | **Revisão de memórias** — usuário faz triagem de chunks recentes, edita, marca obsoleto | Weekly | Baixa |

### Secundários (deferred para v2+)

- Notificações push quando KG detecta conflito (L2) relevante ao usuário
- Widget de tela inicial com "last reflection"
- Watch app (Apple Watch / Wear OS) para captura de voz ultra-rápida

---

## 2. Opções de arquitetura

### Opção A — Relay hospedado (Nox-Supermem como intermediário)

```
iPhone/Android  →  Nox-Supermem Relay  →  VPS do usuário
                    (hosted by us)
```

**Como funciona:**
- App mobile fala com um servidor relay SaaS que o time mantém
- Relay faz proxy autenticado para a VPS do usuário via credenciais armazenadas no relay
- Dados em trânsito cifrados; dados em repouso na relay podem ser anonimizados ou eliminados imediatamente após forward

**Prós:**
- Setup mais simples para usuário: só configurar URL da VPS uma vez
- Funciona mesmo sem VPN ou IP público estático na VPS
- Proxy pode bufferizar quando VPS está offline

**Contras:**
- **Viola o moat de autonomia** — terceiro (mesmo nós) toca os dados
- Custo operacional contínuo (infra relay)
- Single point of failure fora do controle do usuário
- Abre superfície de ataque adicional
- Contradiz "zero vendor lock-in" e "zero SaaS"

**Veredicto: DESCARTADA.** Viola os princípios não-negociáveis do Pillar A. A2 foi construído exatamente para não precisar disto.

---

### Opção B — P2P direto via Tailscale/WireGuard

```
iPhone/Android  ←→  Tailscale tunnel  ←→  VPS do usuário
                    (P2P, criptografado)
```

**Como funciona:**
- Usuário instala Tailscale (ou WireGuard) no iPhone e na VPS
- VPS recebe um IP estável na rede privada Tailscale (ex: `100.x.y.z`)
- App mobile aponta `NOX_API_BASE_URL` para esse IP + porta 18802
- Toda comunicação passa pelo SDK TypeScript (mesma `NoxMemClient`) ou equivalente Swift/Kotlin

**Prós:**
- Zero infra nossa: o Tailscale faz o tunnel
- VPS não precisa de IP público exposto
- Autenticação via Bearer token existente (NOX_API_TOKEN)
- Usa exatamente os endpoints de hoje (`/api/search`, `/api/answer`, etc.)
- Autonomia 100% preservada

**Contras:**
- Requer que usuário configure Tailscale (passo extra de setup)
- App mobile fica inutilizável quando offline ou fora do tunnel
- Tailscale tem plano free limitado; pode criar fricção para usuários não-técnicos
- WireGuard puro requer IP público ou port-forward (mais avançado)

**Veredicto: RECOMENDADA como camada de conectividade online.** Não resolve o problema offline.

---

### Opção C — DB local mobile + sync periódico

```
iPhone                           VPS
SQLite local (subset)  ←→  nox-mem API (delta sync)
(offline-capable)
```

**Como funciona:**
- App mobile mantém SQLite local com subset do corpus (chunks recentes + KG relevante)
- Consultas e capturas operam primeiro no DB local (offline-capable)
- Em background, quando há conectividade, sync bidirecional via A2 delta export + merge
- Conflict resolution baseado em L2 (ver §5)

**Prós:**
- Funciona 100% offline após sync inicial
- Latência de query = zero (local SQLite)
- Não depende de VPN ativa o tempo todo

**Contras:**
- Complexidade: dois DBs para manter em sync
- Conflict resolution não trivial (ver §5)
- Storage no device (subset do corpus pode ser grande)
- Dois code paths de ingest (local vs VPS) devem convergir

**Veredicto: NECESSÁRIA para offline. Usada em combinação com B.**

---

## 3. Abordagem recomendada: Híbrido B+C

```
                    ONLINE                        OFFLINE
                    ──────                        ───────

iPhone/Android ──┐
                 │  Tailscale tunnel        DB local SQLite (subset)
                 ├──────────────────►  VPS  ◄──────────────────────
                 │  (quando online)    18802  (delta sync periódico)
                 │
                 └─ Fallback → DB local (quando offline)
```

**Princípio de operação:**

1. **Online (Tailscale ativo):** app fala diretamente com `/api/*` na VPS. Capturas vão direto ao nox-mem.db canônico. Queries respondem com corpus completo.

2. **Offline (sem tunnel):** app usa DB local. Capturas são enfileiradas com `sync_status=pending`. Queries limitadas ao subset sincronizado.

3. **Reconexão:** ao detectar tunnel ativo, app dispara delta sync:
   - Upload: chunks `pending` → ingest na VPS via `POST /api/ingest`
   - Download: `GET /api/export?since=<last_sync_ts>` → merge no DB local

4. **Conflitos:** qualquer par (local, VPS) onde mesmo `chunk_id` tem conteúdo divergente vai para L2 conflict detection (ver §5).

**Razão da escolha B+C sobre A:**
- B preserva autonomia (sem relay nosso)
- C garante utilidade offline (captura e query sem tunnel)
- Combinação cobre 95% dos casos de uso sem abrir mão do moat de autonomia

---

## 4. Considerações de schema

### Subset sincronizado para mobile

O corpus completo (~69k chunks, ~1.24 GB) é grande demais para mobile. O sync deve ser seletivo:

| Tabela | O que sincroniza | Critério de seleção |
|--------|-----------------|---------------------|
| `chunks` | Subset relevante | `type IN ('decision','lesson','project','person','feedback')` + recency ≤ 90d + `pain >= 0.3` |
| `chunks_fts` | Reconstruído localmente | FTS5 rebuilt no device após sync |
| `vec_chunks` | Não sincroniza em v1 | Embeddings 3072d = 12KB/chunk × 5k = 60MB+ — deferir para v2 |
| `kg_entities` | Todos (< 500KB) | Entidades compactas — sincroniza completo |
| `kg_relations` | Todos | Relações compactas — sincroniza completo |
| `ops_audit` | Não sincroniza | Log de operações — permanece na VPS |

**Schema mobile (SQLite lite):**

```sql
-- Versão reduzida, sem vec_chunks e sem ops_audit
CREATE TABLE mobile_chunks (
  id          INTEGER PRIMARY KEY,
  vps_id      INTEGER NOT NULL,        -- chunk_id canônico na VPS
  text        TEXT NOT NULL,
  type        TEXT,
  created_at  TEXT,
  updated_at  TEXT,
  pain        REAL DEFAULT 0.2,
  section     TEXT,
  section_boost REAL DEFAULT 1.0,
  sync_status TEXT DEFAULT 'synced',   -- 'synced' | 'pending' | 'conflict'
  last_sync_ts TEXT
);

CREATE TABLE mobile_kg_entities (
  id      INTEGER PRIMARY KEY,
  vps_id  INTEGER NOT NULL,
  name    TEXT NOT NULL,
  type    TEXT,
  summary TEXT
);

CREATE TABLE mobile_kg_relations (
  id               INTEGER PRIMARY KEY,
  vps_id           INTEGER NOT NULL,
  source_entity_id INTEGER REFERENCES mobile_kg_entities(id),
  target_entity_id INTEGER REFERENCES mobile_kg_entities(id),
  relation_type    TEXT,
  confidence       REAL   -- L3
);

CREATE TABLE mobile_sync_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  synced_at   TEXT,
  direction   TEXT,        -- 'upload' | 'download'
  chunks_sent INTEGER,
  chunks_recv INTEGER,
  conflicts   INTEGER,
  error       TEXT
);
```

### Mapeamento de IDs

O mobile usa `vps_id` como referência canônica. Chunks criados offline recebem `vps_id = NULL` até sync bem-sucedido. Após sync, o VPS retorna o `id` canônico e o app atualiza `vps_id`.

---

## 5. Resolução de conflitos

### Estratégia geral: merge baseado em L2 + timestamp

A resolução de conflitos opera em dois níveis:

#### Nível 1 — Conflito de chunk (texto divergente)

Quando um chunk existe no DB local e na VPS com conteúdo diferente:

```
Regra:  VPS wins se vps.updated_at > local.updated_at
        Local wins se local.updated_at > vps.updated_at (usuário editou offline)
        Caso exato: VPS wins (conservador)
```

Conflitos onde `abs(vps.updated_at - local.updated_at) < 5min` (edição "simultânea") são marcados `sync_status='conflict'` e surfaceados no app para resolução manual.

#### Nível 2 — Conflito de KG via L2

Quando o usuário captura memória mobile que contradiz uma relação existente no KG da VPS, L2 conflict detection (já implementado — Wave C, PR #13 + #51) é invocado no momento do merge:

```
POST /api/kg/conflicts/check
Body: { entity_ids: [...], text: "<new chunk text>" }
```

L2 retorna `KgConflict[]` com score de severidade. Conflitos com `severity >= 0.7` são marcados para triagem manual; os demais são aceitos com flag `needs_review`.

#### Nível 3 — Conflito de texto cru (mesma chunk_id, texto editado)

Usar diff three-way simples:
- Base = texto na VPS no momento do último sync bem-sucedido (armazenado em `mobile_sync_log`)
- Mine = texto editado localmente offline
- Theirs = texto editado na VPS

Se merge automático possível (não há sobreposição de linhas) → auto-merge.
Se conflito de linha → surfacear no app com UI de resolução.

### Garantias

- Nenhum dado é descartado silenciosamente
- Conflitos não resolvidos ficam marcados `sync_status='conflict'` até ação explícita do usuário
- VPS é sempre a fonte de verdade para `ops_audit` (não replicado)
- `retention_days` da VPS tem precedência sobre mobile em conflitos de metadado

---

## 6. Modelo de segurança

### Princípios

1. **Zero dados nos nossos servidores** — híbrido B+C garante que dados transitam apenas entre device do usuário e VPS do usuário
2. **Cifra em trânsito** — Tailscale usa WireGuard (ChaCha20-Poly1305) end-to-end
3. **Cifra em repouso** — DB local mobile usa SQLCipher (AES-256-CBC) com passphrase derivada do keychain do device
4. **Auth** — Bearer token (`NOX_API_TOKEN`) gerado no VPS, armazenado no Keychain (iOS) / Android Keystore, nunca exposto em logs
5. **Sem chaves embutidas no build** — BYO key obrigatório (herda princípio A4)

### Passphrase para DB local

Usa A2 como inspiração: chave derivada via `scrypt(N=2^14)` a partir de passphrase + device-unique salt. Parâmetros mais conservadores que A2 (N menor) porque geração é on-device sem CPU de servidor.

```
key = scrypt(passphrase, device_salt, N=2^14, r=8, p=1, len=32)
```

Passphrase pode ser biometria-gated (Face ID / Touch ID / fingerprint) via Secure Enclave / StrongBox.

### Threat model (mobile-specific)

| Ameaça | Mitigação |
|--------|-----------|
| Device roubado/comprometido | SQLCipher + biometria-gate; remote wipe via API `DELETE /api/mobile/sessions/<device_id>` |
| MitM no tunnel | WireGuard garante autenticação mútua; Tailscale certificate pinning |
| Token vazado via debug log | Token armazenado apenas no Keychain; zero `console.log(token)` enforced por lint |
| Sync com VPS comprometida | Certificate pinning no Tailscale; usuário controla VPS |
| Captura acidental de PII | A1 privacy filter invocado no device antes de qualquer ingest (mesmo path do P2) |

### Permissões mínimas requeridas

| Permissão | Uso | Gate |
|-----------|-----|------|
| Microfone | Captura de voz (UC-4) | Opt-in explícito por feature |
| Câmera | OCR de documentos (v2+) | Opt-in, não no MVP |
| Rede local | Tailscale VPN tunnel | Obrigatório |
| Notificações | Alertas de sync e conflitos | Opt-in |
| Contacts | Pessoas mencionadas na memória | Não solicitado (v1) |

---

## 7. Superfície de API (lado VPS)

Os endpoints abaixo precisam ser adicionados ou estendidos no nox-mem HTTP API (porta 18802).

### Endpoints novos (P6)

#### `POST /api/mobile/sessions`
Registra um device mobile. Retorna `device_id` (UUID) para rastreamento de sync.

```jsonc
// Request
{
  "device_name": "Toto iPhone 16 Pro",
  "platform": "ios",
  "app_version": "1.0.0",
  "public_key": "<base64-encoded ECDH pubkey>"  // para key agreement futuro
}

// Response 201
{
  "device_id": "d7e3...",
  "granted_at": "2026-05-18T12:00:00Z"
}
```

#### `DELETE /api/mobile/sessions/<device_id>`
Revoga acesso de um device. Tokens emitidos para esse device ficam inválidos imediatamente.

#### `GET /api/mobile/sync/export`
Delta export compacto para mobile. Equivale a `GET /api/export` com filtros específicos.

```
GET /api/mobile/sync/export?since=<ISO8601>&device_id=<uuid>&types=decision,lesson,project,person,feedback&max_pain=0.3
```

Retorna um archive A2 com subset (sem embeddings, sem ops_audit). Content-Type: `application/octet-stream`.

Parâmetros:
- `since` — timestamp do último sync bem-sucedido
- `device_id` — para log de acesso por device
- `types` — filtro de chunk types (default: all)
- `min_pain` — filtro de pain (default: 0.0)
- `max_chunks` — limite máximo (default: 5000, cap hard: 10000)

#### `POST /api/mobile/sync/import`
Upload de chunks capturados offline. Equivale ao caminho de ingest existente mas com rastreamento de device.

```jsonc
// Request (multipart/form-data)
{
  "device_id": "d7e3...",
  "chunks": [
    {
      "local_id": "local-uuid-123",
      "text": "...",
      "type": "lesson",
      "created_at": "2026-05-18T09:23:00Z",
      "pain": 0.6
    }
  ]
}

// Response 200
{
  "accepted": 5,
  "rejected": 0,
  "id_map": { "local-uuid-123": 70001 },  // local_id → vps_id canônico
  "conflicts": []
}
```

#### `GET /api/mobile/sessions`
Lista devices registrados. Para gerenciamento pelo usuário.

### Endpoints existentes reutilizados

| Endpoint | Uso mobile |
|----------|-----------|
| `GET /api/search` | Query online (B) |
| `POST /api/answer` | Answer primitive online (P1) |
| `GET /api/health` | Connectivity check |
| `POST /api/kg/conflicts/check` | L2 conflict detection no merge |

### Autenticação mobile

Todos os endpoints `/api/mobile/*` exigem `Authorization: Bearer <NOX_API_TOKEN>`.

O token é gerado no VPS (`nox-mem generate-token --device "iPhone"`) e configurado no app mobile no setup. O app armazena no Keychain/Keystore.

---

## 8. Arquitetura do app mobile

### Comparativo de plataformas

| Critério | Native (Swift + Kotlin) | Flutter | React Native |
|----------|------------------------|---------|--------------|
| Performance SQLite | Excelente (FMDB/Room nativas) | Boa (sqflite) | Razoável (better-sqlite3-android limitado) |
| Tailscale SDK | Disponível ambas | Indisponível nativo | Wrapper parcial |
| SQLCipher | Excelente ambas | Plugin disponível | Plugin disponível |
| Biometria | Secure Enclave / StrongBox nativo | LocalAuth plugin | OK |
| Time-to-market | 2x (dois codebases) | 1.4x | 1.3x |
| Manutenção longterm | Harder (2 codebases) | Medium | Medium |

**Recomendação: Flutter.**

Razões:
1. Único codebase para iOS e Android
2. `sqflite` + `sqlcipher_flutter_libs` proveem SQLite criptografado
3. Performance SQLite adequada para o subset (~5k chunks)
4. Tailscale não tem SDK Flutter nativo, mas a conexão pode ser gerenciada externamente (Tailscale app precisa estar rodando — não é integração profunda)
5. Biometria via `local_auth` plugin
6. Comunidade ativa; Dart é tipado; debug tools maduros

**Alternativa considerada: React Native.** Descartada porque `better-sqlite3` não tem suporte sólido em React Native Android e o ecosistema mobile RN tem mais fricção com SQLCipher.

**Native Swift + Kotlin** reservado para v2 se Flutter mostrar limitações.

### Estrutura de pacotes Flutter (esboço)

```
nox-mem-mobile/
├── lib/
│   ├── core/
│   │   ├── db/          # SQLite local (sqflite + SQLCipher)
│   │   ├── sync/        # Engine de sync B+C
│   │   ├── api/         # HTTP client (equivalente NoxMemClient)
│   │   ├── privacy/     # Port do A1 filter (Dart)
│   │   └── crypto/      # scrypt + AES passphrase key
│   ├── features/
│   │   ├── capture/     # UC-1 (text) + UC-4 (voice)
│   │   ├── search/      # UC-2
│   │   ├── sync/        # UC-3 (UI de sync status)
│   │   └── review/      # UC-5 (triagem de memórias)
│   └── ui/
│       ├── widgets/
│       └── screens/
├── android/
├── ios/
└── test/
```

### Estado da conectividade (state machine)

```
    OFFLINE ──── tunnel detectado ──── CONNECTING
       ↑                                   │
       │                                   ▼
  disconnect                          ONLINE (B)
       │                                   │
       └─────────────────────────── sync trigger
```

O app monitora conectividade via `connectivity_plus` + testa `GET /api/health` periodicamente (60s). Ao voltar online, sync automático dispara se `pending_chunks > 0` ou `last_sync_ts > 1h atrás`.

---

## 9. Escopo MVP

### v1 — Ship

| Feature | Prioridade | Complexidade |
|---------|-----------|-------------|
| Setup: configurar VPS URL + Bearer token | P0 | Baixa |
| Setup: Tailscale integrado (abrir app Tailscale se não instalado) | P0 | Baixa |
| Query online (search + answer via B) | P0 | Baixa — reutiliza API existente |
| Captura de texto selecionado (share extension iOS/Android) | P0 | Média |
| DB local com subset sincronizado (C) | P0 | Alta |
| Sync delta automático (upload pending + download novos) | P0 | Alta |
| Captura de voz com transcrição (UC-4) | P1 | Média — usa speech-to-text nativo |
| UI de conflicts (triagem básica) | P1 | Média |
| Segurança: SQLCipher + biometria-gate | P0 | Média |

### Deferido para v2+

| Feature | Razão do defer |
|---------|---------------|
| Embeddings no device (vec_chunks mobile) | 60MB+ de dados, bateria, precisa de modelo on-device |
| Notificações push de conflito | Requer infra de push (APNS/FCM) — evita SaaS em v1 |
| Widget / complication | Nice-to-have, não core |
| Apple Watch / Wear OS | Scope grande |
| Câmera + OCR | Aguarda E12 estável |
| Multiple VPS profiles | Complexidade de sync multi-origem |
| Web app (PWA) | Sobrepõe com P5 viewer — avaliar overlap |

### Critérios de DoD para MVP

- [ ] UC-1, UC-2, UC-3 funcionando em iOS e Android
- [ ] Offline-capable: captura funciona sem internet
- [ ] Sync bem-sucedido verificado por `mobile_sync_log` + `/api/health`
- [ ] A1 privacy filter portado para Dart e testado (15+ padrões)
- [ ] SQLCipher ativo; biometria-gate funcionando
- [ ] Zero dados em servidores do time
- [ ] Setup em < 5 minutos (VPS URL + token + Tailscale)
- [ ] Testes: 80% coverage em `core/sync/` e `core/db/`

---

## 10. Roadmap de fases

### P6 — Candidato no Pillar P

**Gate de entrada:** P1+P2+A2 merged e estáveis ≥ 2 semanas (Fev 2026).

| Fase | Período estimado | Entregável |
|------|-----------------|-----------|
| **P6-T1** — VPS API surface | 2d | Endpoints `/api/mobile/*` (§7) + testes |
| **P6-T2** — Flutter scaffold | 3d | Projeto Flutter base + CI (iOS/Android build) |
| **P6-T3** — DB local + sync engine (online) | 5d | sqflite + schema mobile + sync delta B |
| **P6-T4** — DB local offline + sync engine (offline) | 4d | Pending queue + auto-upload ao reconectar |
| **P6-T5** — A1 filter port (Dart) | 2d | 15+ padrões PII + 20 testes |
| **P6-T6** — Captura de texto (share extension) | 3d | iOS Share Extension + Android Intent |
| **P6-T7** — Captura de voz | 2d | speech_to_text + ingest |
| **P6-T8** — Segurança (SQLCipher + biometria) | 2d | scrypt key + biometria-gate |
| **P6-T9** — UI search + answer | 3d | Telas search e answer (P1 primitivo online) |
| **P6-T10** — UI conflicts + sync status | 2d | Triagem e status indicator |
| **P6-T11** — QA + TestFlight / beta interno | 3d | Smoke tests + beta build |
| **Total estimado** | ~31d de dev | |

### Dependências críticas no path

```
P1 (answer primitive) ──────────────┐
P2 (hooks + A1 filter) ─────────────┼──► P6-T1 → P6-T2 → ... → MVP
A2 (export/import delta) ───────────┘
L2 (conflict detection) ──────────── P6-T10
```

### Métricas de sucesso pós-launch

- Sync delta p95 ≤ 10s para 500 chunks
- Captura offline: zero data loss em 100 sessões offline simuladas
- Setup time mediano: < 5 minutos
- Crash rate: < 0.1% por sessão (Firebase Crashlytics)

---

## Cross-links

- [P1 answer primitive](./2026-05-17-P1-answer-primitive.md) — primitivo de query que mobile reutiliza
- [P2 hooks auto-capture](./2026-05-17-P2-hooks-autocapture.md) — arquitetura de pipeline que informa design das 5 camadas mobile
- [A2 export/import](./2026-05-17-A2-export-import.md) — formato de delta sync (manifest.json + chunks.jsonl)
- [L2 conflict detection](./2026-05-17-L2-conflict-detection.md) — engine invocada no merge de conflitos
- [ROADMAP.md §5 Pillar P](../docs/ROADMAP.md) — contexto de prioridade
- [DECISIONS.md](../docs/DECISIONS.md) — princípios não-negociáveis (autonomy, BYO key)

---

*Spec v1.0 — 2026-05-18. Próxima revisão: quando P1+P2+A2 merged + 2 semanas estáveis.*
