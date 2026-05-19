# Nox Neural Memory — Visão

> Documento de visão — **v15 (2026-05-18, pós-D40 + D41)**
> Tagline: *"Pain-weighted hybrid memory with shadow discipline — yours by design."*
> Substitui v14 (2026-04-25). v14 arquivada em `docs/_archive/VISION-v14-pre-Q-A-P-2026-05-18.md`.
>
> **Canônicos vivos:** `docs/HANDOFF.md` (estado), `docs/ROADMAP.md` (sprints Q/A/P), `docs/DECISIONS.md` (D40 + D41 + raciocínio).
> Este doc é **vision** — sprint-agnóstico, sobrevive a re-priorizações, fala da forma final do produto e do que recusamos virar pelo caminho.

---

## A missão

Tudo que você produz — contratos, decks, planilhas, contratos, transcrições de reunião, conversas com agentes — vira conhecimento consultável em segundos, citável com fonte, **sem que isso saia da sua máquina**. Esse é o ponto inteiro. Outras pessoas estão construindo memória pra IA. Quase ninguém está construindo memória **sua** pra IA — onde o arquivo SQLite é seu, o controle é seu, e o vendor é descartável.

Nox-mem nasceu como segundo cérebro pessoal do Toto rodando numa VPS Hostinger, virou plataforma capaz de servir 6 agentes simultaneamente sobre a mesma indexação, e agora aponta pra uma terceira fase: ser a **camada de memória default** que desenvolvedores escolhem quando montam sistemas com Claude Code, Codex, Cursor ou qualquer outro agente — porque a alternativa é amarrar dados em SaaS de terceiros (memanto/Moorcheh) ou em runtimes proprietários (agentmemory/iii-engine). Nenhum dos dois caminhos respeita a premissa "o dado é seu".

A era dos agentes de IA é a era em que memória vira commodity. O que diferencia não é mais "tem memória", é **a qualidade do recall + a autonomia sobre os dados + a UX que aparece no fluxo onde você já trabalha**. Esse triângulo é o que Nox persegue.

---

## O moat que estamos construindo

Quatro frentes compõem o moat — cada uma é defensável sozinha, e juntas formam um produto que nenhum competidor copia rápido.

**Data autonomy.** O arquivo `nox-mem.db` é seu. Roda na VPS, no Mac, num server alugado, num laptop sem rede — escolha sua. Nenhum daemon proprietário precisa estar vivo pra você ler o próprio dado: `sqlite3 nox-mem.db "SELECT * FROM chunks WHERE ..."` funciona pra sempre. Export plaintext e encrypted-by-default (AES-256-GCM + scrypt KDF, opt-out via `--unencrypted`) garantem portabilidade real. Esse é o terreno onde nem memanto (SaaS Moorcheh) nem agentmemory (iii-engine runtime lock-in) nem gbrain (focused on personal brain, não autonomy guarantee) competem.

**Qualidade-first.** Embeddings Gemini 3072d (não 768 baratos, não 1536 default), hybrid retrieval (FTS5 + dense + RRF language-aware), salience pain-weighted (`recency × pain × importance`), KG com edge typing tipado, compiled-truth + timeline pra entities (temporalidade epistêmica — o sistema sabe que "X era verdade ontem mas hoje mudou"). Cada decisão de ranking passa por shadow-mode antes de virar produto. Não nascemos pra disputar "feature breadth"; nascemos pra disputar "numbers that lead" em benchmarks honestos.

**Shadow discipline.** Mudança que afeta retrieval ou ranking nunca vai pra produção sem ≥1 semana de baseline em shadow-mode, comparando A/B contra a produção atual via `/api/health`. Já evitou regressões silenciosas mais de uma vez (salience formula, section_boost, language-aware RRF, FTS5 tuning). Disciplina não é overhead — é o que permite mudar rápido com confiança. É **paciência arquitetural como vantagem competitiva**: enquanto competidor que faz `if (new_thing) better` ship-and-pray, a gente mede e só toca o ranking quando o número justifica.

**Transparent benchmarks.** Quando ganharmos um benchmark público (LoCoMo, LongMemEval, latência, e o nosso `COMPARISON.md` head-to-head com memanto + agentmemory + mem0 + Letta), publicamos. **E só publicamos quando ganhamos.** Não vamos virar mais um README com gráfico maquiado. Empate aceita publicação se a metodologia limpa for honest signal; perda aceita publicação interna pra calibrar próximo move, nunca marketing.

