# Q4 COMPARISON — competitor versions + install commands

> Resolved 2026-05-21 overnight. Toto runs Saturday morning. Re-verify each
> pin before install — projects iterate weekly.

Per spec `specs/2026-05-23-Q4-comparison-execution-plan.md` §1, we benchmark
the **default configuration** of each system (no tuning to win). Pinned
versions match the latest stable release available at overnight resolution
time.

---

## 1. nox-mem (self / reference)

| Field | Value |
|---|---|
| Repo | https://github.com/totobusnello/memoria-nox |
| Version pin | current `main` SHA (resolve at run time via `git rev-parse HEAD`) |
| Install | `npm install && npm run build` |
| API surface | HTTP `/api/search` on port 18802 |
| API keys | `GEMINI_API_KEY` |
| Daemon | `node dist/index.js api` (or via `docker compose --profile noxmem`) |

Adapter: `adapters/nox_mem.py` — uses `requests.get(/api/search)`.

---

## 2. Mem0 (mem0ai)

| Field | Value |
|---|---|
| Repo | https://github.com/mem0ai/mem0 |
| License | Apache-2.0 |
| Stars (2026-05-21) | 53k+ |
| Install | `pip install 'mem0ai==0.1.114'` |
| Version pin | `0.1.114` (latest stable on PyPI as of 2026-05-21) |
| Defaults | Chroma vector store (in-process) + OpenAI embeddings |
| API keys | `OPENAI_API_KEY` (mandatory in default config) |
| Optional extras | `pip install 'mem0ai[graph]'` for the graph layer (Neo4j) |

**Pinning rationale:** 0.1.x is stable; 0.2.x branch is unreleased as of
2026-05-21. Default config doesn't need a daemon (Chroma runs in-process),
so the only setup cost is the OpenAI key.

Adapter: `adapters/mem0.py` — `from mem0 import Memory; Memory().search(...)`.

---

## 3. Zep (getzep)

| Field | Value |
|---|---|
| Repo | https://github.com/getzep/zep |
| License | Apache-2.0 |
| Stars (2026-05-21) | 1.8k+ |
| Install (server) | Docker compose — `docker compose -f compose/docker-compose.yml up -d zep postgres` |
| Install (client) | `pip install 'zep-python==1.5.0'` + **`pip install --upgrade httpcore httpx`** (ver nota) |
| Version pin (server) | `ghcr.io/getzep/zep:0.27.2` |
| Version pin (client) | **`zep-python==1.5.0`** — o `2.4.0` que estava aqui era deriva; ver nota |
| Defaults | Postgres backend. Há caminho de embedding **local** (`Service: local` + container `zep-nlp`), que **este stack removeu por escolha** — ver errata. |
| API keys | Uma chave **paga de LLM**, de **dois** fornecedores possíveis (OpenAI ou Anthropic), obrigatória no arranque — ver errata. |
| Daemon | `zep` + `postgres` containers (see `compose/docker-compose.yml`) |

**Pinning rationale:** Zep 0.27.x is the latest OSS line; 0.28 is roadmapped
but not released. Self-hosted OSS is the fair comparison surface (Cloud is
a paid tier).

Adapter: `adapters/zep.py` — usa `ZepClient.memory.{add_session,add_memory,search_memory}`.

### Pin do cliente — corrigido 2026-09-10 por EXERCÍCIO, não por leitura

Este arquivo dizia `zep-python==2.4.0`. **Errado para o servidor OSS 0.27.x.** O `2.x`
aponta para o **Zep Cloud** e tem outra superfície; o adapter usa a API `1.x`
(`ZepClient(base_url, api_key)`, `Memory`/`Message`/`Session`/`MemorySearchPayload`), que
é a do servidor auto-hospedado.

Confirmado **rodando** contra o `q4-zep` vivo, não por conferir assinaturas:

```
add_session   -> ok
add_memory    -> ok
search_memory -> ok | hits=2 | dist=0,9123
```

⚠️ **Duas armadilhas de instalação, medidas em Python 3.14:**

1. O `httpcore` que o `zep-python==1.5.0` arrasta **não importa** em 3.14 —
   `AttributeError: 'typing.Union' object has no attribute '__module__'` dentro do
   próprio `httpcore/__init__.py`. Resolve com `pip install --upgrade httpcore httpx`.
