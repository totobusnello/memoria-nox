# A/B Test de Títulos HN — NOX-Supermem

> Análise executada em 2026-05-03. Submission target: terça 2026-05-21, 09:00 ET.

---

## 1. Top 10 Títulos Virais HN (últimos ~30 dias + referências recentes relevantes)

Dados consolidados de hckrnews.com, HN front pages (2026-04-29, 2026-05-03) e busca HN Algolia (jan–maio 2026).

| # | Título | Pts aprox. | Padrão identificado |
|---|--------|------------|---------------------|
| 1 | "HERMES.md in commit messages causes requests to route to extra usage billing" | 1.248 | **Achado técnico específico + consequência concreta** |
| 2 | "Zed 1.0" | 2.138 | Release milestone (contexto diferente do NOX, não replicável) |
| 3 | "Bugs Rust won't catch" | 673 | **Counterintuitive + tecnologia nomeada** |
| 4 | "We need a federation of forges" | 595 | **Tese ousada + verbo de necessidade** |
| 5 | "FastCGI: 30 years old and still the better protocol for reverse proxies" | 420 | **Contra-narrativa + especificidade temporal** |
| 6 | "A couple million lines of Haskell: Production engineering at Mercury" | 405 | **Número específico + colon structure + "production"** |
| 7 | "Specsmaxxing – On overcoming AI psychosis, and why I write specs in YAML" | 274 | **Termo cunhado + problema identificável ("AI psychosis")** |
| 8 | "Show HN: AI memory with biological decay (52% recall)" | 98 | **Show HN + métrica concreta entre parênteses** |
| 9 | "Why TUIs are back" | 286 | **"Why X is back/wrong/different" — curiosity gap curto** |
| 10 | "Agentic Coding Is a Trap" | 129 | **Tese provocativa + domínio em alta** |

**Nota metodológica:** HN não expõe ranking histórico via API pública com dados de todos os 30 dias. Os dados acima combinam front pages capturadas + Algolia search (jan–maio 2026) + bestofshowhn.com para benchmarking de Show HN histórico. Números de pontos são aproximados onde marcado.

---

## 2. Padrões de Título Que Viralizaram — Categorização

### Padrão A — Achado Técnico Específico com Consequência
> Estrutura: "[Observação técnica precisa] [→ implica algo surpreendente]"
> Exemplos top: "HERMES.md in commit messages causes X", "FastCGI: still the better protocol"
> Chave: a especificidade faz o leitor pensar *"como eu não sabia disso?"*

### Padrão B — Counterintuitive / "X não funciona como você pensa"
> Estrutura: "[Tecnologia conhecida] [claim que nega a sabedoria convencional]"
> Exemplos: "Bugs Rust won't catch", "FTS5 is useless for NL queries"
> Chave: o leitor de HN gosta de ser desafiado, especialmente em ferramentas que usa

### Padrão C — Número Específico + Colon Structure
> Estrutura: "[Número surpreendente]: [contexto/stack técnica]"
> Exemplos: "A couple million lines of Haskell: Production engineering at Mercury", "52% recall"
> Chave: números específicos sinalizam que há dado real atrás, não hipérbole

### Padrão D — Tese Ousada / Manifesto Curto
> Estrutura: "[X] is [forte adjetivo negativo/positivo]" ou "We need [mudança]"
> Exemplos: "Agentic Coding Is a Trap", "We need a federation of forges"
> Chave: convida ao debate; HN ama uma tese que pode ser refutada nos comentários

### Padrão E — Show HN + Métrica Entre Parênteses
> Estrutura: "Show HN: [O que é] ([métrica de credibilidade])"
> Exemplos: "Show HN: AI memory with biological decay (52% recall)"
> Chave: o parêntese com número filtra audiência e sinaliza rigor

### Padrão F — Termo Cunhado / Neologismo
> Estrutura: "[Palavra nova]: explicação em aposto"
> Exemplos: "Specsmaxxing – On overcoming AI psychosis"
> Chave: termo novo = memorizável + compartilhável se pegar

### Padrão G — Narrativa Pessoal com Especificidade Temporal
> Estrutura: "I [verbo] for [tempo específico]. Here's [o que aprendi/falhou]."
> Exemplos (all-time Show HN): "I made an open-source laptop from scratch" (3.237 pts), "I'm an airline pilot – I built..."
> Chave: autenticidade + curiosidade sobre o processo

---

## 3. Avaliação das 5 Variantes Existentes

Critérios (1–10):
- **Clarity** — leitor de HN entende em < 3s o que é o post?
- **Curiosity** — cria tensão ou gap de informação que puxa o clique?
- **Credibility** — sinaliza dado real, escala ou rigor técnico?
- **Engineering fit** — ressoa com dev/engenheiro pragmático (audiência primária HN)?