---

## Os 3 pilares — Quality, Autonomy, Product

A partir de D40 (2026-05-17), o trabalho de evolução foi reorganizado em três pilares product-first + um Lab gated a 40% de capacity. Vision pra cada um, em horizonte 18 meses:

### Quality (Q) — "numbers that lead"

Em 18 meses, Nox-mem ganha consistentemente os benchmarks públicos de memória de longo prazo (LoCoMo e LongMemEval), entrega p95 de retrieval abaixo do que SaaS competidor consegue (porque rodamos local sem network hop), e publica `COMPARISON.md` cujo design é honest-by-construction — mesma query, mesma dataset, mesmas regras, scoring auditável. "Numbers that lead" significa que quem chega no repo lê a primeira tabela e fecha a decisão. Não significa "ganhamos por 0.3pp num benchmark sintético"; significa diferencial perceptível em uso real. Se o número não chegar lá, o pilar Q não publica até chegar. Disciplina sobre vaidade.

### Autonomy (A) — "data is yours, completely"

Em 18 meses, autonomia evolui de "arquivo SQLite portável" pra **federation**: várias instâncias de Nox (laptop + VPS + segundo Mac) sincronizam via mesh peer-to-peer sem servidor central, sem cloud broker, sem vendor de sincronização. Você decide quais instâncias confiam em quais. Encrypted-by-default vira encrypted-end-to-end no transporte. Provider abstraction (já scaffolded em A3) permite trocar Gemini por OpenAI/Voyage/local em uma flag — Gemini fica como default porque o número manda, não porque o vendor manda. Zero-vendor validation (A4) é teste contínuo no CI: a suíte roda sem nenhuma API key, contra mocks e fixtures, e o sistema continua funcional em modo degradado. Se um dia o Toto resolver desligar tudo na nuvem, Nox-mem continua rodando — só perde semântica nova até reconectar provider.

### Product (UX) — "memory that shows up where you work"

Em 18 meses, Nox-mem é a camada de memória default que dev sério escolhe quando configura Claude Code, Codex ou Cursor. Não porque é grátis — é grátis hoje, sempre vai ser pro arquivo SQLite — mas porque a UX está exatamente onde o trabalho acontece: hooks auto-capture em Claude Code (P2) consolidam toda sessão sem manual ingest; `nox-mem answer` (P1) é o primitive natural quando você quer perguntar antes de buscar; queries temporais (P3) — "o que decidi sobre X semana passada?" — funcionam como linguagem nativa; `nox-mem connect <ide>` (P4) Tier A (3 IDEs deep: Claude Code, Codex, Cursor) cobre 80% do mercado dev real sem virar PR-spam de 12 IDEs shallow; viewer real-time (P5) na porta `18802/ui` te dá um Obsidian-like sem precisar abrir Obsidian.

O pilar UX é onde a maioria dos competidores de memória pra agentes erra. agentmemory provou que UX bem desenhada (auto-capture viral via hooks) vira 11.3k stars mesmo com arquitetura similar (BM25 + vec + KG + RRF). A diferença é que eles travaram o usuário no iii-engine runtime; a gente entrega o mesmo conforto sem travar.

---

## A disciplina do Lab — 40% capacity, gated graduation

Pesquisa é necessária mas perigosa. Antes de D40, capacity era 80% retrieval research interna (E13/E14/E15) — bom pro paper, péssimo pra produto visível. Pós-D40, Lab fica capado em **40% da capacity** e cada experimento tem **gate explícito pra graduar**:

- **Hipótese** com baseline numérico esperado
- **Shadow-mode obrigatório** com janela de baseline (mínimo 1 semana)
- **Gate métrico** definido antes de começar (ex: L3 confidence field requer ≥1.0pp absolute lift no eval pra integrar ao ranking — abaixo disso, o schema fica isolado e o ranking integration vira iteração separada)
- **Cut criteria** explícito — quando o experimento morre

Lab tem três áreas vivas hoje (L1 retrieval research em pausa pós-pivot, L2 conflict detection inspirada por memanto, L3 confidence field gated). O que graduar do Lab vira feature de pilar (Q/A/P). O que não graduar morre publicamente em `DECISIONS.md` com aprendizado registrado (D36, D38, D39 são exemplos vivos disso). Falha pública é cultura. Cemitério de ideias é honesto.

---

## A competição e onde a gente se encaixa