2. Isso **viola o pin declarado** (`httpx<0.25.0,>=0.24.0`) e o pip avisa. Ainda assim
   os cinco símbolos importam **e as três chamadas funcionam** contra o servidor. O pin
   declarado é mais estreito que o necessário — mas isto é fato medido nesta
   combinação, não garantia geral: quem reproduzir deve repetir o smoke test.

### ⚠️ A suíte `test/test_zep_ingest.py` não exercita os imports reais (2026-09-10)

11 dos 23 casos falham com `ModuleNotFoundError: No module named 'zep_python'`, e caem
**dentro do adapter** (linhas 265, 398, 466) — os `from zep_python import ...` que vivem
dentro de `ingest_corpus()` e `search()`. A suíte injeta um falso em `sys.modules` que
não alcança esses caminhos tardios.

⇒ **O verde/vermelho desta suíte diz pouco sobre o adapter.** Mesma classe do que foi
corrigido em `test_evermind_ingest.py` no mesmo dia: um teste que faz mock do que não é
o caminho real passa sem verificar nada. Medido que as 11 falhas são **pré-existentes**
(idênticas com e sem a correção de versão abaixo), logo não são regressão.

### ⚠️ Errata 2026-09-10 — medido, e o bloqueio não é o que estava escrito

Escrevi aqui, de manhã, que **duas** linhas do README eram falsas. Depois de a sessão
par cruzar com o fonte `v0.27.2`, o saldo é outro: **uma das minhas "correções" era ela
própria falsa**, e a outra estava certa mas imprecisa. Fica o que sobrevive à medição.

**(1) 🔴 RETRATADO — HÁ caminho de embedding local, e a minha inferência foi inválida.**
Escrevi que não havia, porque `EmbeddingsConfig` não tem campo de modelo nem de
endpoint. **A inferência é inválida:** o endpoint do caminho local vive em **outro
bloco** de config (`NLP.ServerURL`), e o schema tem esse bloco. `embeddings.go@v0.27.2`:

```go
if model.Service == "local" { return embedTextsLocal(...) }
return appState.LLMClient.EmbedTexts(ctx, text)
```

`embedTextsLocal` faz `POST {NLP.ServerURL}/embeddings/{message,document}` — o container
`zep-nlp`, **sem chave nenhuma**. Confirmado no artefato: o binário contém
`embeddings/document`, `embeddings/message` e o literal
`"not implemented. use a local embedding model"` (a mensagem do `EmbedTexts` do
Anthropic, que aponta o caminho local em texto).

⇒ **Ausência do campo naquela struct não é ausência do recurso no artefato** — é
[[feedback_absence_at_one_json_path_is_not_absence_in_the_artifact]] com uma struct no
lugar do caminho de JSON. Cometi a minha própria lição, dois dias depois de a escrever.

🔑 **O que é verdade sobre ESTE stack:** o nosso `docker-compose.yml` **removeu** o
servidor NLP de propósito — comentário na linha 25: *"ZEP_NLP_SERVER_URL removed — no NLP
server in this stack"*, e não há bloco `NLP` no `zep-config.yaml`. Logo o embedding por
OpenAI a 1536d é **decisão nossa de comparabilidade**, não restrição do Zep. Isso muda a
tabela de autonomia do paper na direção **favorável ao Zep**: ele não exige provedor pago
para embedar.

**(2) A chave é obrigatória no arranque — mas não é "chave OpenAI".**
`NewLLMClient` liga em `cfg.LLM.Service`, e `case "anthropic"` é de primeira classe →
`NewAnthropicLLM` → `log.Fatal(AnthropicAPIKeyNotSetError)`. O `log.Fatal` do OpenAI só é
alcançado nos casos `"openai"` e `""` (retrocompat). ⇒ A afirmação defensável é **uma
chave paga de LLM, de dois fornecedores possíveis**.

Sem a chave do serviço escolhido o binário aborta no arranque; com uma inválida, arranca
`healthy` e **falha em segundo plano**:

```
level=error msg="Task HandleError error: MessageEmbedderTask embed messages failed:
llm error: error while creating embedding (original error: API returned unexpected
status code: 401: Incorrect API key provided: ...)"  max_retries=5
```

