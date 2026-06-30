# memoria-nox — Browser Extension (P7 Phase 1)

> *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

Manifest V3 browser extension that lets você capturar trechos da web, buscar
sua memória da barra de endereços (`nx <query>`) e salvar tudo no seu próprio
servidor `nox-mem` local. Tudo passa pelo filtro A1+A1.1 (25 padrões: 13
secrets US + 12 PII BR com check-digit validation) antes de sair do browser.

**Status:** P7 Phase 1 MVP kickoff (UC-1 *Save selection* + UC-3 *Omnibox
search* — escopo central da spec [`specs/2026-05-18-P7-browser-extension.md`](../specs/2026-05-18-P7-browser-extension.md)).

---

## Sumário

- [Por que existe](#por-que-existe)
- [Escopo Phase 1](#escopo-phase-1)
- [O que está deferred](#o-que-está-deferred)
- [Privacidade — princípios não-negociáveis](#privacidade--princípios-não-negociáveis)
- [Instalação (dev mode)](#instalação-dev-mode)
- [Configuração](#configuração)
- [Arquitetura](#arquitetura)
- [Build e empacotamento](#build-e-empacotamento)
- [Testes](#testes)
- [Cross-links](#cross-links)

---

## Por que existe

A spec P7 (Pillar P — Product UX) identificou que a memória só é útil quando
está perto do ponto onde a informação aparece. O browser é onde a maior parte
do consumo de texto acontece. Uma extensão que:

1. **Salva** parágrafos selecionados em 1 clique (right-click + popup).
2. **Busca** a memória inteira pela barra de endereços (`nx <query>`).
3. **Redata** PII e secrets ANTES de qualquer texto sair do dispositivo.

é o que falta entre a captura via OpenClaw hooks (P2) e o uso diário no laptop.

---

## Escopo Phase 1

Cobre **UC-1** (Save selection) e **UC-3** (Omnibox search) — os 2 cenários
mais frequentes da spec. Foundation para Phase 2/3.

| Task | Componente | Status |
|------|-----------|--------|
| T1   | Manifest v3 (Chrome + Firefox variants)            | done |
| T2   | A1 + A1.1 patterns em JS (25 padrões, 4 validators)| done |
| T3   | Service worker: heartbeat, queue, message hub      | done |
| T4   | Content script: toast UI + GET_SELECTION           | done |
| T5   | Popup: quick capture + search + recent saves       | done |
| T6   | Omnibox `nx <query>` → /api/search                 | done |
| T7   | Options page: API URL, token, allowlist, queue ops | done |
| T8   | Build pipeline (esbuild → chrome + firefox + zip)  | done |
| T9   | Tests (60 passing — 48 privacy + 7 SW + 5 omnibox) | done |
| T10  | README + spec cross-link                            | done |

---

## O que está deferred

| Feature | Fase | Motivo do defer |
|---------|------|----------------|
| UC-2 — auto-capture classifier inline                 | Phase 2 | UX precisa de iteração; risco de privacy fora da allowlist |
| UC-4 — inline answer no campo de texto ativo          | Phase 3 | Depende do P1 answer primitive estável + UX research        |
| UC-5 — save page completa com resumo LLM              | Phase 2 | Custo Gemini por save; gating em E12                        |
| Auto-highlight de termos da memória na página         | Phase 3 | Performance em páginas grandes                              |
| Readwise / Kindle import                              | Backlog | 3rd-party integration                                       |
| Chrome Web Store listing                              | Phase 2 | Review process ~1 semana; MVP é `.crx` manual               |
| Safari extension                                      | Backlog | Xcode + signing; audiência menor                            |

Phase 2 + Phase 3 detalhados na spec — §9 (Escopo MVP) e §10 (Roadmap de fases).

---

## Privacidade — princípios não-negociáveis

A extensão toca em dados de qualquer página que você visita. O risco é máximo.
As defesas são em camadas:

### 1. Allowlist-only de domínios

**Default: vazia.** Nada é capturado até você adicionar domínios explicitamente
em *Settings → Domain allowlist*. Mesmo o context menu "Save selection" só
dispara em hostnames listados.

Recomendação:

- ✅ docs técnicas (developer.mozilla.org, kernel.org, postgresql.org)
- ✅ news / blogs técnicos (news.ycombinator.com, lobste.rs)
- ✅ GitHub / GitLab (issues, PRs, gists)
- ❌ banking / fintech / e-mail / saúde / qualquer página com `login`/`auth`/`account`

### 2. A1 + A1.1 filter local (25 padrões)

Antes de qualquer chunk sair do browser, esses padrões rodam:

**13 secrets US** (A1):
PEM private keys, AWS access key + secret, Anthropic / OpenAI / Gemini /
GitHub / Slack / Discord tokens, JWT, Authorization header values, .env-style
assignments (`PASSWORD=`, `*_TOKEN=`, etc.), credit cards com Luhn check.

**12 PII BR** (A1.1):
CPF (com DV), CNPJ (com DV), telefone BR (móvel + fixo, com/sem +55, com/sem
DDD), cartão BR (Luhn), PIX (email / phone / UUID v4 / CPF), CEP, RG, CNH (com
DV próprio), Título de Eleitor (com DV TSE).

Todos os validators de check-digit rodam — placeholders (000.000.000-00,
sequências triviais) são rejeitados. Texto que falha validação **não é
redatado** (evita false positive em version numbers, SKUs, timestamps).

### 3. Sem `<all_urls>` permission

O `manifest.json` lista *zero* permissões wildcard. Content script só carrega
em `127.0.0.1` (lint check garante isso). A permission `activeTab` é o único
gateway pra ler texto da página — ela só fica ativa quando você clica no ícone
ou no menu de contexto.

### 4. Local-only API target

`http://127.0.0.1:18802` por padrão. Pra acesso à VPS, configurar via Tailscale
(`http://100.x.y.z:18802`) — sem expor a API à internet pública. Bearer token
opcional pra localhost, obrigatório pra VPS.

### 5. Sem telemetria

Zero analytics, zero tracking pixels, zero remote logging. Settings + offline
queue ficam em `chrome.storage.local` apenas (nunca `sync`).

---

## Instalação (dev mode)

### Chrome / Edge / Brave

1. `cd staged/P7-browser-extension && npm install && npm run build:chrome`
2. Abrir `chrome://extensions` no browser
3. Ativar *Developer mode* (toggle no canto superior direito)
4. Clicar *Load unpacked* e selecionar `dist/chrome/`
5. O ícone aparece na barra de extensões — clique pra abrir popup

### Firefox

1. `npm run build:firefox`
2. Abrir `about:debugging#/runtime/this-firefox`
3. Clicar *Load Temporary Add-on…*
4. Selecionar `dist/firefox/manifest.json`

⚠️ Firefox MV3 ainda não suporta omnibox 100% — o keyword `nx` pode não funcionar
até que a Mozilla finalize o suporte. Use o popup pra search nesse caso.

### Primeiro setup (depois de carregar)

1. Clicar no ícone → *Settings* (engrenagem)
2. *Connection*: confirmar API URL (`http://127.0.0.1:18802`) e testar
3. *Domain allowlist*: adicionar pelo menos um domínio onde quer salvar
   (ex: `github.com`)
4. Voltar pra qualquer página em allowlist, selecionar texto, right-click →
   *Save selection to nox-mem*

---

## Configuração

Todas as settings ficam em `chrome.storage.local`. Schema (defaults):

```jsonc
{
  "api_url": "http://127.0.0.1:18802",
  "auth_token": "",            // criptografado com AES-GCM via WebCrypto
  "allowlist": [],             // hostnames exatos (sem wildcards)
  "auto_capture": false,       // UC-2 (deferred Phase 2)
  "inline_answer": false,      // UC-4 (deferred Phase 3)
  "omnibox_prefix": "nx"       // prefixo da omnibox
}
```

O Bearer token é envolvido em AES-GCM antes de gravar (chave também em
`chrome.storage.local`, então é só barreira contra inspeção casual — proteção
real seria OS keychain, fora de escopo no MVP).

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────┐
│  Browser                                                  │
│                                                            │
│  ┌─────────────┐    ┌─────────────────────────────────┐    │
│  │ Service     │    │  Content Script (allowlist-only)│    │
│  │ Worker (SW) │    │                                 │    │
│  │             │◄───│  • toast UI                     │    │
│  │ • messages  │    │  • GET_SELECTION resolver       │    │
│  │ • heartbeat │    └─────────────────────────────────┘    │
│  │ • queue     │                                            │
│  │ • omnibox   │    ┌─────────────┐    ┌──────────────┐    │
│  │ • ctxMenu   │◄───│  Popup      │    │  Options     │    │
│  └─────┬───────┘    │  (quick     │    │  (settings,  │    │
│        │            │  capture,   │    │   allowlist) │    │
│        │            │  search)    │    │              │    │
│        │            └─────────────┘    └──────────────┘    │
└────────┼───────────────────────────────────────────────────┘
         │  fetch
         ▼
   nox-mem HTTP API @ 127.0.0.1:18802
   (POST /api/ingest, GET /api/search, GET /api/health)
```

### Componentes

| Arquivo | Papel |
|---------|-------|
| `src/background.js`        | Service worker. Único ponto de I/O com a API. |
| `src/content/content.js`   | Toast + GET_SELECTION (allowlist-only). |
| `src/popup/popup.{html,css,js}`     | Quick capture + search + recent. |
| `src/options/options.{html,css,js}` | Settings completos. |
| `src/lib/privacy/patterns.js`       | Catálogo A1+A1.1 (25 padrões). |
| `src/lib/privacy/validators.js`     | CPF/CNPJ/Luhn/CEP/CNH/Título. |
| `src/lib/privacy/redact.js`         | Pipeline single-pass + scanRedactions(). |
| `src/omnibox.js`            | Helpers de formatação de sugestões. |
| `manifest.json`             | Chrome MV3. |
| `manifest.firefox.json`     | Firefox MV3 (`browser_specific_settings`). |

### MV3 lifecycle (importante)

Service Worker é terminado após ~30s idle. **Nunca** guarde state em variáveis
de módulo — sempre leia de `chrome.storage.local`. Heartbeat é via
`chrome.alarms` (periodicidade mínima permitida: 30s).

### Fluxo de save (UC-1)

```
1. user right-click "Save selection to nox-mem"
2. background.contextMenus.onClicked
3.   isAllowed(tab.url, settings.allowlist) → if not, drop silently
4.   redactAll(info.selectionText)        ← A1 + A1.1 client-side
5.   POST /api/ingest {text, source_url, ..., redaction: {count, kinds}}
6.   if fail → enfileira em pending_chunks (FIFO, max 100)
7. tabs.sendMessage({type: TOAST, message: "Saved"}) → content.js renderiza toast
```

### Fluxo de omnibox (UC-3)

```
1. user digita "nx sqlite vs postgres" na barra
2. omnibox.onInputChanged(text)
3. GET /api/search?q=...&limit=5 → results
4. format suggestions (chunk title + meta)
5. user seleciona → omnibox.onInputEntered → abre URL ou search page
```

---

## Build e empacotamento

```bash
npm install                   # esbuild only (zero runtime deps)
npm run build                 # → dist/chrome/ + dist/firefox/
npm run build:chrome          # apenas Chrome
npm run build:firefox         # apenas Firefox
npm run watch                 # esbuild watch mode
npm run package               # build + zip → dist/chrome.zip + dist/firefox.zip
npm run lint:manifest         # CRITICAL — confirma "no <all_urls>" etc.
npm run clean                 # rm -rf dist/
```

### Output layout

```
dist/
├── chrome/
│   ├── manifest.json
│   ├── src/
│   │   ├── background.js          (esbuild-bundled ESM)
│   │   ├── popup/popup.{html,css,js}
│   │   ├── options/options.{html,css,js}
│   │   ├── content/content.js
│   │   └── icons/*.svg
│   └── ...
├── firefox/                       (same structure, manifest variant)
├── chrome.zip                     (only if --package)
└── firefox.zip
```

---

## Testes

```bash
npm test                      # roda todos (60 testes)
npm run test:patterns         # só os 48 testes de privacy
npm run lint:manifest         # 0 errors esperado
```

Cobertura atual:

| Suíte                                       | Testes | Foco |
|---------------------------------------------|--------|------|
| `extension/src/lib/privacy/__tests__/validators.test.mjs` | 20     | CPF/CNPJ/Luhn/CEP/CNH/Título |
| `extension/src/lib/privacy/__tests__/redact.test.mjs`     | 28     | Pipeline + 25 patterns + edge |
| `extension/__tests__/background-integration.test.mjs`     | 7      | isAllowed + escapeXml |
| `extension/__tests__/omnibox.test.mjs`                    | 5      | formatOmniboxSuggestion |
| **Total**                                                  | **60** | — |

E2E real (carregar a extensão no Chrome, salvar selection, validar chunk no
nox-mem) é validado manualmente até v0.2 (CDP/Puppeteer harness é Phase 2).

---

## Roadmap Phase 1 → Phase 2/3

| Fase | O que entra | Pré-requisito |
|------|------------|--------------|
| **P7 Phase 1** (este) | UC-1 + UC-3 + scaffold completo                    | P1+P2 stable, CORS patch na API |
| **P7 Phase 2**        | UC-2 auto-capture; Chrome Web Store; E2E harness   | Phase 1 em uso ≥ 2 semanas |
| **P7 Phase 3**        | UC-4 inline answer; auto-highlight; Readwise import| P1 answer primitive estável em prod |

Spec completo: [`specs/2026-05-18-P7-browser-extension.md`](../specs/2026-05-18-P7-browser-extension.md).

---

## Cross-links

- **Spec P7:** `specs/2026-05-18-P7-browser-extension.md` (este PR é a Phase 1 do roadmap §10).
- **A1 privacy filter (TS source):** `staged/privacy/edits/privacy/patterns.ts` — 13 US patterns que portamos.
- **A1.1 BR PII:** `staged/A1.1/edits/src/lib/privacy-br/patterns.ts` — 12 BR patterns + validators.
- **P2 hooks pipeline:** `staged/P2/edits/src/lib/hooks/` — futuro target (`/api/hooks/event`) em v0.2.
- **P1 answer primitive:** `staged/P1/` — futuro target (`/api/answer`) em Phase 3 (UC-4).
- **CORS patch necessário no servidor:** `src/api/server.ts` — adicionar `^chrome-extension://` ao `ALLOWED_ORIGINS` (T1 da spec roadmap, pré-req pra esta extensão funcionar contra qualquer build > localhost-IP).

---

## Filosofia operacional

- **Defense in depth:** o A1 server-side roda também (camada 3 do P2). Se a
  extensão fica desatualizada, o server pega o que ela perdeu.
- **Allowlist explícita:** sem opt-out gigante de domínios "perigosos". Você
  adiciona um a um o que confia.
- **Local first:** padrão é `127.0.0.1`. Tailscale pra remote é opt-in, não
  padrão.
- **No vendor lock-in:** todo dado capturado vai pro *seu* `nox-mem`. Sem
  cloud, sem telemetria, sem 3rd-party SDK no bundle.

---

*v0.1.0 — Phase 1 MVP — 2026-05-18.*