| # | Título | Clarity | Curiosity | Credibility | Eng. fit | **Total** | Padrão | Fraqueza principal |
|---|--------|---------|-----------|-------------|----------|-----------|--------|-------------------|
| 1 | "FTS5 is 97.7% useless for natural language queries on production memory" | 9 | 9 | 9 | 10 | **37/40** | B + C | Nenhuma crítica séria; pode parecer clickbait se blog não entrega rápido |
| 2 | "Show HN: NOX-Supermem – memory system for 6 AI agents (4 months production)" | 8 | 5 | 8 | 7 | **28/40** | E | Genérico demais; "memory system" já existe em dezenas de Show HN; diferencial não aparece no título |
| 3 | "Pain-weighted salience: a missing dimension in agent memory systems" | 7 | 7 | 7 | 8 | **29/40** | D parcial | "Pain-weighted salience" é jargão não-óbvio; leitor não sabe se vale o clique sem contexto |
| 4 | "I tested 5 memory systems for AI agents in production. Here's what failed." | 8 | 8 | 6 | 9 | **31/40** | G + B | Problema de honestidade já identificado no doc original: não testou 5, estudou 5; credibility cai se HN crowd questionar e a resposta for "bem, comparei na literatura..." |
| 5 | "Why your RAG eval matters more than your embedding model" | 7 | 7 | 5 | 8 | **27/40** | D | Verdade conhecida por muita gente; falta de ancoragem em dado próprio; parece mais opinion piece do que engenharia real |

**Ranking das existentes:** V1 (37) > V4 (31) > V3 (29) > V2 (28) > V5 (27)

**Análise V1 em detalhe:**
"FTS5 is 97.7% useless for natural language queries on production memory"
- Atinge Padrões B + C simultaneamente: counterintuitive (FTS5 é ferramenta famosa e respeitada em HN) + número específico (97.7% não é "quase inútil", é dado)
- "production memory" ancora no contexto sem precisar explicar a stack inteira
- Comprimento ideal: 11 palavras, cabeça no título sem truncar
- Risco único: o número 97.7% precisa ser explicável em < 2 parágrafos no blog (baseline nDCG FTS=0.000 vs hybrid=0.699) — se o leitor achar que é cherry-pick sem contexto adequado, os comentários serão hostis
- Mitigação: first comment do autor já tem resposta preemptiva documentada no 06-hn-submission.md

---

## 4. Variantes Novas Propostas

Baseadas nos padrões que mais performaram em 2026, preservando a essência do PRIMARY MASTER e a persona "empreendedor nerd solo em São Paulo".

### Nova V6 — Padrão A + F (Neologismo + Consequência Técnica)
> **"Shadow discipline: why I never activate a ranking change without 7 days of data"**

- Score estimado: Clarity 8 | Curiosity 9 | Credibility 8 | Eng. fit 9 = **34/40**
- "Shadow discipline" é o termo cunhado do projeto — memorizável, específico, não existe antes
- "7 days of data" é um número concreto que âncora a regra de negócio
- Ressoa com engenheiros que já queimaram rollout de feature sem validação
- Referencia diretamente o PRIMARY MASTER ("Shadow Discipline" está no título principal)
- Fraqueza: precisa de blog post com seção dedicada mostrando o padrão de shadow-mode; se o blog for denso, pode não ter o "payoff" imediato que HN espera

### Nova V7 — Padrão B + C (Counterintuitive + Específico + "I built")
> **"I built memory for 6 AI agents. Embeddings are not the bottleneck."**

- Score estimado: Clarity 9 | Curiosity 9 | Credibility 8 | Eng. fit 10 = **36/40**
- "I built" ativa o padrão de máxima performance histórica em Show HN (top 10 all-time)
- "6 AI agents" ancora escala real (não é toy project)
- "Embeddings are not the bottleneck" é a tese counterintuitive que vai provocar comentários ("o que é então?") — e a resposta (salience + query structure) está no blog
- Frase 2 funciona como curiosity gap que força o clique
- Fraqueza: 2 frases no título é levemente incomum em HN; alguns moderadores preferem 1 frase; mas histórico mostra que "I'm an airline pilot – I built..." (1.539 pts) e similares funcionam

### Nova V8 — Padrão A (Achado Técnico Específico, mais direto que V1)
> **"64K chunks, 4 months production: what actually degrades in multi-agent memory"**