⚠️ **`healthy` não é evidência de que o Zep embeda.** O healthcheck prova que a
porta atende; o embedder é uma tarefa assíncrona que estoura depois, com 5
retentativas, e a busca então devolve 500. As duas coisas são independentes.

### 🔴 RETRATAÇÃO no mesmo dia — a culpa era da MINHA grafia, e o schema publicado mente

Escrevi aqui, horas antes, que o `LLM.OpenAIEndpoint` **não alcança o caminho de
embedding**. **Falso.** A sessão par cruzou com o fonte `v0.27.2` e mostrou o
mecanismo no código (`llm_openai.go`: `case cfg.LLM.OpenAIEndpoint != "" →
openai.WithBaseURL(...)`, no **mesmo** cliente que `EmbedTexts` usa). Remedi e ela
está certa.

**O que a minha medição realmente mostrou.** Dump da config efetiva, com a chave
substituída por sentinela:

```
"AzureOpenAIEndpoint": "",
"OpenAIEndpoint": "",            ← VAZIO, com o yaml declarando o endpoint
```

O yaml **é** lido — provei por um discriminador independente: troquei
`Server.Port` para 8123 e o processo passou a escutar em 8123
(`msg="Listening on: 0.0.0.0:8123"`). Logo o arquivo chega ao binário e ainda
assim aquele campo ficava vazio.

**A causa:** a grafia da chave. Com `openai_endpoint:` (snake_case) o dump passa a
mostrar `"OpenAIEndpoint": "http://…"`. Com `OpenAIEndpoint:` — **a grafia que o
próprio `zep json-schema` publica** — o viper ignora, sem aviso.

> ⚠️ **`zep json-schema` publica chaves em CamelCase que o loader NÃO aceita.** O
> schema é gerado das tags JSON da struct; o carregamento usa mapstructure em
> snake_case. Um arquivo de config escrito **a partir do schema publicado** é
> silenciosamente ignorado nesses campos, e o efeito é indistinguível de "o
> recurso não existe".

**Erro de método, e é o que importa levar:** o meu controle positivo provava que o
**coletor** recebia e gravava — não que a **config** tinha chegado ao campo. Três
formas de sufixo (`/v1`, sem sufixo, `/v1/`) não discriminam nada se a chave nunca
liga: as três falham igual. Sem uma perna que prove que o valor **tomou**, "não
suportado" e "a minha config não chegou" têm saída idêntica.

**Estado da pergunta:** se o Zep embeda por endpoint OpenAI-compat de terceiro
(Gemini) **fica NÃO TESTADO** — e saiu do caminho crítico, porque há chave OpenAI
válida (abaixo). Não afirmar nem negar isso no manuscrito.

### ✅ 2026-09-10 — o Zep RODA, e a busca devolve distância real

**Preflight pago de 5 documentos** (`scripts/zep-preflight.py`), que responde o que
assinatura não responde:

| pergunta | resultado |
|---|---|
| o `gold_id` faz round-trip pelo `metadata` da mensagem? | **3/3** — e o documento esperado veio em **1º lugar** nas três consultas |
| a distância é real (não zero, não vazia)? | sim — 0,9349 / 0,8602 / … |
| quantas sessões o agrupamento cria? | **2** para 2 `conv_id` distintos |
| mensagens gravadas | 5 de 5 |

⚠️ O embedding do Zep é **assíncrono**: o preflight espera 15 s antes de buscar. Sem a
espera, "0 hits" mede a espera e não a busca. E a busca do adapter faz **fan-out por
sessão** — o custo e a latência da fase de busca crescem com o número de `conv_id`, não
com o de documentos.

⇒ `EXIT=0`: **o corpus inteiro pode correr.**

Com uma chave OpenAI válida instalada (`/root/q4-zep/.env`, mode 600), medido na
kvm8 **sem** nenhuma alteração ao `zep-config.yaml` original:

```
POST /api/v1/sessions/<s>/memory  -> 200
erros de embedding no minuto seguinte -> 0
POST /api/v1/sessions/<s>/search  -> 200 | 2 hits | dist=0,9172
```

