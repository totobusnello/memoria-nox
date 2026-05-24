# Checklist de Lançamento — Quarta-feira 2026-06-03

> **Operador solo:** Toto Busnello  
> **Janela crítica:** 05:01–12:00 BRT (PH go-live até encerramento do ciclo de manhã HN)  
> **Regra D27:** arXiv submetido Ter 06-02 → ID chega ~6h depois → link disponível antes de dormir Ter

---

## §1 Verificação pré-lançamento (Ter 2026-06-02 — tarde/noite)

> Completar TUDO antes de ir dormir Ter. Não lançar se algum item crítico estiver aberto.

### arXiv
- [ ] arXiv submission confirmada sem erros (LaTeX compila limpo)
- [ ] arXiv ID recebido por e-mail + URL anotada (formato `https://arxiv.org/abs/26XX.XXXXX`)
- [ ] PDF acessível publicamente no arXiv (testar em aba anônima)
- [ ] arXiv link embutido em: blog post, social copy (todos os canais), README badge

### Conteúdo
- [ ] Blog post v0 — revisão final: números Q4 cravados (+18.8% nDCG@10 + MRR), arXiv link inserido
- [ ] Social copy — revisão final: T1–T9 Twitter thread, HN body, Reddit body, PH copy revisados
- [ ] Rascunhos salvos localmente (não só em memória): Twitter thread, HN body, Reddit body, PH copy

### Assets visuais
- [ ] Demo GIF CLI (asciinema export) — gravado + comprimido + commitado no repo
- [ ] Demo GIF F10 dashboard — gravado + comprimido + commitado
- [ ] README hero final: números reais + arXiv badge + repo badge + demo GIF embutido
- [ ] Diagrama de arquitetura (se usado no blog/PH gallery) — versão final exportada

### FOSS hygiene
- [ ] `LICENSE` commitado (MIT ou Apache-2.0 — confirmar escolha)
- [ ] `CONTRIBUTING.md` commitado
- [ ] `CODE_OF_CONDUCT.md` commitado
- [ ] `SECURITY.md` commitado
- [ ] Nenhum segredo em staging: `grep -r "API_KEY\|api_key\|GEMINI" --include="*.ts" --include="*.js" src/ | grep -v '\.env'`

