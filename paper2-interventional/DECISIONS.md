# Martelo — Decisões travadas (Paper 2)

> Convergência de 3 vozes adversariais (Codex/Kimi/GLM) + síntese. Detalhe das vozes em `REVIEWS.md`.
> Data: 2026-07-05. Atualizado 2026-07-12 (rota do desenho) e 2026-07-25 (modelo de independência).

## ✅ Modelo de independência — **estrutural, sem pessoas** (Toto, 2026-07-25)

Contexto: o desenho v0.2 exigia **auditor externo** + **data monitor independente** (pessoas nomeadas, distintas). Custo real: lead time de convite, dependência de terceiro para operar o estudo, e risco de o projeto travar num "não".

**Decisão: nenhum humano nos dois papéis.** Cada garantia que eles davam vira mecanismo verificável:

| Garantia | Antes (pessoa) | Agora (mecanismo) |
|---|---|---|
| Randomização não escolhida a dedo | monitor gera e guarda a seed | **beacon público `drand`** — round que não existe no momento do registro; qualquer um recomputa |
| Parada não-interessada | monitor decide o abort | **regra numérica congelada**, arm-blind, que derruba o estudo inteiro (nunca um braço) |
| Regras fixadas antes dos dados | auditor assina pré-unblinding | **hash dos veredictos publicado ANTES do join** com os rótulos de braço (ordering proof) |
| Exclusões arm-blind | auditor verifica | **exclusões são código** que não tem o artefato de rótulos no escopo — lê-se o commit |
| Adjudicação sem viés de braço | humanos cegos | **painel de LLMs de famílias de treino distintas**, prompt hasheado, maioria + mediana, Fleiss' κ |

- **Claim causal PRESERVADO.** A identificação causal vem da randomização, não da supervisão. Seed derivada de beacon é *mais* difícil de manipular que seed guardada por pessoa. O §1-H1 fica como está.
- **Limitação declarada (não escondida):** ninguém independente observa a execução em tempo real; a verificação é **post-hoc e aberta**, não *ex ante* e delegada. Some-se a perda do desempate humano em casos de fronteira (tratado mecanicamente em §4.1).
- **Ganho colateral:** sem sujeitos nem contribuintes humanos, a seção de ética simplifica e a isenção de IRB fica direta.
- **Rejeitado:** convidar auditor "leve" (2h de sign-off) — Toto optou por zero dependência externa, 2026-07-25.

Detalhe completo: `PREREG-DRAFT.md` §0b (+ §2 seed/blinding, §3 abort, §4.1 painel, §5 exclusões, §7 COI).

## ✅ Rota do desenho A/B — **2-lite** (Toto, 2026-07-12)

Contexto: o GLM challenge do `PREREG-DRAFT.md` v0.1 (ver `REVIEWS-PREREG.md`) mostrou que cluster agente×bloco + washout **não** resolve o SUTVA — carry-over via writes compartilhados + contaminação cross-agent simultânea.

**Decisão: Route 2-lite** — crossover com **epochs fleet-wide** (os 6 agentes trocam de braço juntos; nenhum instante com braços misturados) + **serving-side snapshot** por epoch (brief servido do snapshot do início do epoch; writes seguem no store vivo, intocados). Carry-over residual (conteúdo do snapshot moldado pelo braço anterior) tratado por co-estimativas pré-commitadas (A→B-restricted, lag-1, bounds).

- **Rejeitadas:** Rota 1 (conservadora) abre mão do claim causal que o paper precisa pra COLM full/D&B — fica como **fallback documentado** se o snapshot for inviável operacionalmente; Rota 3 (análise formal sobre o desenho velho) deixa F1/F4 indefensáveis (veredito GLM); Rota 2 full (store per-arm + flush) custa muito ops pra pouco ganho sobre a 2-lite.
- **Pré-requisito de engenharia criado:** mecanismo de serving-side snapshot no nox-mem, implementado e validado em shadow antes do pilot (item §9.3 do PREREG-DRAFT).

## ✅ Spine (confirmado pelas 3 vozes)

Representação ≠ decisão. Retrieval mede o primeiro; o valor da memória do agente está no segundo. **É o paper.** A intuição é "forte e genuinamente subexplorada" (consenso das 3 vozes).

## ✅ Framing — a regra mais importante

**NÃO** usar "causal/interventional" como claim guarda-chuva. Foi o alerta mais forte (Codex + GLM):

- Só o **braço A/B randomizado** é interventional. O benchmark de traces + o outcome-weighting são **observacionais retrospectivos**.
- Chamar tudo de "causal" = **inflation terminológica → desk-reject** (area chair do COLM).
- **Regra:** reservar "causal" exclusivamente pro braço randomizado. No resto: *"decision-relevant"*, *"outcome-associated"*, *"behaviourally validated"*.
- **Methods em duas camadas explícitas:**
  - *Benchmark contribution:* retrospective log study (n=…, período=…).
  - *Causal claim:* only for the randomized withholding arm (n=…, pre-registered primary outcome).

## ✅ Título (working — nome exato não travado)

Candidatos, todos evitando "causal" no headline como claim absoluto:

- *Interventional Memory: Decision-Relevant Retrieval from Live Multi-Agent Traces*
- *Retrieval Metrics Can't See What Agent Memory Is For* (gancho do gap de avaliação)

Pain aparece como **motivação/primitivo**, nunca no título.

## ✅ Venue

- **COLM 2027** — alvo primário (interactions / multi-agent / evaluation encaixam).
- **NeurIPS D&B 2027** — se o artefato público for sério (dataset + código).
- **EMNLP 2027** — fallback, moldura *negative-finding + resource*.

## ✅ Onde o paper se ganha

**80% é metodologia, não escrita.** Ver `METHODOLOGY.md`. A prioridade zero é blindar o desenho (pré-registro + SUTVA + auditoria + artefato), não escrever melhor.

## ❌ O que rejeitamos explicitamente

- **Pain-weighting como mecanismo-protagonista** — beco morto do Paper 1 (insignificante). Vira primitivo, não headline.
- **"Causal" sem randomização** — hype; abate no desk-reject.
- **A/B ingênuo on/off** sem tratar interferência cross-agent — quebra o estimador (ver SUTVA em `METHODOLOGY.md`).
