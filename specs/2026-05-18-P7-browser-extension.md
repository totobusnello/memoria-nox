# P7 — Browser Extension Spec

> **Status:** Spec (2026-05-18) — P7 candidate (pillar P, Roadmap §5)
> **Tagline:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*
> **Pillar:** P — Product UX
> **Dependências diretas:** P1 (answer primitive), P2 (hooks auto-capture), A1 (privacy filter)
> **Gate:** P1+P2 merged e estáveis em prod ≥ 2 semanas antes de iniciar P7

---

## Sumário

1. [Casos de uso](#1-casos-de-uso)
2. [Arquitetura — Manifest V3](#2-arquitetura--manifest-v3)
3. [Permissões](#3-permissões)
4. [Comunicação com nox-mem](#4-comunicação-com-nox-mem)
5. [Privacidade](#5-privacidade)
6. [Modelo de autenticação](#6-modelo-de-autenticação)
7. [UI/UX](#7-uiux)
8. [Integração com P2 hooks](#8-integração-com-p2-hooks)
9. [Escopo MVP](#9-escopo-mvp)
10. [Roadmap de fases](#10-roadmap-de-fases)

---

## 1. Casos de uso

### Primários

| ID | Cenário | Frequência | Criticidade |
|----|---------|------------|-------------|
| UC-1 | **Save selection** — usuário seleciona parágrafo de artigo, right-click → "Save to nox-mem" | Daily | Alta |
| UC-2 | **Auto-capture interessante** — ao ler artigo, classificador detecta conteúdo relevante (tutorial, decisão técnica, benchmarks) e sugere captura | Several/week | Média |
| UC-3 | **Omnibox search** — usuário digita `nx <query>` na barra de endereços e vê resultados de memória | Several/day | Alta |
| UC-4 | **Inline answer** — ao digitar pergunta em campo de texto (ex: GitHub issue, Slack web, Notion), extensão reconhece padrão de pergunta e oferece resposta inline da memória | Several/day | Média |
| UC-5 | **Save current page** — salvar metadados da página atual (URL + título + resumo gerado) como chunk | Weekly | Baixa |

### Secundários (deferred)

- Auto-highlight de termos que aparecem na memória do usuário enquanto navega
- Import de highlights do Readwise/Kindle
- Captura de screenshots de código com OCR integrado (aguarda E12)

---

## 2. Arquitetura — Manifest V3

A extensão segue Manifest V3 (MV3) obrigatório para Chrome/Edge desde Jan 2024; compatível com Firefox via WebExtensions MV3 (mínimas adaptações).

### Componentes

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│                                                     │
│  ┌──────────────┐   ┌───────────────────────────┐   │
│  │ Service Worker│   │   Content Script          │   │
│  │ (background) │   │   (injetado em páginas)    │   │
│  │              │   │                            │   │
│  │ • message hub│◄──│ • selection listener       │   │
│  │ • fetch proxy│   │ • auto-capture classifier  │   │
│  │ • omnibox    │   │ • inline answer UI         │   │
│  │ • alarm      │   │ • privacy redact           │   │
│  └──────┬───────┘   └───────────────────────────┘   │
│         │                                            │
│  ┌──────▼───────┐                                    │
│  │  Popup       │                                    │
│  │  (action)    │                                    │
│  │ • search     │                                    │
│  │ • quick save │                                    │
│  │ • sync status│                                    │
│  └──────────────┘                                    │
└─────────────────┬───────────────────────────────────┘
                  │ fetch (localhost:18802)
                  ▼
         nox-mem HTTP API (:18802)
```

### Service Worker (background)

MV3 não permite background page persistente — usa Service Worker que pode terminar a qualquer momento.

**Responsabilidades:**
- Hub de mensagens (recebe de content-script e popup via `chrome.runtime.sendMessage`)
- Proxy de chamadas fetch para `http://127.0.0.1:18802` (content-scripts não podem chamar localhost diretamente no Firefox — precisa do service worker como intermediário)
- Handler do omnibox (`chrome.omnibox`)
- Alarm periódico para sync de estado (cada 5 minutos, via `chrome.alarms`)
- Gestão de fila de chunks pendentes (quando API está offline, enfileira em `chrome.storage.local`)

**NOTA sobre MV3 Service Worker lifecycle:** o service worker é terminado após ~30s de inatividade. Toda a state persistente deve usar `chrome.storage.local`, nunca variáveis em memória.

### Content Script

Injetado dinamicamente em páginas da allowlist (ver §5).

**Responsabilidades:**
- Detectar seleção de texto (`document.getSelection()`) e registrar handler de right-click via `chrome.contextMenus`
- Classificador de conteúdo (heurístico leve — ver §5)
- UI inline para inline answer (UC-4): injeta `<div>` flutuante quando detecta padrão de pergunta
- Redação de PII antes de enviar ao service worker

**IMPORTANTE:** Content script NUNCA chama a API diretamente. Todo tráfego vai via `chrome.runtime.sendMessage` → service worker → fetch localhost.

### Popup

HTML/CSS/JS em `popup.html` — abre ao clicar no ícone da extensão.

**Conteúdo:**
- Campo de busca com preview de resultados (3-5 chunks)
- Botão "Save page" / "Save selection" (se houver seleção ativa)
- Status da conexão com nox-mem (verde/vermelho)
- Link para configurações

---

## 3. Permissões

Princípio: **mínimo necessário**. Cada permissão com justificativa explícita.

### Permissões no manifest.json

```json
{
  "permissions": [
    "activeTab",
    "contextMenus",
    "storage",
    "alarms",
    "omnibox"
  ],
  "optional_permissions": [
    "tabs"
  ],
  "host_permissions": [
    "http://127.0.0.1:18802/*"
  ]
}
```

| Permissão | Uso | Obrigatória? |
|-----------|-----|-------------|
| `activeTab` | Acessar conteúdo da aba ativa quando usuário interage (não monitoring passivo) | Sim |
| `contextMenus` | Adicionar "Save to nox-mem" no right-click menu | Sim |
| `storage` | Armazenar configurações (API URL, token) e fila offline | Sim |
| `alarms` | Ping periódico de conectividade (5min) | Sim |
| `omnibox` | UC-3 — `nx <query>` na barra de endereços | Sim |
| `tabs` | (Optional) Ler URL e título da aba para "Save page" com metadata completa | Opt-in |
| `http://127.0.0.1:18802/*` | Host permission para fetch direto ao nox-mem local | Sim |

### O que NÃO é solicitado

| Permissão | Por que não |
|-----------|------------|
| `<all_urls>` | Desnecessária — content-script só roda em allowlist configurável |
| `history` | Não monitora histórico de navegação |
| `cookies` | Não acessa cookies |
| `webRequest` | Não intercepta tráfego de rede |
| `downloads` | Não acessa downloads |

### Firefox

Firefox usa permissão `host_permissions` diferente — adicionar `"127.0.0.1"` à lista de `permissions` ou usar `browser.permissions.request()` em runtime.

---

## 4. Comunicação com nox-mem

### Protocolo

**Único ponto de contato:** `http://127.0.0.1:18802` — porta do nox-mem HTTP API existente. Não há websockets ou SSE na extensão (MV3 service worker tem lifecycle limitado).

**Conexão localhost-only por design:** a extensão não funciona se nox-mem estiver em VPS remota sem Tailscale — ver §6.

### Endpoints usados

| Operação | Endpoint | Fluxo |
|----------|----------|-------|
| Salvar chunk | `POST /api/ingest` | Popup / content-script → SW → API |
| Buscar | `GET /api/search?q=<query>` | Popup / omnibox → SW → API |
| Resposta inline | `POST /api/answer` | Content-script → SW → API (P1) |
| Verificar conectividade | `GET /api/health` | SW (alarm 5min) → API |
| Status hooks | `GET /api/hooks/status` | Popup → SW → API (P2) |

### Fluxo de save (UC-1)

```
1. Usuário seleciona texto + right-click "Save to nox-mem"
2. Content-script:
   a. Captura: selection.toString() + page URL + title
   b. Redação PII (§5)
   c. chrome.runtime.sendMessage({ type: 'SAVE_CHUNK', payload: {...} })
3. Service Worker:
   a. Recebe mensagem
   b. Adiciona metadados: source_url, source_title, captured_at, provenance='browser_extension'
   c. fetch POST /api/ingest
   d. Se API offline: enfileira em chrome.storage.local['pending_chunks']
   e. Responde ao content-script: { success: true, chunk_id: 70001 }
4. Content-script: mostra toast "Saved" (500ms, não-intrusivo)
```

### Fluxo de omnibox (UC-3)

```
1. Usuário digita "nx <query>" na barra de endereços
2. chrome.omnibox.onInputChanged → SW → GET /api/search?q=<query>&limit=5
3. SW retorna sugestões formatadas como chrome.omnibox.SuggestResult[]
4. Usuário seleciona sugestão → abre nova aba com popup expandido mostrando resultado completo
   (ou navega para URL do source se o chunk tem source_url)
```

### Fluxo de inline answer (UC-4)

```
1. Content-script detecta padrão de pergunta em campo de texto ativo
   (heurística: campo focado + texto termina em "?" + len > 20 chars)
2. Debounce 800ms para evitar spam
3. content-script → chrome.runtime.sendMessage({ type: 'ANSWER', text: '...' })
4. SW → POST /api/answer { query: text, max_chunks: 3, citation_style: 'inline' }
5. SW → content-script: { answer: '...', citations: [...] }
6. Content-script: injeta painel flutuante ao lado do campo com resposta + botão "Insert"
7. Usuário clica "Insert" → texto da resposta inserido no campo
```

### Offline handling

Quando `GET /api/health` falha (API offline):
- Popup mostra badge vermelho + "nox-mem offline"
- Capturas são enfileiradas em `chrome.storage.local['pending_chunks']` (máx 100 itens, FIFO)
- Na próxima vez que API volta online (detectado pelo alarm de 5min), chunks pendentes são drenados

---

## 5. Privacidade

### Filosofia

A extensão toca em dados de qualquer página que o usuário visita. O risco é máximo. Mitigações são não-negociáveis.

### Allowlist de domínios (opt-in por domínio)

**Padrão: NÃO captura nenhuma página** sem configuração explícita.

Usuário adiciona domínios permitidos nas configurações:
```
✅ github.com
✅ news.ycombinator.com
✅ developer.mozilla.org
```

Content-script é injetado APENAS em tabs cujo domínio está na allowlist. `activeTab` garante que mesmo o script de conteúdo não roda em abas não permitidas.

**NUNCA na allowlist por padrão:**
- Bancos e fintech (`*.itau.com.br`, `*.nubank.com.br`, etc.)
- E-mail (`mail.google.com`, `outlook.com`)
- Saúde
- Qualquer domínio com `login`, `account`, `auth` no path

A UI de configuração deve sugerir uma lista segura de defaults (docs técnicas, news sites, etc.) sem pré-marcar nada.

### Redação antes de enviar

Antes de qualquer chunk sair do content-script, o A1 privacy filter é aplicado em JavaScript:

**Port do A1 filter para JS (não depende do servidor):**

```javascript
// Padrões de redação (port dos 13+ padrões do A1 + BR PII A1.1)
const REDACT_PATTERNS = [
  { pattern: /\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g, tag: '<cpf>' },       // CPF
  { pattern: /\b\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}\b/g, tag: '<cnpj>' },// CNPJ
  { pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, tag: '<email>' },
  { pattern: /\b(?:\+55\s?)?\(?\d{2}\)?\s?\d{4,5}-?\d{4}\b/g, tag: '<phone>' },
  { pattern: /\bsk-[a-zA-Z0-9]{32,}\b/g, tag: '<api_key>' },
  { pattern: /\bghp_[a-zA-Z0-9]{36}\b/g, tag: '<gh_token>' },
  { pattern: /\b(?:password|senha|secret|token|apikey)\s*[:=]\s*\S+/gi, tag: '<credential>' },
  // ... demais padrões do A1
];

function redact(text) {
  return REDACT_PATTERNS.reduce(
    (t, { pattern, tag }) => t.replace(pattern, tag),
    text
  );
}
```

**O texto redatado é enviado ao nox-mem; o texto original nunca sai do browser.**

### Auto-capture classifier (UC-2)

Classificador heurístico leve (sem LLM no content-script — custo e latência):

**Sinais positivos (sugere captura):**
- Página tem `<article>`, `<main>`, `<section>` com > 500 palavras
- Domínio é blog técnico, documentação, notícia
- Título contém: "how to", "tutorial", "benchmark", "vs", "comparison", "decision", "lesson", "post-mortem"
- Usuário ficou > 3 minutos na página (indica leitura, não bounce)

**Sinais negativos (não sugere):**
- URL contém: `/login`, `/account`, `/checkout`, `/payment`, `/admin`
- `<form>` com campo `type=password` visível
- Domínio não está na allowlist

**UI do classificador:** balão não-intrusivo na margem inferior direita, fácil de dispensar. "Save this page to nox-mem?" com botão Dismiss permanente para o domínio.

### Dados locais na extensão

`chrome.storage.local` armazena:
- Token de autenticação (Bearer) — nunca em `sync storage` (não sai do device)
- Configurações (API URL, allowlist)
- Fila offline (máx 100 chunks pendentes)

Nada vai para `chrome.storage.sync` (que sincroniza entre devices via conta Google/Microsoft).

---

## 6. Modelo de autenticação

### Localhost-only (default)

Por padrão, a extensão conecta em `http://127.0.0.1:18802`. Isso implica que o nox-mem deve estar rodando na mesma máquina que o browser.

**Para o cenário típico (dev/poder user, nox-mem no laptop local):** funciona sem configuração extra de auth. A API local pode aceitar requests sem token (`NOX_API_TOKEN` não configurado = localhost-only mode sem auth).

**Recomendado:** configurar `NOX_API_TOKEN` mesmo para localhost para evitar que outras extensões maliciosas façam requests à API.

### VPS remota via Tailscale

Quando nox-mem roda na VPS (caso de uso principal do Toto), o browser pode falar com ele via Tailscale:
1. Tailscale app rodando no laptop
2. VPS tem IP Tailscale (ex: `100.x.y.z`)
3. Na configuração da extensão, usuário muda `API URL` para `http://100.x.y.z:18802`
4. Token configurado obrigatório nesse caso (`NOX_API_TOKEN` setado na VPS)

Não é necessário abrir porta 18802 para internet pública — Tailscale faz o tunnel.

### Configuração

```jsonc
// chrome.storage.local['settings']
{
  "api_url": "http://127.0.0.1:18802",
  "auth_token": "",          // Bearer token — vazio = sem auth
  "allowlist": [],           // domínios permitidos
  "auto_capture": false,     // UC-2 opt-in
  "inline_answer": false,    // UC-4 opt-in
  "omnibox_prefix": "nx"     // prefixo omnibox
}
```

**Importante:** `auth_token` nunca vai para `chrome.storage.sync`.

### CORS

A API do nox-mem precisará aceitar requests de `chrome-extension://<id>` no header `Origin`. Adicionar à lista de allowed origins no HTTP server:

```typescript
// src/api/server.ts — extensão necessária para P7
const ALLOWED_ORIGINS = [
  "http://127.0.0.1:18802",        // self
  /^chrome-extension:\/\//,        // Chrome extensions
  /^moz-extension:\/\//,           // Firefox extensions
];
```

Isso é uma mudança pequena no servidor existente — não um endpoint novo.

---

## 7. UI/UX

### Popup (action popup)

Abre ao clicar no ícone da extensão na toolbar.

```
┌────────────────────────────────────────┐
│  🔍 Search memory...              [⚙]  │
│                                        │
│  ● nox-mem online (69.2k chunks)       │
│                                        │
│  [Save selection]  [Save page]         │
│                                        │
│  Recent saves:                         │
│  • "React vs Vue comparison..." 2m ago │
│  • "Decision: use SQLite for..." 1h ago│
│                                        │
│  [Pending: 0 chunks]                   │
└────────────────────────────────────────┘
```

- Campo de busca: GET /api/search, mostra 5 resultados com snippet
- Status: verde se API responde, vermelho se offline
- Recent saves: últimos 5 chunks salvos pela extensão (armazenados em `chrome.storage.local`)
- Save buttons: ativos quando há seleção na aba atual

### Context menu (right-click)

```
Save to nox-mem
  ├── Save selection
  └── Save page (URL + title)
```

Aparece SOMENTE em domínios da allowlist.

### Toast de confirmação

Após salvar: toast mínimo na margem inferior direita da página, 2 segundos, sem bloquear conteúdo.

```
┌─────────────────────────────┐
│  ✓ Saved to nox-mem          │
│    chunk_id: 70001           │
└─────────────────────────────┘
```

### Inline answer panel (UC-4)

Painel flutuante ao lado do campo de texto ativo quando resposta disponível:

```
┌──────────────────────────────────────┐
│  nox-mem suggests:                    │
│                                      │
│  "SQLite FTS5 usa BM25 por padrão... │
│  [source: 2026-04-20, chunk #48233]" │
│                                      │
│  [Insert]  [Dismiss]  [Don't suggest]│
└──────────────────────────────────────┘
```

- "Don't suggest" adiciona o domínio à blocklist de inline answers
- Painel não aparece em campos de senha ou campos com `autocomplete=off`
- Desativado por padrão; opt-in nas configurações

### Omnibox (UC-3)

Ao digitar `nx <query>`:

```
Address bar: nx when should i use sqlite vs postgres

Suggestions:
  › "Decision 2025-11-12: escolhemos SQLite..." — chunk #41233
  › "Lesson: SQLite FTS5 and NOT query patterns..." — chunk #39821
  › Search nox-mem for "when should i use sqlite vs postgres"
```

### Configurações (options page)

- API URL + Bearer token (com teste de conexão inline)
- Allowlist de domínios (add/remove/toggle)
- Toggle: Auto-capture classifier
- Toggle: Inline answer
- Omnibox prefix (default "nx")
- Botão: Clear pending queue
- Botão: Export settings (JSON)

---

## 8. Integração com P2 hooks

P2 define uma pipeline de 5 camadas de privacidade para captura automática via OpenClaw hooks. A extensão de browser é uma **fonte de eventos** que pode ser registrada como hook source.

### Extensão como hook source

```
Browser Extension (content-script capture)
         ↓
POST /api/hooks/event
{
  "source": "browser_extension",
  "device_id": "<extension_instance_id>",
  "text": "...",
  "url": "...",
  "title": "...",
  "captured_at": "..."
}
         ↓
P2 pipeline (5 camadas)
         ↓
nox-mem.db
```

Ao usar o endpoint `POST /api/hooks/event` (P2), a extensão ganha automaticamente:
- Layer 3: A1 privacy filter (redundante com o client-side, mas defense-in-depth)
- Layer 4: content classifier server-side (mais sofisticado que o heurístico JS)
- Layer 5: rate-limit + cosine dedup (evita duplicatas se usuário salva mesma página 2x)

### Alternativa: POST /api/ingest direto

Para simplicidade no MVP, a extensão pode usar `POST /api/ingest` diretamente com `provenance='browser_extension'`. Isso evita depender do P2 estar ativo, mas perde as camadas 3-5 do pipeline.

**Recomendação MVP:** usar `/api/ingest` direto com A1 filter client-side. Em v1.1, migrar para `/api/hooks/event` quando P2 estiver estável.

### Telemetria de hook events

Quando `POST /api/hooks/event` é usado, a tabela `agent_events` registra:

```sql
INSERT INTO agent_events (source, action, layer, reason, captured_at)
VALUES ('browser_extension', 'ingest', 'passed', 'all_layers', NOW());
```

Isso aparece no `/api/health` e no P5 viewer (real-time feed) — o usuário vê capturas do browser chegando ao sistema.

---

## 9. Escopo MVP

### v1 — Ship

| Feature | Prioridade | Complexidade |
|---------|-----------|-------------|
| Manifest V3 scaffold (Chrome) | P0 | Baixa |
| Setup: API URL + token + teste de conexão | P0 | Baixa |
| Context menu "Save selection" | P0 | Baixa |
| Allowlist de domínios (configurável) | P0 | Média |
| A1 filter em JS (client-side redaction) | P0 | Média — port do A1 TypeScript |
| Popup: search + status + recent saves | P0 | Média |
| Offline queue (chrome.storage) | P1 | Baixa |
| Omnibox `nx <query>` | P1 | Baixa |
| CORS allowance na API | P0 | Baixa — patch em src/api/server.ts |
| Firefox compatibility | P1 | Baixa — adaptações mínimas |

### Deferido para v2+

| Feature | Razão do defer |
|---------|---------------|
| UC-2 auto-capture classifier | Nice-to-have; complexity/privacy risk |
| UC-4 inline answer | Mais invasivo; aguarda feedback de UC-1/UC-3 |
| UC-5 save page com resumo LLM | Requer chamada Gemini por page save — custo |
| Safari Extension | Xcode + signing process; menor audience técnico |
| Auto-highlight de termos na página | Performance risk em páginas grandes |
| Readwise import | Integração com 3rd party |

### Critérios de DoD para MVP

- [ ] UC-1 (save selection) funcionando no Chrome
- [ ] UC-3 (omnibox nx) funcionando
- [ ] A1 filter em JS redatando CPF/CNPJ/email/phone/tokens em texto selecionado
- [ ] Allowlist configurável — extensão silenciosa fora da allowlist
- [ ] Nenhuma permissão excessiva no manifest.json
- [ ] CORS patch no nox-mem server aceito
- [ ] Popup com status de conectividade e recent saves
- [ ] Offline queue: chunks salvos offline são reenviados quando API volta
- [ ] Testes: 70% coverage em service worker (message handling + fetch + queue)
- [ ] Firefox: funcional (pode ser MV3 com adaptações mínimas)
- [ ] Extension disponível como `.crx` para instalação manual (não Chrome Web Store no MVP)

---

## 10. Roadmap de fases

### P7 — Candidato no Pillar P

**Gate de entrada:** P1+P2 merged e estáveis ≥ 2 semanas (Fev 2026).

| Fase | Período estimado | Entregável |
|------|-----------------|-----------|
| **P7-T1** — CORS patch no servidor | 0.5d | Patch em `src/api/server.ts` + testes |
| **P7-T2** — MV3 scaffold | 1d | `manifest.json` + estrutura de diretórios + build (esbuild) |
| **P7-T3** — A1 filter port (JS) | 1.5d | `src/privacy.js` com 13+ padrões + 20 testes (jest) |
| **P7-T4** — Service worker: save + queue | 2d | Message hub + POST /api/ingest + offline queue |
| **P7-T5** — Context menu + content script | 1.5d | Right-click "Save selection" + toast |
| **P7-T6** — Allowlist de domínios | 1d | Config + content-script gate |
| **P7-T7** — Popup: search + status | 2d | UI popup com search + status + recent |
| **P7-T8** — Omnibox | 1d | `nx <query>` com sugestões |
| **P7-T9** — Settings page | 1d | Options page completo |
| **P7-T10** — Firefox compat | 1d | `browser.*` polyfill + MV3 Firefox adaptações |
| **P7-T11** — QA + empacotamento | 1.5d | Testes E2E + `.crx` build + README |
| **Total estimado** | ~14d de dev | |

### Dependências no path

```
P1 (answer primitive) ──────────────────────────────── P7-T8 (omnibox answer)
P2 (hooks pipeline) ──────────────────────────────────► P7-v1.1 migration
A1 (privacy filter TS) ─────────────────────────────── P7-T3 (port para JS)
CORS patch (P7-T1) ──────────────────────────────────── todo resto
```

### Publicação

- **MVP:** `.crx` para instalação manual (link no README)
- **v1.1:** Chrome Web Store (requer review ~1 semana)
- **v1.1:** Firefox Add-ons (AMO review ~2 semanas)
- **v2:** Edge Add-ons (mesmo código que Chrome)

### Métricas de sucesso pós-launch

- Zero permissões excessivas auditadas (usar [webextension-security-scanner](https://github.com/nicowillis/webextension-security-scanner))
- A1 filter: FP rate ≤ 3% (herda target do A1 servidor)
- Save latency (online): p95 ≤ 300ms
- Offline queue: zero data loss em 1000 queued chunks
- User feedback: "saves corretamente" em domínios da allowlist

---

## Considerações de distribuição

### Chrome Web Store — checklist de privacidade obrigatório

A CWS exige justificativa para cada permissão. Template:

| Permissão | Justificativa CWS |
|-----------|------------------|
| `activeTab` | "Required to read selected text when user activates the extension via right-click or popup. Not used for passive monitoring." |
| `contextMenus` | "Required to add 'Save to nox-mem' option in right-click context menu." |
| `storage` | "Stores user settings (API URL, allowlist) and offline queue locally. No data leaves the device except to user's own nox-mem server." |
| `alarms` | "Periodic connectivity check every 5 minutes to detect when local nox-mem server is available." |
| `omnibox` | "Enables 'nx <query>' search prefix in address bar." |

### Privacy policy statement

"This extension stores data only on the user's device (chrome.storage.local) and sends data only to the user's own nox-mem server (configured by the user). No data is sent to any third-party server. The extension does not use analytics, tracking pixels, or remote logging."

---

## Cross-links

- [P1 answer primitive](./2026-05-17-P1-answer-primitive.md) — UC-3/UC-4 reutilizam `/api/answer`
- [P2 hooks auto-capture](./2026-05-17-P2-hooks-autocapture.md) — arquitetura das 5 camadas e `/api/hooks/event`
- [A1 privacy filter](../staged-A1/) — source dos padrões portados para JS
- [P6 mobile sync](./2026-05-18-P6-mobile-sync.md) — spec irmã (mesma wave K)
- [ROADMAP.md §5 Pillar P](../docs/ROADMAP.md) — contexto de prioridade
- [DECISIONS.md](../docs/DECISIONS.md) — BYO key, zero vendor lock-in

---

*Spec v1.0 — 2026-05-18. Próxima revisão: quando P1+P2 merged + 2 semanas estáveis.*