### Infraestrutura
- [ ] VPS health green: `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` — embedded == total
- [ ] `/api/answer` respondendo em <3s (smoke test: uma query simples)
- [ ] Cron healthcheck ativo (PR #164 — alerta 15min interval)
- [ ] Backup noturno confirmado (02:00 BRT automático)

### Product Hunt (único canal que agenda antecipado)
- [ ] PH draft criado: título, tagline, descrição, gallery (screenshots + GIFs), primeiro comentário do maker
- [ ] PH agendado para **Wed 2026-06-03 00:01 PST = 05:01 BRT** (PH permite agendar 24h em advance)
- [ ] Confirmar que Toto está listado como maker no produto (não precisa de hunter para self-launch)

---

## §2 Timeline do dia de lançamento (Qua 2026-06-03)

| Hora BRT | Hora ET | Hora PT | Ação | Canal |
|---|---|---|---|---|
| 05:01 | 04:01 | 01:01 | Product Hunt vai ao ar (automático via scheduled) | PH |
| 06:00 | 05:00 | 02:00 | Acordar. Verificar PH live + primeiros votos + primeiro comment do maker postado | PH |
| 06:30 | 05:30 | 02:30 | Verificar VPS health + /api/answer smoke test | Infra |
| 07:00 | 06:00 | 03:00 | Twitter thread T1 postado (prime time leste dos EUA abrindo) | Twitter |
| 07:05 | 06:05 | 03:05 | T2–T9 postados em sequência (1 por minuto) | Twitter |
| 07:30 | 06:30 | 03:30 | Reddit r/MachineLearning post submetido | Reddit |
| 07:45 | 06:45 | 03:45 | Reddit r/LocalLLaMA post (se relevante para Autonomy pillar) | Reddit |
| 09:00 | 08:00 | 05:00 | Blog post publicado no site pessoal (se planejado) | Blog |
| 09:05 | 08:05 | 05:05 | Tweet repromovendo blog post (linkar para post + arXiv) | Twitter |
| 09:30 | 08:30 | 05:30 | Responder primeiros comentários Reddit | Reddit |
| **10:00** | **09:00** | **06:00** | **HN Show HN submetido** ← SHIFTED (era 07:15 BRT / 06:15 ET; nova janela 09:00 ET = peak HN; ver análise em `docs/launch-hn-submission-final.md §5`) | **HN** |
| **10:01** | **09:01** | **06:01** | **Maker first comment postado no HN (dentro de 60s da submissão)** — copy em `docs/launch-hn-submission-final.md §4` | **HN** |
| 10:05 | 09:05 | 06:05 | Verificar comment apareceu; refresh thread | HN |
| 10:30 | 09:30 | 06:30 | Primeiro sweep de replies HN (top comments por pontuação) | HN |
| 10:30 | 09:30 | 06:30 | Trendshift submission (link repo + descrição curta) | Trendshift |
| 11:00 | 10:00 | 07:00 | LinkedIn announcement (opcional — audiência diferente de HN/Twitter) | LinkedIn |
| 12:00–18:00 | 11:00–17:00 | 08:00–14:00 | Janela ativa de respostas — HN / Twitter / Reddit / DMs | Todos |
| 18:00 | 17:00 | 14:00 | Checkpoint de métricas do meio do dia (ver §5) | — |
| 20:00 | 19:00 | 16:00 | Tweet de encerramento do dia — stats destacados + agradecimento à comunidade | Twitter |
| 22:00 | 21:00 | 18:00 | Revisão de comentários do blog + respostas pendentes | Blog/Twitter |
| 22:30 | 21:30 | 18:30 | Último checkpoint HN (se ainda na front page — responder threads ativos) | HN |

### Notas de timing
- **HN:** submeter às **10:00 BRT = 09:00 ET** (peak window; original 07:15 BRT / 06:15 ET era sub-ótimo — análise completa em `docs/launch-hn-submission-final.md §5`). Não submeter durante fins de semana ou feriados EUA.
- **Twitter:** 07:00 BRT = 06:00 ET = janela matinal costa leste, antes do rush de 09:00 ET.
- **PH:** votações pesam mais nas primeiras 6h. Votos de 00:01–06:00 PST são críticos para ranking diário.
- **Reddit r/ML:** postar logo após HN para efeito de cross-canal. Incluir flair correto (Research, Project).

---

## §3 Planos de crise

| Cenário | Resposta |
|---|---|
| arXiv submission rejeitada pré-lançamento | Adiar 24h. Diagnosticar LaTeX (`pdflatex --halt-on-error`). Reagendar lançamento Qui 06-04. Atualizar PH schedule. |
| arXiv ID não chegou até 23h Ter 06-02 | Checar `https://arxiv.org/find/` + e-mail de confirmação. Se preso em hold, lançar sem badge arXiv + adicionar link depois. |
| HN Show HN post flagado/removido | Aguardar 30min (às vezes auto-unflag). Resubmeter com título mais neutro. Contatar mods via `hn@ycombinator.com`. Não repostar no mesmo dia. |
| HN Show HN preso em página 2+ (sem tração) | Postar comment substancial no próprio thread com benchmark highlight. Não votar em si mesmo. Compartilhar link em comunidades técnicas relevantes. |
| PH submission bloqueada | Verificar que Toto está listado como maker (não precisa de hunter). Checar se domínio/produto já existe no PH. Suporte: `https://www.producthunt.com/contact`. |
| PH com poucos votos nas primeiras 2h | Compartilhar link PH no Twitter thread (T9 pode incluir link PH). Não comprar votos — PH detecta e penaliza. |
| Twitter thread atacado por bots/trolls | Silenciar conversa específica. Fixar thread no perfil. Responder apenas comentários substantivos. |
| Reddit auto-moderado (post removido silenciosamente) | Checar mod log ou DM moderadores explicando contexto FOSS + acadêmico. Oferecer remover se violar regras. Tentar r/programming como alternativa. |
| VPS cai durante o lançamento | Cron de healthcheck (PR #164) alerta em 15min. Rollback: redirecionar demo para screenshots estáticos (ou Loom gravado). Postar update no HN thread: "Demo momentaneamente offline — fix em andamento". Não apagar post HN. |
| Bug crítico descoberto pós-lançamento | Postar update transparente no HN thread ("Update: bug identificado, fix em progresso"). Abrir PR com fix. Nunca apagar nem editar post original. Considerar release de patch v3.7.1. |
| Q4 números contestados (community challenge) | Linkar para arXiv com metodologia completa. Disponibilizar eval harness e dataset. Responder com dados, não com defesa emocional. |
| Regressão de performance descoberta no eval pré-launch | Ver §6 — condições de cancelamento. Se regressão <2%, lançar com caveat no post. Se >5%, adiar. |

---

## §4 Verificação final de assets (Ter 2026-06-02 18h BRT)

> Esta checklist é a última barreira antes de dormir. Se algum item estiver vazio, **não dormir** até resolver.

### README
- [ ] Hero section: título + tagline + badge arXiv + badge GitHub + badge license
- [ ] Demo GIF CLI (asciinema) embutido e carregando
- [ ] Demo GIF F10 dashboard embutido e carregando
- [ ] Números Q4 na seção de resultados: +18.8% nDCG@10, MRR, latência p50/p95
- [ ] Link arXiv correto (testar em aba anônima)
- [ ] Link `/api/answer` ou demo endpoint documentado

### Blog post
- [ ] Versão HTML gerada (se postando no site pessoal)
- [ ] Todos os números Q4 presentes e consistentes com arXiv
- [ ] arXiv link embutido no texto
- [ ] Meta tags OG (title, description, image) configuradas para share preview

### Twitter
- [ ] Thread T1–T9 salva como rascunho (ou em arquivo local `docs/launch-social-copy.md`)
- [ ] Cada tweet dentro do limite de 280 chars (verificar com counter)
- [ ] T1 tem hook forte + número destaque
- [ ] Último tweet tem link para repo + arXiv

### HN Show HN
- [ ] **Title + body + maker comment FINAL** lidos em `docs/launch-hn-submission-final.md` (§1, §3, §4) — copy-paste ready
- [ ] **Timing:** 10:00 BRT (09:00 ET) — NÃO 07:15 BRT (ver análise §5 do mesmo doc)
- [ ] arXiv link preenchido no maker comment antes de postar (aguardar ID chegar Ter 06-02 noite)
- [ ] Title escolhido: `Show HN: nox-mem – SQLite-based hybrid memory for LLM agents (FTS5 + vec0 + RRF)`
- [ ] Body tem: O que é, motivação, stack, benchmark highlight honesto (LoCoMo +40% com caveat), link arXiv
- [ ] Sem hipérboles ("melhor do mundo", "revolucionário") — HN penaliza

### Reddit r/MachineLearning
- [ ] Post body salvo em arquivo local
- [ ] Flair selecionado (Research ou Project)
- [ ] Abstract do arXiv embutido (r/ML aprecia contexto técnico)
- [ ] Link para repo + arXiv + blog (se houver)

### Product Hunt
- [ ] Título, tagline, descrição curta, descrição longa salvos no draft PH
- [ ] Gallery: mínimo 3 imagens/GIFs (screenshots CLI, F10 dashboard, diagrama de arquitetura)
- [ ] Primeiro comentário do maker escrito (aparece logo após go-live — contexto adicional + convite para feedback)
- [ ] Agendamento confirmado: **Wed 2026-06-03 00:01 PST**

### Trendshift
- [ ] URL do repo anotada (submissão é simples — link + categoria)

---

## §5 Retrospectiva pós-lançamento (Qui 2026-06-04 manhã)

### Métricas a compilar

| Métrica | Alvo mínimo | Real |
|---|---|---|
| HN pontos | >50 | — |
| HN posição máxima | Top 30 Show HN | — |
| PH votos | >100 | — |
| PH posição | Top 5 do dia | — |
| Twitter impressões (thread) | >10k | — |
| Twitter retweets | >50 | — |
| Reddit upvotes (r/ML) | >50 | — |
| Repo stars Δ (vs pré-launch) | >100 em 24h | — |
| Issues abertas (feedback) | — | — |

### Checklist retrospectiva
- [ ] Compilar métricas acima em arquivo `docs/launch-retrospective-2026-06-04.md`
- [ ] Listar anomalias (HN flagged, bug reports, críticas recorrentes)
- [ ] Listar feedback positivo acionável (features pedidas, integrações sugeridas)
- [ ] Decidir próximos passos: follow-up posts, talk submissions, resposta a críticas técnicas
- [ ] Atualizar `docs/HANDOFF.md` com estado pós-lançamento
- [ ] Se repo stars > alvo: avaliar momentum para GTM Phase 2 gate

---

## §6 Condições de cancelamento (stop-the-launch)

**Cancelar ou adiar o lançamento se QUALQUER condição abaixo for verdadeira:**

| Condição | Threshold | Ação |
|---|---|---|
| arXiv submission ainda falhando | Seg 2026-06-01 EOD | Adiar para data sem arXiv (só GitHub + blog) OU esperar até Qui 06-04 |
| Regressão nos números Q4 | >5% abaixo de +18.8% nDCG@10 vs baseline | Adiar. Investigar causa. Não lançar com claim errado. |
| Finding de segurança crítico no código | CVSS ≥ 7.0 descoberto no audit FOSS hygiene | Corrigir antes de lançar. Não há timeline que justifique lançar com CVE conhecido. |
| VPS instável na semana anterior | 3+ outages em 7 dias pré-launch | Adiar até resolver infra. Demo offline no dia de lançamento é fatal para credibilidade. |
| arXiv ID não disponível até 23h Ter 06-02 | — | Lançar sem badge arXiv (aceitável como contingência — anunciar que submission está em revisão) |

### Protocolo de adiamento
1. Não deletar nenhum rascunho/draft
2. Se PH foi agendado: cancelar o schedule na plataforma (não há penalidade para cancelamento)
3. Postar note no próprio calendário com nova data
4. Reagendar para próxima Qua (06-10) ou Qui (06-04) se adiamento mínimo

---

## §7 Referências rápidas (para o dia)

| Recurso | Link/Comando |
|---|---|
| arXiv submission | `https://arxiv.org/submit/` |
| HN Show HN | `https://news.ycombinator.com/submit` |
| Product Hunt dashboard | `https://www.producthunt.com/dashboard` |
| Reddit r/ML | `https://www.reddit.com/r/MachineLearning/submit` |
| Reddit r/LocalLLaMA | `https://www.reddit.com/r/LocalLLaMA/submit` |
| Trendshift | `https://trendshift.io/` |
| VPS health check | `curl http://127.0.0.1:18802/api/health \| jq .vectorCoverage` |
| VPS IP atual | 187.77.234.79 (PR #164) |
| Backup snapshot dir | `/var/backups/nox-mem/pre-op/` |
| Social copy doc | `docs/launch-social-copy.md` |
| Blog post draft | `docs/launch-blog-v0-draft.md` |
| Demo plan | `docs/launch-demo-plan.md` |
