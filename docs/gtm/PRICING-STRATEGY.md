# Nox-Supermem — Pricing Strategy

> Documento estratégico para GTM do produto comercial Nox-Supermem.
> **Este documento apresenta hipóteses e frameworks — não decisões de pricing.**
> As decisões cabem a Toto após validação com o mercado.
>
> **Status:** 2026-05-18 (Wave H — pré-GTM, hipóteses iniciais)
> **Produto:** Nox-Supermem (repo `nox-supermem/`) — camada comercial sobre o OSS nox-mem
> **Plataforma inicial:** Hotmart (mercado BR), com expansão para stripe global
> **Cross-links:** `docs/cost-model.md` · `docs/COMPETITIVE-POSITIONING.md` · `docs/gtm/ROI-CALCULATOR.md`

---

## Índice

1. [O que estamos vendendo](#1-o-que-estamos-vendendo)
2. [Posicionamento de preço](#2-posicionamento-de-preco)
3. [Hipóteses de tiers](#3-hipoteses-de-tiers)
4. [Anchors competitivos](#4-anchors-competitivos)
5. [Estratégia freemium e trial](#5-estrategia-freemium-e-trial)
6. [Funil de conversão](#6-funil-de-conversao)
7. [Riscos de churn e defesas](#7-riscos-de-churn-e-defesas)
8. [Projeções de receita (ilustrativas)](#8-projecoes-de-receita)
9. [Contexto Hotmart e mercado BR](#9-contexto-hotmart-e-mercado-br)
10. [Matriz de decisão — perguntas abertas para Toto](#10-perguntas-abertas)

---

## 1. O Que Estamos Vendendo

### O produto hosted Nox-Supermem

Nox-Supermem **não é** um produto diferente de nox-mem. É a **camada de conveniência** sobre o OSS nox-mem:

| O que nox-mem OSS exige | O que Nox-Supermem elimina |
|---|---|
| Git clone + npm install + Node.js | 1 clique de signup |
| Configurar VPS Hostinger | VPS gerenciado por nós |
| Obter Gemini API key + configurar .env | Key gerenciada; usuário não precisa saber |
| `rsync` ou SSH para sincronizar entre dispositivos | Cloud-native, multi-device automático |
| Configurar backup + DR | Backup automático + ponto de restore |
| Atualizar versão manualmente | Updates automáticos |
| Monitorar `nox-mem-api` uptime | SLA gerenciado |

### O que NÃO muda com Nox-Supermem

- O SQLite é do usuário. Export a qualquer momento (A2 — export/import portável)
- Dados **não** são vendidos, analisados para treinamento, ou compartilhados com terceiros
- Usuário pode self-hostar a qualquer hora com os mesmos dados
- OSS MIT permanece free para sempre

### Proposição de valor em uma frase

*"Pay for time, not for data — seus dados ficam com você, a infraestrutura fica com a gente."*

---

## 2. Posicionamento de Preço

### Framework: valor percebido vs custo real

O custo de self-hosting para um power user é ~$10/mês (VPS $6 + provider ~$4). O valor percebido de **não ter que fazer isso** depende do perfil:

- **Developer early adopter**: sabe self-hostar; pagaria até $15–20/mês para não precisar
- **Profissional de conhecimento** (consultor, pesquisador, gerente): não quer VPS; pagaria $20–30/mês
- **Team lead** com equipe: justifica $30–60/mês/usuário se eliminar overhead de setup para time
- **Enterprise**: não se discute $5–20/usuário/mês com time de 50 pessoas

### Princípio de pricing: não competir com self-hosting no preço

Self-hosting sempre será mais barato para quem tem o skill. Isso é intencional — o Pillar A (Autonomia) exige que self-hosting seja always-viable. O hosted tier compete em **conveniência e tempo**, não em preço.

Referência de mercado (todos USD, valores mensais, 2026-05):

| Produto | Tier | Preço | O que oferece |
|---|---|---|---|
| ChatGPT Plus | Único | $20/mês | GPT-4o + plugins + memory |
| Notion AI | Add-on | $10/mês | AI assist em workspace Notion |
| Claude Pro | Único | $20/mês | Claude Opus 4.5 + projetos |
| Cursor Pro | Único | $20/mês | IDE com AI |
| Copilot Individual | Único | $10/mês | GitHub Copilot |
| memanto | (sem pricing público) | ~$10–30 hipotético | SaaS memory layer |

Posição alvo: **entre Notion AI ($10) e ChatGPT Plus ($20)** para o tier pessoal. Abaixo de $20 para não criar friction de comparação com o "já pago ChatGPT".

---

## 3. Hipóteses de Tiers

> Hipóteses — não são preços definidos. Números marcados com `[H]` são hipotéticos.

### Tier 0 — Free (OSS puro)

**Quem é:** Developer, entusiasta, power user que quer controle total
**Oferta:**
- nox-mem completo, MIT, self-hosted
- Usuário provê Gemini API key (ou outra)
- Usuário gerencia VPS, backups, updates
- Comunidade Discord/GitHub para suporte

**Limites:**
- Nenhum limit técnico — é OSS
- Zero custo para o usuário (paga direto ao provedor)
- Zero receita para nós

**Função estratégica:**
- Acquisition channel — GitHub stars → conversão para tier hosted
- Credibilidade técnica — "se fosse ruim, por que tantos devs usariam?"
- Pressão de qualidade — bugs expostos na comunidade antes de chegarem aos pagantes

---

### Tier 1 — Personal [H: $9–$15/mês]

**Quem é:** Desenvolvedor ou profissional de conhecimento que quer memória persistente sem administrar infraestrutura.

**O que inclui:**
- nox-mem hospedado em VPS gerenciado (KVM 1 dedicado logicamente por usuário)
- Gemini API key gerenciada — usuário não precisa ter conta no Google AI Studio
- Backup automático diário + retenção 30d
- Updates automáticos de versão
- Multi-device (sync via API hosted)
- Suporte via email (SLA 48h)

**Limites [hipotéticos]:**
- `[H]` 50k chunks max no corpus
- `[H]` 1.000 queries/dia
- KG extraction: incremental nightly (não real-time)
- 1 usuário/conta

**Custo interno estimado (ver `docs/cost-model.md` §9):**
- VPS fraction: ~$2/usuário/mês (em escala de 10+ usuários/VPS)
- Provider cost (Gemini): ~$1–2/usuário/mês (power user do tier)
- Margem bruta target: 60–70%

**Preço ainda aberto:** $9/mês (agressivo, volume-first) vs $15/mês (margem-first). Ver pergunta aberta P1.

---

### Tier 2 — Pro [H: $25–$40/mês]

**Quem é:** Power user, pesquisador, engineer senior que usa memoria extensivamente.

**O que inclui tudo do Personal mais:**
- Corpus expandido `[H]`: 250k chunks
- `[H]` 5.000 queries/dia
- KG extraction real-time (não só nightly)
- P5 viewer hosted (SSE real-time dashboard)
- L2 conflict detection ativa (quando shipped)
- L3 confidence/provenance ativa (quando shipped, gated on eval)
- Suporte via email (SLA 24h) + Discord prioritário

**Custo interno estimado:**
- VPS fraction: ~$3–4/usuário/mês
- Provider cost: ~$4–6/usuário/mês
- Margem bruta target: 55–65%

---

### Tier 3 — Team [H: $20–$35/usuário/mês, min 3 usuários]

**Quem é:** Time de produto, startup de produto, grupo de pesquisa.

**O que inclui tudo do Pro mais:**
- Multi-user (shared corpus + per-user namespaces)
- Cross-agent search (compartilhamento seletivo de memória entre usuários)
- Audit log visível (quem ingested o quê, quando)
- Admin dashboard para gerenciar usuários
- SSO (SAML/OIDC) — [H: apenas tiers >= 5 usuários]
- Suporte dedicado via Slack/Discord compartilhado (SLA 8h)

**Custo interno estimado (5 usuários):**
- VPS: ~$15/mês (VPS KVM 2 dedicado)
- Provider: ~$20/mês (volume maior de queries)
- Overhead de multi-tenancy: $5/mês
- Receita hipotética (5 × $25): $125/mês → margem ~70%

---

### Tier 4 — Enterprise [H: custom, $500–$3k/mês]

**Quem é:** Empresa com 20+ usuários, equipes de AI, pipelines automatizados.

**O que inclui tudo do Team mais:**
- VPS dedicado (não compartilhado)
- Custom SLA (99.9% uptime, resposta <4h)
- On-premise option: suporte + consultoria para self-host na infra do cliente
- LGPD compliance documentado (A1.1 BR patterns, data residência Brasil)
- Integração com sistemas internos (Slack, Notion, Google Workspace) via MCP
- Treinamento onboarding para time

**Modelo de preço:** custom. Âncora mínima hipotética: `[H]` $500/mês para 20 usuários.

---

## 4. Anchors Competitivos

### Posicionamento por dimensão

```
Preço           Barato ←─────────────────────────────────→ Caro
                        nox-supermem     memanto (hipot.)
                        Personal $12     ~$20-30
                 OSS     ↑                                   agentmemory (hosted?)

Controle         Mínimo ←─────────────────────────────────→ Máximo
(data autonomy)          memanto (zero)   agentmemory (baixo)  nox-mem (total)

Qualidade        Baixa ←─────────────────────────────────→ Alta
(benchmark)              gbrain (~grep)   agentmemory(claimed)  nox-mem (measured)
```

### Narrativa de posicionamento por audiência

**vs memanto:** "mesma conveniência de hosted, sem o lock-in. Você pode exportar tudo a qualquer hora com um comando. O SQLite é seu."

**vs agentmemory:** "agentmemory exige o iii-engine runtime — seu histórico de sessão fica preso nele. Com nox-mem, você pode mudar de VPS, mudar de provider de LLM, ou passar para self-hosted amanhã. Os dados seguem você."

**vs ChatGPT memory / Notion AI:** "essas ferramentas sabem o que você fez dentro delas. nox-mem sabe tudo que você permite — incluindo o que acontece fora delas."

---

## 5. Estratégia Freemium e Trial

### Princípio: reduzir friction, não reduzir preço

A barreira para adoção não é preço — é friction de setup. A estratégia correta é eliminar friction, não ofertar desconto.

### Opções de trial (hipóteses para validar)

**Opção A — Trial 14 dias sem cartão:**
- Usuário assina Personal sem inserir cartão de crédito
- 14 dias completos do tier
- No dia 14: pede cartão ou downgrade para sandbox limitado
- Pro: máxima conversão inicial; contra: mais churn de quem experimenta sem intenção

**Opção B — Sandbox permanente (1k chunks):**
- Tier hosted gratuito com limite técnico severo (1k chunks, 50 queries/dia)
- Útil para "ver funcionar" sem compromisso
- Conversão é orgânica: usuário cresce e atinge o limite
- Pro: menor churn; contra: usuário pode viver no sandbox para sempre

**Opção C — 30 dias de Personal com cartão salvo (refund garantido):**
- Cartão é registrado mas não cobrado no primeiro mês
- Conversão automática para billing no mês 2
- Pro: alta conversão para billing; contra: pode gerar chargebacks se mal comunicado

Recomendação para discussão: **Opção B como default** (sandbox permanente) + **Opção A disponível** como "upgrade trial" para quem quer ver o tier completo. Toto decide qual mix.

### "Export anytime" como sinal de confiança

Ao contrário de SaaS típico que esconde o botão de export, nox-mem deve **destacar** o export na landing page e no onboarding. Isso sinaliza: "não temos medo de você sair porque confiamos que o produto é bom."

---

## 6. Funil de Conversão

### Etapas do funil (OSS → Hosted → Pro)

```
1. GitHub (OSS discovery)
   ↓
   README com hero claro + benchmark + demo video
   ↓
2. Quickstart (<15 min para primeiro resultado)
   ↓
   Local install + 10 chunks ingeridos + primeira search com resultado
   ↓
3. Self-host friction point
   ↓
   VPS setup / API key / backup / multi-device → CTA: "existe versão hosted"
   ↓
4. Hosted trial (Personal sandbox ou 14d trial)
   ↓
   Onboarding: migrar corpus local para hosted; configurar sync
   ↓
5. Personal paying
   ↓
   Crescimento de corpus → volume limits → upsell Pro
   ↓
6. Pro → Team (quando usuário traz um colega)
   ↓
   "Convidar um membro" → trial Team; pricing per-seat
   ↓
7. Team → Enterprise
   ↓
   Volume + SLA requirements → custom contract
```

### Drivers de conversão por etapa

| Etapa | Driver | Métrica |
|---|---|---|
| GitHub → Quickstart | README quality + benchmark numbers | CTR para quickstart |
| Quickstart → Self-host | Time to first successful search | Completion rate |
| Self-host → Hosted trial | Friction pain (backup, multi-device, updates) | Trial signup rate |
| Trial → Paying | "Aha moment" (receber algo de volta que seria perdido) | Trial → paid conversion |
| Personal → Pro | Corpus growth rate (hitting limit) | Upgrade rate |
| Pro → Team | Referral (usuário Pro convidar colega) | Net promoter metric |

---

## 7. Riscos de Churn e Defesas

### Risco 1 — Usuário aprender a self-hostar

**Probabilidade:** Alta para developers (early adopters)
**Impacto:** Baixo (esses usuários eram o Free tier de qualquer forma)
**Defesa:** Não é churn — é o design. Free tier → community → contribuição OSS → mais stars → mais conversões pagas de outros perfis.

### Risco 2 — Competidor launch com preço menor

**Probabilidade:** Média (espaço está aquecendo)
**Impacto:** Alto para Personal tier (sensível a preço)
**Defesa:** Moat de autonomia (não comparável) + shadow discipline (qualidade comprovada) + dados são do usuário (cost of leaving é zero = trust signal)

### Risco 3 — Memanto lança tier free competitivo

**Probabilidade:** Alta (estratégia freemium é quase obrigatória no espaço)
**Impacto:** Reduz conversão de trial em topo de funil
**Defesa:** "Nosso free tier é OSS completo — o deles é SaaS com limite." Comunicar que o free OSS nox-mem tem zero lock-in e é o produto real.

### Risco 4 — Hostinger Brasil aumenta preços ou tem outage

**Probabilidade:** Baixa para preço; média para outage pontual
**Impacto:** Afeta margem (preço) ou NPS (outage)
**Defesa:** Abstrair provider de VPS na camada de infraestrutura; SLA deve ser honesto sobre o que controlamos vs o que Hostinger controla.

### Risco 5 — Hotmart aumenta taxa ou muda regras

**Probabilidade:** Baixa-média
**Impacto:** Reduz margem; pode exigir reprecificação
**Defesa:** Preço inicial deve absorver Hotmart fee de 10% como custo normal, não como desconto temporário.

---

## 8. Projeções de Receita (Ilustrativas)

> Todos os números abaixo são **projeções ilustrativas** para planejamento — não são forecasts ou compromissos. Servem para calibrar sizing de infraestrutura e decisões de investment.

### Y1 — Cenário conservador (pós-open-source launch, GTM Phase 2)

Premissas: GitHub stars → 5% trial → 20% trial→paid conversion. Preços hipotéticos: Personal $12, Pro $30, Team $40/usuário.

| Tier | Usuários pagantes | Receita/mês |
|---|---|---|
| Personal | 80 | $960 |
| Pro | 20 | $600 |
| Team (3 users avg) | 5 times × 3 = 15 seats | $600 |
| **Total Y1 end** | | **~$2.160/mês** |

Hotmart fee ~10%: receita líquida ~$1.944/mês
Custo de infra (VPS + provider): ~$400/mês
**Margem bruta: ~$1.544/mês (~80%)**

### Y2 — Cenário base

Premissas: 10k GitHub stars, word-of-mouth, 1 menção técnica relevante.

| Tier | Usuários pagantes | Receita/mês |
|---|---|---|
| Personal | 500 | $6.000 |
| Pro | 100 | $3.000 |
| Team | 30 times × 4 seats | $4.800 |
| Enterprise | 2 clientes | $2.000 |
| **Total Y2 end** | | **~$15.800/mês** |

### Path to $1M ARR

Três rotas plausíveis (não mutuamente exclusivas):

**Rota A — Volume Personal:** 7.000 usuários Personal × $12/mês × 12 = $1.008.000 ARR
**Rota B — Team:** 250 times × 5 usuários × $40/mês × 12 = $600.000 ARR + Personal/Pro para complementar
**Rota C — Enterprise:** 50 clientes × $1.700/mês × 12 = $1.020.000 ARR

Rota mais realista no horizonte de 3 anos: combinação B+C, com A alimentando o funil.

---

## 9. Contexto Hotmart e Mercado BR

### Por que começar pelo Brasil

- Mercado de SaaS B2B2C no Brasil é subservido por produtos de qualidade técnica alta
- Hotmart tem audience de tecnologia (developers, designers, produtores de conteúdo) já treinada para assinar produtos digitais
- LGPD é vantagem competitiva real: A1 privacy filter com BR patterns + data residência no Brasil (Hostinger BR) = compliance diferenciado
- Toto tem network BR relevante (Galapagos, Nuvini, FII Treviso) para warm outreach

### Hotmart — mecânica

- Taxa de marketplace: ~10% sobre cada venda
- Repasse: D+1 a D+3 para conta do vendedor
- Checkout já integrado com PIX, Boleto, Cartão BR
- Recorrência (assinatura mensal) é nativa na plataforma
- Afiliados: possível activar network de afiliados BR (relevante para tier Personal viral growth)

### Pricing em BRL vs USD

**Opção A — BRL-first:** R$ 59/mês (Personal) → ~$12 USD ao câmbio atual (≈5,0x)
- Mais natural para consumidor BR
- Exposição ao câmbio: se BRL desvaloriza, margem cai

**Opção B — USD com conversão dinâmica:** $12/mês USD, Hotmart converte no checkout
- Mais simples de gerenciar
- Usuário BR vê valor em dólares (pode causar friction para "não tech")

**Opção C — Dupla cotação:** Pricing em BRL no site BR, USD no site global
- Mais trabalho de manutenção
- Permite segmentar estratégia por mercado

Recomendação para discussão: BRL-first para Hotmart + USD para stripe global quando expandir. Toto decide.

### LGPD — Compliance points

Já endereçados no nox-mem OSS:
- A1 privacy filter (13 padrões BR incluídos — CPF, CNPJ, CEP, telefone BR, nome BR)
- Data residência: Hostinger Brasil datacenter
- Export A2: usuário pode exportar tudo a qualquer momento (direito de portabilidade LGPD Art. 18)
- Dados de terceiros em chunks: responsabilidade do usuário (escopo na ToS)

---

## 10. Perguntas Abertas

> Estas perguntas requerem decisão de Toto antes de fechar a estratégia de pricing.

| ID | Pergunta | Opções | Impacto |
|---|---|---|---|
| P1 | Preço do tier Personal: volume-first ($9) ou margem-first ($15)? | $9 / $12 / $15 | Velocidade de adoption vs margem bruta |
| P2 | Limite de chunks do Personal tier: 50k ou 100k? | 50k / 100k / unlimited | Diferenciação Pro vs Personal; custo de infra |
| P3 | Desconto anual: 10% ou 20% off mensal? | 10% / 20% / nenhum | ARR vs MRR; fluxo de caixa |
| P4 | Enterprise mínimo: $500/mês ou $1.500/mês? | $500 / $1.000 / $1.500 | Tamanho de cliente que faz sentido perseguir |
| P5 | BRL ou USD como moeda default no Hotmart? | BRL / USD / dual | Friction BR vs exposure ao câmbio |
| P6 | Trial sem cartão (14d) ou sandbox permanente (1k chunks)? | 14d trial / sandbox / ambos | Conversão inicial vs qualidade do funil |
| P7 | Network de afiliados Hotmart: ativar desde o início? | Sim / Não | Custo de aquisição vs velocidade |
| P8 | Incluir Gemini API key no hosted ou exigir que usuário traga a sua? | Incluir / BYOK | Simplicidade de onboarding vs custo marginal |
| P9 | Tier Team: per-seat ou flat por workspace? | Per-seat / Flat workspace | Previsibilidade de receita vs simplicidade |
| P10 | Lançar Personal antes de Team, ou os dois simultâneos? | Personal first / simultâneo | Foco de desenvolvimento vs cobertura de mercado |

---

*Documento gerado 2026-05-18 (Wave H). Próxima revisão: após Q4 gate abrir (COMPARISON.md nox-mem winning) ou após feedback de 10+ usuários em trial.*

*Cross-links: `docs/cost-model.md` · `docs/gtm/ROI-CALCULATOR.md` · `docs/COMPETITIVE-POSITIONING.md` · `docs/ROADMAP.md §GTM-Phase-2`*