| Player | Star count (2026-05) | O que oferece | O que sacrifica | Posição |
|---|---|---|---|---|
| **memanto** (Moorcheh) | ~126 | Memória SaaS-first, pitch acadêmico, conflict detection bonita | Dados na nuvem deles, lock-in via API, custo recorrente | SaaS premium nicho |
| **agentmemory** (iii-engine) | ~11.3k | UX viral (hooks auto-capture, multi-IDE breadth, real-time viewer, marketing forte) | Runtime proprietário (iii-engine), data preso ao runtime | Produto viral lock-in |
| **gbrain** (Garry Tan) | ~16.6k | Personal brain framework, halo VC famoso, UX clean | Foco personal brain, não memory layer agnóstico; autonomy não é selling point principal | Personal productivity tool |
| **mem0** | ~30k+ | Memory layer abstraction, multi-backend, dev mindshare | Camada de abstração; quality é tão boa quanto o backend que você pluga | Infra layer |
| **Letta** (ex-MemGPT) | ~12k+ | Agent runtime com memória embutida, hierarquia stateful | Você compra o runtime inteiro; memória não é portável fora | Agent runtime |
| **nox-mem** | (privado, em open-source rampup) | Hybrid retrieval premium (Gemini 3072d + RRF language-aware + pain salience + KG edge typing), autonomy genuína (SQLite portável), shadow discipline, transparent benchmarks | Curva de adoção mais alta (não é "npm install pronto"), foco em qualidade não em breadth shallow | **Quality + Autonomy + UX honesta** |

O quadro acima desenha **o vácuo no mercado** que Nox ocupa. memanto pede que você confie no servidor deles. agentmemory pede que você confie no runtime deles. gbrain te dá um framework pessoal mas não vende memory-layer pra agentes. mem0 é layer fina — qualidade depende de quem você pluga embaixo. Letta vende o runtime — você compra tudo ou nada.

Ninguém mais entrega simultaneamente: (a) arquivo SQLite seu portável, (b) qualidade de retrieval que ganha benchmark público, (c) UX que mora dentro do Claude Code / Codex / Cursor sem extrair você pra outra UI. Esse é o gap. É terreno defensável porque exige disciplina arquitetural que SaaS-first companies não pagam o custo de ter (eles ganham margem em lock-in), e que viral-runtime companies já abriram mão (não dá mais pra desfazer iii-engine sem refazer produto).

---

## Marcos de 18 meses

Datas são intencionais — vision sem prazo é wishlist. Cada bloco é gated em medição empírica, não em vontade.