`text-embedding-3-small` confirmado a **1536d** direto na API, o que casa com o
`Dimensions: 1536` do config. ⇒ **O Zep deixa de ser competidor não-executado.**

⚠️ Consequência para o manuscrito: as frases que atribuem ao Zep *"never ran"* e
*"requires a privileged Docker host"* são **duplamente** falsas — ele rodou em
2026-05-25 (artefato em `output/zep.json`) e corre hoje num host não privilegiado.


---

## 4. Letta (ex-MemGPT, letta-ai)

| Field | Value |
|---|---|
| Repo | https://github.com/letta-ai/letta |
| License | Apache-2.0 |
| Stars (2026-05-21) | 14k+ |
| Install (server) | `pip install 'letta==0.6.6'` then `letta server` OR `docker compose --profile letta up -d` |
| Install (client) | `pip install 'letta-client==0.1.46'` |
| Version pin (server) | `letta==0.6.6` |
| Defaults | SQLite backend; OpenAI embeddings (configurable) |
| API keys | `OPENAI_API_KEY` (mandatory in default config) |
| Daemon | `letta server` on :8283 OR `q4-letta` container |
| Notes | Letta is a full agent runtime; we bench `archival_memory_search` (recall-only) for fair retrieval comparison. |

**Pinning rationale:** 0.6.x is current stable. The bench-only entrypoint
`archival_memory_search` has been stable since 0.5.x.

Adapter: `adapters/letta.py` — uses `letta_client.Letta`.

---

## 5. agentmemory (rohitg00)

| Field | Value |
|---|---|
| Repo | https://github.com/rohitg00/agentmemory |
| License | Apache-2.0 (CLI + npm package); iii-engine = **ELv2** (self-host OK; SaaS-compete prohibited) |
| Stars (2026-05-23 probe) | 16,726 |
| Install | `npm install -g '@agentmemory/agentmemory'` |
| Version pin | **v0.9.21** (installed + verified 2026-05-23) |
| Daemon | iii-engine **auto-installs** from npm on first run (no paid license required for self-host) |
| API keys | None required for local run |
| REST API | `POST http://localhost:3111/agentmemory/remember` + `POST /agentmemory/search` |

**Probe results (2026-05-23):**

- `npm install -g @agentmemory/agentmemory` — SUCCEEDED, v0.9.21, ~8s, 242 packages
- iii-engine: auto-downloaded + started (v0.11.2 pinned in npm bundle). **Not paid-only.**
  License is ELv2 (not MIT) but self-host for benchmark is permitted; SaaS-compete is not.
- REST API liveness: `GET /agentmemory/livez` → `{"service":"agentmemory","status":"ok"}` PASS
- Smoke ingest (5 chunks via `POST /agentmemory/remember`): PASS, all returned `"success":true`
- Smoke search (`POST /agentmemory/search`, `query="hybrid search BM25"`): PASS, 5 results, scores ~0.68
- **Adapter mismatch (BLOCKER fixed in adapter):** CLI has no `add`/`recall` subcommands — it is
  server-only (REST on :3111). Adapter rewritten to use REST (`POST /remember`, `POST /search`).
- **ID round-trip gap:** `/agentmemory/remember` does NOT accept custom `id`; issues system-generated
  `mem_xxx` IDs. Nox-mem chunk id must be embedded in `content` and extracted at search time.
  Adapter updated to embed `[nox_id:<id>]` prefix and parse it back from returned content.

**Pinning rationale:** v0.9.21 confirmed installed. Record `agentmemory --version` on VPS after
daemon is running (the binary outputs version only after iii-engine connects).

**⚠️ Start sequence on VPS:**
```bash
agentmemory &   # starts daemon + auto-installs iii-engine if absent; binds :3111
sleep 5
curl http://localhost:3111/agentmemory/livez   # must return {"status":"ok"}
```

Adapter: `adapters/agentmemory.py` — REST `POST /agentmemory/remember` + `POST /agentmemory/search`.

---

## 6. EverMind-AI (EverOS) — deixou de ser GAP em 2026-09-10

