# Taxa de episódios por epoch — medida sobre o action archive

> Fecha o item 3 do bloco de 18/08 ("medir a taxa real de episódios adjudicados
> por epoch"). Insumo da emenda.

## Medição

`extract_episodes.py --raiz /var/lib/nox-mem/action-archive`, **sem** filtro,
2026-08-19. Saída fora do repo (`/tmp/episodios-full-20260819.jsonl`,
sha256 `a467bf83…`).

| | episódios | por epoch (24 h) |
|---|---|---|
| corpus-piloto (`universo-combinado.jsonl`, 30 epochs) | 9.579 | **319** |
| archive, janela 2026-07-12 → 08-19 (34 dias) | 11.799 | **347** |
| **10 dias completos mais recentes** | — | **309,4** |
| projeção do §9 (`r̂` 29,838403 × T 12 h) | — | ~358–396 |

**A projeção está ~15% acima do medido.** Discrepância normal, não defeito — e o
piloto (319) e o presente (309) concordam entre si, o que é o achado que importa:
**o volume da frota não mudou** entre a janela do piloto e agora.

## ⚠️ Um erro meu, e a classe dele

A primeira medição rodou com `--only-errors` e deu **1.107** episódios. Comparei
esse número contra os **9.579** do corpus-piloto — que **não** tem esse filtro — e
concluí um gap de "12 a 28×", com consequências dramáticas para censo e potência.

**Era artefato do meu próprio filtro.** `universo-combinado.jsonl` tem 9.579
episódios dos quais 698 (7,3%) são `is_error`; o archive tem 11.799 dos quais
1.107 (9,4%). Comparação correta: 11.799 vs 9.579.

Mesma classe de [[feedback_correct_arithmetic_can_come_from_an_inapplicable_formula]]:
a aritmética estava certa, as duas quantidades não eram a mesma coisa. O sinal que
eu tinha e ignorei: o output do script imprime `emitidos` **e** `is_error`
separadamente — a informação estava na tela.

## O que o número faz com a decisão de painel do §9

O §9 reduziu o painel porque projetou um censo de 5 painelistas como inviável.
A aritmética, nas três bases:

| base | episódios totais | janelas de quota Moonshot (~100/janela) |
|---|---|---|
| §9 original (96 epochs × 396) | 38.016 | 380 |
| §9 corrigido (234 epochs × 396, o fator 2,4× que o próprio doc declara) | 92.664 | 927 |
| **medido (234 × 309,4)** | **72.400** | **724** |

Duas leituras, e as duas precisam ser ditas porque isoladas enganam:

- contra o **original**, o volume medido é **1,90×** — o `~38.000` era
  subestimativa, exatamente como o doc já admite;
- contra o **corrigido**, é **0,78×** — o fator 2,4× é ~22% conservador.

**A conclusão do §9 fica de pé e mais forte:** 724 janelas de quota continua
inviável para censo de 5 painelistas. A decisão de painel reduzido não depende de
qual das três bases se usa.

## Sinal colateral: `is_error` caiu, o volume não

| dia | total | `is_error` |
|---|---|---|
| 08-06 | 353 | 56 |
| 08-07 | 114 | 46 |
| 08-12 | 243 | 11 |
| 08-16 | 197 | **3** |
| 08-17 | 329 | 17 |
| 08-18 | 172 | 5 |

O total oscila em torno de ~300/dia e a fração de erro caiu de ~16% para ~2-5%.
Isso é sinal real, não instrumentação: mesma extração, mesma raiz. **Não** entra em
nenhum número travado, mas é candidato a covariável de tempo e vale declarar —
uma taxa de falha que cai ao longo do estudo confunde-se com efeito de tratamento
se os braços não estiverem balanceados no calendário (eles estão: a
estratificação é calendar-half × weekday/weekend).

## Cobertura do corpus — verificada

- **Os 7 agentes da frota estão no archive** (`agents-{nox,atlas,boris,cipher,forge,lex,gordon-gekko}`).
  ⚠️ Um primeiro check meu disse que **todos** estavam ausentes: o campo é
  `agents-nox`, não `nox`.
- **O stream vive no endereço do failover:** 434 de 435 `tool_use` desde 18/08 em
  `.claude-nuvini-team`, não em `.claude`. O archive está em paridade (435), logo
  o coletor **não** está cego — ver
  [[feedback_action_corpus_instrumentation_is_provider_bound]].

## O que ainda falta para λ

Isto mede o **denominador** (episódios candidatos por epoch). λ, no sentido que a
banda de dose precisa, é a taxa de episódios **adjudicados como falha** por epoch —
o que exige uma rodada de painel sobre uma janela recente. Bounded, não operação
contínua.