**2026 Q3 — Quality declarado e GTM Phase 2 launched.** Q1 (LoCoMo), Q2 (LongMemEval) e Q3 (latência p95) com números que liderem ou empatem topo. Q4 (`COMPARISON.md` head-to-head) publicado se e somente se as três anteriores entregarem. GTM Phase 2 lança simultânea: README hero com tagline + COMPARISON table + 30s install demo. Asset production (banner + 6 stat SVGs + logo D minimal + accent `#00C896`) já está pronto (PR #19, completed D41), aguardando gate Q4.

**2026 Q4 — Product breadth no Tier A IDEs.** P1 (`nox-mem answer`) + P2 (hooks auto-capture Claude Code) + P3 (queries temporais) + P4 Tier A (Claude Code + Codex + Cursor connect) + P5 (real-time viewer porta 18802) entregues. Tier B (passive MCP pra outros IDEs) sai grátis porque MCP já está implementado. Foco: três IDEs com integration profunda > doze IDEs com adapter raso.

**2027 H1 — Federation prototype + Nox-Supermem comercialização.** Federation A2-extended: multiple Nox instances sync via P2P mesh, sem broker. Validação inicial Mac do Toto + VPS Hostinger + (eventual) segundo Mac. Encryption end-to-end no transporte. Nox-Supermem (productized layer pra brasileiros via Hotmart, tiers A/B/C) sai do `nox-supermem/` repo como produto comercializado — mesma engine, marketing nacional, instalador friendly, suporte português.

**2027 H2 — API platform com autonomia preservada.** Nox-mem-as-a-service, com a regra crítica: "service" significa "sua instância na sua infra, com nossas knobs", **nunca** "seus dados nos nossos servidores". Possíveis formas: instalador one-line que provisiona Nox numa VPS sua via Tailscale; tier hosted onde rodamos Nox numa instância dedicada que **você possui** (não compartilhada, não multi-tenant); operator Kubernetes pra quem tem cluster. Em qualquer forma, a invariante é: o arquivo SQLite mora onde você manda, não onde a gente manda.

---

## O que a gente nunca faz

Linhas vermelhas. Não negociáveis. São a contrapartida do moat — se você violar uma, perde o diferencial inteiro.

- **Nunca colocamos dados do usuário em servidor nosso.** Não tem cluster Postgres central, não tem S3 bucket nosso com chunks alheios, não tem "free tier hosted" que armazena dados de cliente em nossa infra. Variantes hosted no horizonte 2027 H2 são single-tenant dedicado pra um usuário cada — mesmo princípio.
- **Nunca travamos via daemon proprietário ou runtime exclusivo.** SQLite + sqlite-vec + FTS5 é open-source standard. Provider Gemini é trocável (A3). Você consegue ler `nox-mem.db` com `sqlite3` CLI puro pra sempre.
- **Nunca publicamos benchmark que perdemos como se tivéssemos ganhado.** Se o número não está lá, COMPARISON.md não sai. Marketing baseado em métrica massageada destrói credibilidade técnica, e credibilidade técnica é o ativo desse projeto. Honest by construction.
- **Nunca aceitamos "primeiro em benchmark" se exige UX hostil.** Se ganhar LoCoMo exigir que usuário rode 7 comandos pré-query, não vale. Métrica boa + UX boa, ou não publica.
- **Nunca competimos em breadth shallow.** Doze adapters de IDE feitos no fim de semana > três adapters profundos? Não. Tier A profundo (Claude Code + Codex + Cursor) é onde a gente investe. Tier B (passive MCP) cobre o resto sem prometer profundidade. Breadth without depth é PR-spam que dilui marca.
- **Nunca atalhamos shadow discipline em mudança de ranking.** Já evitou regressão custosa mais de uma vez. Cada ranking change passa por baseline 1 semana mínimo em `/api/health`, comparando A/B contra produção. "Foi um fix pequeno" não é exceção; é o cenário onde o bug entra escondido.

---

## O compromisso cultural

Nox-mem não é um produto onde se esconde decisão. Cemitério de ideias é público — `docs/DECISIONS.md` D36, D38, D39 documentam fixes que NÃO funcionaram, mantidos no canônico pra que ninguém (incluindo Toto daqui a 6 meses) tente o mesmo caminho de novo. D40 e D41 documentam o pivot Q/A/P + as 5 polish decisions de 2026-05-18 com razão e alternativas rejeitadas.

Shadow discipline em retrieval é uma cara desse compromisso. Honest evaluation em benchmark é outra cara. Failure debrief público é a terceira. Não vendemos certeza; vendemos disciplina pra alcançar certeza.

Contribuição externa é bem-vinda, com uma única regra: PR que toca retrieval/ranking entra com shadow-mode + métrica baseline obrigatórios. PR de UX entra normal. PR de novo backend entra com test isolation contra mocks (zero-vendor invariant). Quem entender essa cadência se sente em casa rápido.

Nox-mem é construído por uma pessoa (Toto) operando como advisor / board member / empreendedor de fundo, com fluência em todas as funções C-level por trajetória passada, e usando agentes IA (Atlas, Boris, Cipher, Forge, Lex, Nox) como time de execução paralelo. Esse modelo de trabalho — 1 humano + N agentes coordenados — é em si parte da tese: memória de qualidade pra agentes é a infraestrutura que torna o modelo escalável. Construímos a coisa que usamos.

---

## Fechamento

*Pain-weighted hybrid memory with shadow discipline — yours by design.*

Em 18 meses o sucesso parece com isso: dev sério configurando Claude Code roda `nox-mem connect claude-code`, faz pergunta, recebe resposta com fonte citada de uma SQLite que mora no laptop dele, com numbers que lideram o leaderboard público, sem nunca ter pensado em "qual SaaS posso usar pra memória do meu agente". O arquivo é dele. A latência é dele. O controle é dele. A gente entregou o engine + a UX + os benchmarks; ele entregou o uso. E todo mundo sabe — porque está em `COMPARISON.md` com método auditável — que essa é a opção que ganha em qualidade **e** em autonomia, não escolhendo um dos dois.

Esse é o ponto inteiro.

---

*Última revisão: 2026-05-18 (pós-D40 + D41). Próxima revisão: pós-Q4 gate (2026 Q3 esperado) ou sempre que pivot estratégico justificar.*