> 🟢 **ESTADO 2026-09-10.** O cabeçalho desta seção dizia **"GAP"** até hoje e a
> alegação venceu: a ingestão fechou (`fecho ok=6826 falhas=4`, 4 h 11 min) e
> **6.822** documentos estão no índice sqlite (`knowledge_documents`), com
> `missing ∩ gold = ∅`. A busca das 2.482 queries corre agora. O texto abaixo é
> **histórico** — fica porque descreve como o GAP foi diagnosticado e por que a
> razão de 2026-05-23 estava errada, e apagá-lo apagaria a prova do que esteve
> publicado. Números vivos: `RESULTADOS-Q4-2026-09-10.md`.

### 6.0 Histórico — como era, e a razão errada de 2026-05-23

⚠️ **ERRATA 2026-09-10.** Esta seção dizia que o repo **não existia** (404 em 2026-05-23,
cinco sondas). **Ele existe, e existia então.** As cinco sondas erraram do mesmo jeito:
trocaram **org** e **repo**.

| sonda de 2026-05-23 | resultado |
|---|---|
| `EverOS-AI/EverMind-AI` | 404 |
| `EverMind-AI/EverMind-AI` | 404 |
| `EverOS/EverMind` | 404 |
| **`EverMind-AI/EverOS`** ← nunca tentada | **HTTP 200** |

Medido 2026-09-10:

| Field | Value |
|---|---|
| Repo | https://github.com/EverMind-AI/EverOS — **12.856 ★**, Apache-2.0, push 2026-09-09 |
| Org | `EverMind-AI` — HTTP 200, **16 repos públicos** (inclui `EverMemBench`, que o paper cita) |
| Install | `pip install everos` → **v1.3.1** (PyPI HTTP 200); importa sem credencial |
| Forma | README **afirma** *"No API key or server setup required"* — ⚠️ **falso para a busca**: `service/search.py` instancia cliente de LLM, e `create_document()` roda extração de LLM por documento. Instala e importa sem credencial; **correr** exige provedor de LLM + embedding (ambos configuráveis) |
| Embedding | agnóstico por protocolo OpenAI: nomeia **Ollama** e **vLLM** locais; DeepInfra é **um default** (`settings.py:403`), não requisito |
| `docker-compose.yml` na raiz | **404** — o stack de 5 serviços que o paper conta em `[^everos-stack]` não está mais lá |

🔑 **A lição do método, e é a que importa mais que o fato:** a conclusão *"não existe"*
saiu de **enumerar nomes** em vez de **listar o espaço**. `GET /orgs/EverMind-AI/repos`
responde de uma vez o que cinco palpites não responderam — e uma varredura que conclui
ausência precisa de controle positivo, que aqui seria justamente listar a org.

**Status atual: GAP aberto (não rodado), VIÁVEL, adapter PRONTO.**

`adapters/evermind.py` reescrito 2026-09-10 contra a API medida da v1.3.1 — a versão
anterior falava com um CLI `evermind retrieve` e um `EVERMIND_PYTHON_MODULE` que **não
existem** (as CLI commands são `init · demo · server · cascade · config`). Superfície
escolhida: `service.knowledge`, porque `create_document(doc_id=…)` e
`SearchHit.document.doc_id` fazem o id do chunk voltar — sem isso o nDCG por
`gold_chunk_ids` é indefinido. A superfície de **memória** (`service.memorize` /
`service.search`) devolve episódios derivados, sem essa proveniência, e por isso não é
comparável. Suíte: `test/test_evermind_ingest.py`, 16 casos, 7 mutações mordem.

⚠️ **O que falta é decisão, não código:** a ingestão custa **6.830** extrações de LLM
(~3,54 M tokens de entrada; o LongMemEval é 14% dos documentos e ~95% dos caracteres) e
está barrada por `EVEROS_ALLOW_PAID_INGEST=1`. Ver
`paper/publication/spike-item6-2026-09-10.md` (adenda de 10-09).

## Quick reference

