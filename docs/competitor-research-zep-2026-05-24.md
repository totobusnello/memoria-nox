# Zep Cloud Competitive Research — 2026-05-24

## TL;DR (3 linhas)
- Zep Cloud é SaaS de context engineering / agent memory baseado em Graphiti (temporal KG sobre Neo4j), com pricing por crédito (ingestion-based, ~$25/10k créditos) e tier Enterprise com BYOC + HIPAA + SOC2.
- YC W24, ~$2.3M raised (seed + convertible note), fundado 2023 por Daniel Chalef. Produto comercial é cloud-only; OSS Graphiti (Apache 2.0) é só o motor de grafo, sem o layer managed de context engineering.
- nox-mem nDCG@10 = 0.6380 vs Zep OSS 0.3909 (+63% absoluto). Fraqueza crítica: depende de Neo4j + OpenAI por padrão — anti-tese do Pillar A.

---

## Product

### OSS vs Cloud — onde a linha está

| Aspecto | Graphiti OSS (Apache 2.0) | Zep Cloud (SaaS) |
|---|---|---|
| Motor de grafo temporal | ✅ MIT graph engine | ✅ gerenciado |
| Multi-tenant / projects | ❌ | ✅ (até 2 projects no Flex) |
| Dashboard / monitoring | ❌ | ✅ |
| SSO + RBAC + Audit logs | ❌ | ✅ Enterprise |
| BYOC / BYOK / BYOM | ❌ | ✅ Enterprise |
| SOC 2 Type II / HIPAA BAA | ❌ | ✅ Enterprise |
| Suporte dedicado (Slack) | ❌ | ✅ Enterprise |
| Context assembly automático | ❌ (engine raw) | ✅ (managed retrieval orchestration) |
| Latência garantida | — | <200ms SLA |

**Conclusão:** Graphiti OSS é só o motor de KG. O produto real (context assembly, retrieval orchestration, multi-tenant, compliance) é cloud-only. Não há caminho self-hosted com feature parity — só o grafo nu.

### Pricing tiers (confirmado via official page)

| Tier | Preço | Créditos | Limite / notas |
|---|---|---|---|
| **Free** | $0 | 1,000/mês | Sem rollover, sem auto-topup, 1 project |
| **Flex** | $25 por 10k créditos (auto-topup) | 10k créditos/topup | Rollover 30d, 2 projects |
| **Flex Plus** | $75 por 40k créditos (auto-topup) | 40k créditos/topup | Rollover 60d, 2 projects |
| **Metered** | $1.25/1k mensagens + $2.50/MB data | Ilimitado | Rate limits maiores, ideal produção |
| **Enterprise** | Custom | Ilimitado | BYOC/BYOK/BYOM, SSO, HIPAA BAA, SLA dedicado |

**Modelo de cobrança:** por ingestion/processamento de Episodes. 1 crédito = até 350 bytes. Armazenamento é gratuito. Você paga por processar, não por guardar.

### Features principais que vendem

1. **Graphiti Temporal KG** — cada fato tem dois eixos de tempo: event_time (quando foi verdade no mundo) + ingestion_time (quando Zep aprendeu). Agentes raciocinam sobre mudanças históricas de forma nativa.
2. **Fact extraction + entity disambiguation** — LLM extrai entidades e relações automaticamente de conversas e business data estruturado; sem authoring manual.
3. **Context assembly <200ms** — Zep orquestra busca semântica + keyword + graph traversal e entrega contexto montado, não chunks brutos. "Context engineering platform" é o pitch, não "memória".
4. **Provider flexibility (parcial)** — Graphiti suporta OpenAI, Azure OpenAI, Gemini, Anthropic, Groq, Ollama. Na prática, Cloud usa OpenAI como default; BYOM só no Enterprise.
5. **MCP Server 1.0** — Graphiti MCP Server 1.0 lançado recentemente, expõe KG via MCP protocol nativo.

---

## Customers

### Segmentos

- **Primário:** AI-native startups construindo agentes para domínios verticais (finance, healthcare, enterprise SaaS)
- **Secundário:** scale-ups com engenharia interna que precisam de context layer sem construir do zero
- **Enterprise gated:** compliance-heavy (HIPAA = healthcare / fintech) via BYOC/BYOK