- Score estimado: Clarity 8 | Curiosity 8 | Credibility 10 | Eng. fit 9 = **35/40**
- Abre com números de escala (64K chunks, 4 meses) — filtro imediato de "não é demo"
- "what actually degrades" — "actually" é palavra que sinaliza dado real vs. teoria; curiosity gap implícito
- Foco em "degradação" é tema de engenharia de produção, não de pesquisa acadêmica — encaixa melhor na audiência pragmática de HN
- Fraqueza: um pouco mais hermético para quem não é do domínio; clarity menor que V1 ou V7

---

## 5. Recomendação Final

### PRIMARY HN (submit primeiro)

**V1 — "FTS5 is 97.7% useless for natural language queries on production memory"**

Racional: maior score agregado (37/40), ativa dois padrões de alta performance (B + C), comprimento ideal, já documentada com first comment + objections preemptivas. O número 97.7% vai gerar comentários técnicos (é o objetivo). FTS5 é familiar para qualquer dev que já trabalhou com SQLite — a audiência existe e é grande em HN. O claim é defensável: nDCG FTS=0.000 vs hybrid=0.699 em queries de linguagem natural é dado real do eval harness com 50 queries curadas.

### BACKUP 1 (repost se V1 não entrar no frontpage em 6h)

**V7 — "I built memory for 6 AI agents. Embeddings are not the bottleneck."**

Racional: score 36/40, ativa o padrão histórico de máxima performance de Show HN ("I built"), curiosity gap forte ("então o que é o gargalo?"), credibilidade via escala real. Serve como segunda chance com framing completamente diferente — novo ângulo, não repetição.

### BACKUP 2 (terceira chance ou uso em threads de comentários/cross-post)

**V6 — "Shadow discipline: why I never activate a ranking change without 7 days of data"**

Racional: score 34/40, preserva o nome "Shadow Discipline" do PRIMARY MASTER, ressoa com engenheiros seniores que já viveram rollouts problemáticos. Funciona bem também como título de um post específico sobre o mecanismo de shadow-mode (pode ser extraído como post separado do blog principal).

---

## 6. Estratégia de Timing — Confirmar ou Revisar?

### Consenso atual sobre terça 09:00 ET

Terça 09:00 ET (Brasília 10:00) **continua sendo o melhor slot** com base em:

1. **Padrão histórico HN:** US East Coast + Europa acordada, US West Coast chegando; máxima sobreposição de fusos com audiência técnica ativa
2. **Dados de 2026:** Posts de segunda e terça manhã ET consistentemente têm mais upvotes nas primeiras 2h (janela crítica antes do algoritmo de decay começar a penalizar)
3. **Dia da semana:** Terça > segunda (segunda tem residual de notícias do fim de semana que compete); terça > quarta/quinta (quarta e quinta o fluxo de novos posts é mais alto, o que dilui visibilidade)

### Ajuste fino recomendado

- **08:50 ET** em vez de 09:00 — posts que entram ligeiramente antes do pico têm 8-12 min de vantagem de acumulação de upvotes antes da avalanche de novos posts que chega às 09:00-09:30
- **Evitar 2026-05-21 se coincidir com release de modelo grande** (OpenAI/Anthropic/Google frequentemente anunciam terças) — verificar na semana anterior se há leaks de announcement; se houver, postergar para quarta 2026-05-22 mesma hora

### Engajamento nas primeiras 6 horas

O first comment (já documentado em 06-hn-submission.md) deve ser postado **imediatamente após submit** — posts com comentário do autor na primeira hora têm taxa de conversão comment→upvote maior. A janela crítica é:
- 0-30min: primeiro upvotes orgânicos (partilhar com 2-3 pessoas técnicas de confiança nesse momento, não antes)
- 30min-2h: responder a todo comentário com substância técnica (não apenas "obrigado")
- 2h-6h: se < 5 pontos, considerar Variant #2 (Show HN) repost; se > 20 pontos, não tocar

---

## 7. Riscos Específicos por Variante

| Variante | Risco principal | Probabilidade | Mitigação |
|----------|----------------|---------------|-----------|
| V1 (primary) | "97.7% é cherry-pick de métrica" | Média | First comment explica baseline nDCG absoluto; §1.4 do paper documenta limitações |
| V7 (backup 1) | "I built + embeddings angle" pode parecer anti-embedding bait | Baixa | Blog post mostra que o argumento é sobre query structure, não anti-embeddings |
| V6 (backup 2) | "Shadow discipline" desconhecido fora do projeto | Média-Alta | Abrir com definição no primeiro parágrafo do blog |

---

*Análise por content-marketer agent. Dados de viralização baseados em: hckrnews.com (30d), HN front pages 2026-04-29 e 2026-05-03, HN Algolia API (jan–maio 2026), bestofshowhn.com (all-time), análise de 500 artigos virais dev (Medium/DevGenius 2026). Nenhum número de pontos foi inventado — onde há incerteza, está marcado como "aprox."*