```bash
# Python-side (run once)
pip install -r requirements.txt

# Node-side (agentmemory — verified working 2026-05-23)
npm install -g @agentmemory/agentmemory   # installs v0.9.21 + iii-engine auto-download
agentmemory &                              # start daemon; binds REST on :3111
sleep 5 && curl http://localhost:3111/agentmemory/livez   # verify {"status":"ok"}

# Docker-side (Zep + optional Letta + optional noxmem)
docker compose -f compose/docker-compose.yml up -d zep postgres
# add --profile letta or --profile noxmem if desired

# EverOS (registry key `evermind`) — adapter PRONTO; ingestao EXECUTADA em 2026-09-10
# sob ordem explicita do Toto. O gate abaixo continua a valer para QUALQUER nova corrida:
pip install everos==1.3.1
export EVEROS_LLM__API_KEY=... EVEROS_LLM__BASE_URL=...          # OpenAI-compativel (Gemini serve)
export EVEROS_EMBEDDING__API_KEY=... EVEROS_EMBEDDING__BASE_URL=...
python adapters/evermind.py                                       # validate(), zero rede
# Para RODAR a ingestao (6.830 docs x 1 extracao de LLM), so com ordem explicita:
# export EVEROS_ALLOW_PAID_INGEST=1

# Set env (paste into shell or .env.q4):
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...
# Optional:
# export ZEP_USE_CLOUD=1 ZEP_API_KEY=...
# export NOX_API_BASE=http://vps.host:18802
```

---

## Blockers resolved / needing Toto's decision

- [x] **agentmemory iii-engine daemon** — RESOLVED 2026-05-23. iii-engine auto-installs
      from npm bundle (ELv2, not paid). REST API verified working. Adapter updated to REST.
- [ ] **EverOS retrieve API** — ⚠️ **RETRATADO 2026-09-10.** Este item esteve marcado
      `[x] RESOLVED` por 3,5 meses afirmando que o repo *"does not exist"* e que o sistema
      seria `SKIPPED`. **O repo existe** (`EverMind-AI/EverOS`, 12.856 ★) e existia então;
      as cinco sondas trocaram org e repo (§6). Uma caixa marcada errada é pior que uma
      caixa vazia: fecha a pergunta. Estado real: adapter pronto contra a v1.3.1, ingestão
      **paga** (6.830 extrações de LLM) e barrada por `EVEROS_ALLOW_PAID_INGEST=1`.
      Falta **ordem do Toto para gastar**, não trabalho.
      🟢 **FECHADO 2026-09-10.** A ordem veio, a ingestão correu (`fecho ok=6826
      falhas=4`, 4 h 11 min) e 6.822 documentos estão no índice. A caixa fica `[ ]`
      até a busca fechar com nDCG no §7 — marcar agora repetiria o erro que este
      item denuncia, que é caixa marcada antes do estado.
- [ ] **OpenAI quota** — Mem0 + Letta both default to OpenAI embeddings.
      Estimate: ~600 queries × 2 datasets × 2 systems = 2,400 embedding
      calls. Budget < $1 at current ada pricing, but confirm before run.
      ⚠️ **2026-09-10 — este item não cobre o Zep, e o Zep também embeda pela
      OpenAI.** O `zep-config.yaml` liga `Extractors.Messages.Embeddings` com
      `Service: openai` (`text-embedding-3-small`, 1536d). A cota superior da
      corrida de hoje está em `RESULTADOS-Q4-2026-09-10.md` §5.4, com a natureza de
      cada linha declarada (medida vs cota) — o medidor autoritativo
      (`/v1/organization/usage/embeddings`) recusa: a chave deste projeto não tem o
      escopo `api.usage.read`.
- [x] **Zep self-host RAM** — ✅ **MEDIDO 2026-09-10 sob carga de busca**, que é a
      única janela em que isto se mede. A estimativa estava **8× alta** e a premissa
      estava no host errado:

      | | escrito aqui | medido |
      |---|---|---|
      | `q4-zep` + `q4-postgres` | "~2 GB resident" | **364 MiB** (100,9 + 262,9) |
      | host | "VPS has 16 GB" | **32 GB — é o kvm8, não a VPS de produção** |
      | maior consumidor de RAM | (implícito: o Zep) | **o nosso harness**, 2.249 MB |

      ⇒ A preocupação inverte-se: quem competia por memória eram os nossos próprios
      processos de busca, não o stack do Zep. E o item foi escrito sobre a VPS de
      produção, que é **proibida** de hospedar benchmark até 2026-09-21 (ensaio do
      Paper 2 em curso) — logo a premissa dele nunca descreveu onde a corrida ia
      acontecer.