### Case study público confirmado

**Athena Intelligence** — agentes autônomos para decisões de alto risco em finance, healthcare e enterprise:
- Produto central: Tia, assistente AI para compliance audits, financial reporting, medical documentation
- Problema: usuários reexplicavam portfolio preferences e risk tolerance a cada sessão — zero memória persistente
- Solução: Zep context layer com temporal KG
- Resultado: KG expandiu para **160+ nodes e 220+ edges em menos de 3 horas**; contexto retido cross-session
- Motivação declarada: "escolheram Zep pra shippar mais rápido e focar no core product"

### Sem outros case studies públicos

Não há segunda empresa nomeada no site. Tração principal é via comunidade dev (GitHub/Discord) e referências de partners (LangChain, AutoGen, LlamaIndex ecosystem).

---

## Funding

| Round | Data | Valor | Investidores |
|---|---|---|---|
| Pre-Seed | Mar 2024 | $500K | **Y Combinator (W24)** |
| Convertible Note | 2024 | — | Não divulgado |
| **Total raised** | — | **~$2.3M** | YC + convertible |

- **Stage:** post-seed / pre-Series A (YC W24). Nenhuma Series A/B anunciada.
- **Fundador:** Daniel Chalef (solo founder confirmado)
- **HQ:** San Francisco (2261 Market Street)
- Referência crunchbase menciona Bessemer como investidor potencial mas não confirmado em round fechado.

**Implicação:** empresa muito early. $2.3M total é pouco para infra enterprise. BYOC/SOC2/HIPAA são credenciais de produto, não necessariamente de empresa estabelecida.

---

## GitHub / OSS Activity

| Repo | Stars | Status |
|---|---|---|
| `getzep/graphiti` | **~20k+ stars** (hit 20k milestone anunciado) | Ativo — releases frequentes, MCP Server 1.0 recente |
| `getzep/zep` (legacy OSS) | — | **Deprecated** — Community Edition movida para `legacy/` folder |

**Mudança estratégica crítica (2026):** Zep anunciou nova direção OSS — Community Edition **descontinuada e deprecated**. OSS focus migrou 100% para Graphiti. O produto Zep (context engineering layer) é agora **cloud-only sem exceção**. Não há mais self-hosted Zep.

- Graphiti: ~35 contributors, 25k weekly PyPI downloads, releases regulares
- Última atividade `getzep/zep`: abril 2026 (exemplos e integrações apenas)
- Paper técnico arxiv: `2501.13956` — "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" (Jan 2025)

---

## Integrações Nativas

| Framework | Suporte |
|---|---|
| LangChain / LangGraph | ✅ nativo (documentado + exemplos) |
| LlamaIndex | ✅ nativo |
| AutoGen (Microsoft) | ✅ (Microsoft docs citam Zep) |
| CrewAI | Não confirmado |
| OpenAI Assistants | Não confirmado |
| MCP Protocol | ✅ Graphiti MCP Server 1.0 |
| Neo4j | ✅ requerido para Graphiti OSS (5.26+) |
| FalkorDB | ✅ alternativa ao Neo4j (1.1.2+) |
| Ollama | ✅ via Graphiti (LLM local) |

**Dependência crítica:** Graphiti OSS requer Neo4j ou FalkorDB como backend de grafo. Não há opção SQLite. Isso é uma barreira de adoção significativa para devs individuais e projetos solo.

---

## GTM Implications for nox-mem

### Como atacar (3-5 bullets)

1. **"Zero infrastructure tax" vs Neo4j obrigatório** — Zep OSS exige Neo4j 5.26+. nox-mem é um arquivo SQLite. Para o developer individual, startup early-stage, ou qualquer cenário sem Neo4j já provisionado, nox-mem ganha em time-to-first-memory por ordem de magnitude. Pitch: "Zep precisa de Neo4j rodando. nox-mem precisa de `cp`."

2. **Benchmark direto publicável** — nox-mem nDCG@10 = 0.6380 vs Zep OSS 0.3909 (+63%). E latência: nox-mem p50 = 7-12ms vs Zep OSS p50 = 15.216ms (15 segundos vs milissegundos). Estes números são armas GTM quando o Q4 COMPARISON.md for publicado.

