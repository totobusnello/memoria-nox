# `linked` — o que dá para construir, medido

> **2026-08-15.** Exploratório, pré-tratamento, read-only. Não altera número
> travado. Script: `link_feasibility.mjs`. Existe porque a medição de dose
> (`dose_reach.mjs`) expôs que o termo `linked` do §2 nunca foi definido.

## 1. Não há chave de junção — e não é oversight recuperável

| | |
|---|---|
| sessões distintas nos episódios | 789 |
| UUIDs de sessão em `source_file` de chunks | 48 |
| **interseção** | **0** |
| chunks vindos do action-archive | **0** |
| chunks com `episode` em `metadata` | **0** |

Os UUIDs de sessão dos episódios são do **Claude CLI** (`/root/.claude/projects`);
os dos chunks são do **OpenClaw** (`sessions/<agente>/…`). Namespaces distintos.
Não há link latente: o link tem de ser **construído**, e como se constrói decide
quais chunks recebem o boost — ou seja, decide o tratamento.

## 2. As três construções, e por que duas caem

**A — casar chunks existentes por assinatura (`sig()`), textualmente.**
Rejeitada, e pelo argumento que o próprio documento já registra: chunks não têm
assinatura, então o casamento seria FTS sobre os tokens da assinatura. Isso mede
**adjacência de tópico**, não vínculo episódico — exatamente o defeito pelo qual
a coluna `pain` foi proibida como wiring (`Do not wire this to the existing pain
column`, §9-4; memória `feedback_pain_column_is_topical_not_episodic`). Pior:
transforma a heurística de casamento num parâmetro livre do tratamento.

**C — mudar os pesos da salience para chunks de episódio** (ex.: isentar da
penalidade de `access_count`). Rejeitada: o braço de controle é *"production
brief policy"*. Mexer na fórmula para o estudo funcionar contamina o controle e
destrói a comparação que o desenho inteiro existe para fazer.

**B — escrever a memória a partir do episódio adjudicado**, com `episode_id` no
`metadata`, e aplicar `W_OUTCOME × severity` sobre ela. O vínculo passa a ser
**por construção**: auditável, sem heurística, sem chave inventada. É a única que
sobra — e é também a que corresponde à tese do paper (memória de falhas evita
repeti-las), enquanto reponderar chunks pré-existentes que nunca foram sobre os
episódios não transmite informação de falha nenhuma.

## 3. B funciona? Medido

Chunk escrito como `chunk_type='lesson'` → importance **0,90**
(`IMPORTANCE_BY_TYPE`), `access_count = 0`, `pain` = severidade.

| corte | valor |
|---|---|
| slot 10 do pool principal | **0,8524** |
| fresh slot 2 (`freshSlots = 2`) | **0,7342** |

| sev | share dos failures | base | w=0,5 | w=1,0 | w=2,0 | entra? | `w` mínimo |
|---|---|---|---|---|---|---|---|
| **S1** | **69,73%** | 0,6700 | 0,6754 | 0,6808 | 0,6915 | nunca | **6,0** |
| **S2** | **29,62%** | 0,6950 | 0,7058 | 0,7165 | **0,7380** | só a `w=2,0` | 1,8 |
| S3 | 0,58% | 0,7200 | **0,7361** | 0,7522 | 0,7845 | a partir de `w=0,5` | 0,4 |
| S4 | 0,08% | 0,7450 | — | — | — | já entra sem dose | 0 |

**Três leituras, nesta ordem de importância:**

1. **O slot principal é inalcançável para conteúdo novo em qualquer dose travada.**
   O melhor caso fica 0,0214 abaixo do corte. Toda a ação do tratamento acontece
   nos **2 coverage slots**, não nos 8 principais.
2. **A dose decide, e decide onde tem massa.** Em S2 — 29,62% dos failures — só
   `w = 2,0` entra. Isso é um gradiente dose-resposta real, com 30% do corpus
   como população tratada efetiva. O braço `w` não é rótulo.
3. **A falha modal está fora de alcance.** S1 é 69,73% dos failures e precisaria
   de `w ≈ 6,0` — três vezes o topo da faixa travada `{0,5 · 1,0 · 2,0}`.
   Estendê-la seria **emenda**, não cláusula de escape: `w` foi travado em
   29/07 com a faixa explícita.

## 4. O que isto obriga a declarar

- A **população tratada efetiva é ~30% dos failures** (S2+), não todos. Isso
  aperta ainda mais o efeito detectável e pertence ao abstract, não a
  limitações.
- O efeito de `w` é **binário na fronteira do fresh slot** para S2, não
  contínuo. A regra de leitura dose-resposta pré-comprometida no §3 tem de ser
  reescrita nesses termos.
- `w ≈ 6,0` como o que seria preciso para alcançar S1 fica **registrado agora**,
  antes de qualquer dado de braço, para que estendê-lo depois seja visivelmente
  uma emenda e não um refinamento.

## 5. O que continua aberto

A construção B ainda precisa de decisões que **não** são medição: quem escreve o
chunk (o próprio pipeline de adjudicação?), quando (fim do epoch? imediato?),
com que texto, e se a escrita acontece nos **dois** braços com só o boost
diferindo — que é a única forma de o contraste isolar a ponderação em vez de
confundir escrita com ponderação. Essa última é a mais importante e é decisão de
desenho, não de número.