3. **Data autonomy vs deprecated OSS** — Zep Community Edition foi deprecated. Usuários que adotaram OSS Zep estão em dead end forçando migração para cloud pago. nox-mem MIT stay-forever é contraposição direta: "nosso OSS nunca será deprecated, nunca vai te forçar para SaaS."

4. **Custo de ingestion vs custo de armazenamento** — modelo Zep cobra por processar ($1.25/1k mensagens). nox-mem não tem custo por mensagem — você paga o provider LLM diretamente (Gemini API) e o SQLite é seu. Para alto volume de ingestão, vantagem de custo cresce exponencialmente.

5. **Narrativa "context engineering" vs "memory substrate"** — Zep pivotou para "context engineering platform" em 2025 (não se chama mais só de "memory"). Se nox-mem vai por qualidade de retrieval puro (nDCG + coverage), os produtos não colidem diretamente na narrativa. nox-mem pode ser o "memory layer que você usa antes de precisar de context engineering."

### Onde Zep é forte (não desperdiçar energia)

- **Enterprise compliance** — SOC2 Type II + HIPAA BAA + BYOC é moat real para healthcare/fintech enterprise. nox-mem não compete aqui hoje (nem deve no Q/A/P Q0/Q1).
- **LangGraph/LangChain ecosystem** — Zep tem integrações nativas profundas com o ecossistema LangChain. Se o mercado-alvo de nox-mem é usuário Claude Code / OpenClaw, não colide. Se for LangChain devs, Zep tem vantagem de friction zero.
- **Temporal reasoning narrativa** — Graphiti paper arxiv + "event_time vs ingestion_time" é narrativa técnica sólida e defensável. Não tentar copiar; diferenciar por coverage vs concentration (conforme D59 framing).
- **YC brand + comunidade** — 20k stars Graphiti é social proof real. No espaço GTM comunitário, Zep está à frente.

### Onde Zep é fraco (onde nox-mem ataca)

- **OSS deprecated** — Community Edition morreu. Usuários OSS estão expostos a vendor lock-in imediato. nox-mem MIT = trincheira Autonomy.
- **Retrieval quality medível** — nDCG@10 0.3909 vs 0.6380 é diferença enorme quando Q4 cross-system for publicado. Zep não publica benchmark comparativo honesto.
- **Neo4j dependency** — barreira de infra alta. Zero opção SQLite-only. Qualquer dev solo, indie hacker, ou pequeno time descarta Zep cedo por causa disso.
- **Modelo de pricing por ingestion** — previsibilidade baixa para produto com alto volume de conversas. nox-mem tem custo fixo (API key do provider, sem markup per-message).
- **Early stage + pouco funding** — $2.3M total com produto cloud-only e infra enterprise é financeiramente tenso. Risco de pivot ou down-round público.
- **Latência OSS** — 15s p50 é catastrófico para uso real-time. Mesmo se Cloud for mais rápido (<200ms SLA), indica arquitetura que não escala trivialmente.

---

## Referências

- [Zep homepage](https://www.getzep.com/) — "Context Engineering & Agent Memory Platform"
- [Zep pricing](https://www.getzep.com/pricing/) — créditos + metered + enterprise
- [Athena Intelligence case study](https://www.getzep.com/customers/athena-intelligence/) — único case público
- [Graphiti GitHub](https://github.com/getzep/graphiti) — 20k+ stars, MCP Server 1.0
- [Zep GitHub (legacy)](https://github.com/getzep/zep) — Community Edition deprecated
- [arXiv paper 2501.13956](https://arxiv.org/abs/2501.13956) — "Zep: A Temporal Knowledge Graph Architecture for Agent Memory"
- [Zep AI Crunchbase](https://www.crunchbase.com/organization/zep-ai) — funding $2.3M, YC W24
- [New OSS direction blog post](https://blog.getzep.com/announcing-a-new-direction-for-zeps-open-source-strategy/) — Community Edition deprecated
- [Zep Enterprise page](https://www.getzep.com/enterprise/) — BYOC/BYOK/BYOM, SSO, HIPAA
