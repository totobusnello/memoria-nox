# CHECK-G — verificação mecânica independente do manuscrito após a parte G

Data: 2026-10-04. Alvo: `paper/paper-tecnico-nox-mem.md` (191.801 bytes, md5 `97041d76…`).
Bases de comparação: `scratchpad/applyG/` (estado imediatamente anterior à parte G),
`scratchpad/applyF/` (anterior à parte F) e `scratchpad/v102/`. Não confiei no
`APPLY-REPORT-G.md`: cada afirmação abaixo vem de script ou leitura direta do arquivo.
Nenhum comando git. Nada publicado. Ninguém contatado. Nenhuma edição no manuscrito.
Efeito colateral declarado: rodar `paper/measurement/recompute-rc4-categories.py` reescreveu
`paper/measurement/out/recompute-rc4-categories.json` (saída determinística, `ok — §6.4 reproduced`).

## Veredito curto

- `claims_check.py`: `ok — 21 guardas passaram; 6 alegações retratadas com lista de invalidação` (exit 0).
- `claims_check_mutation_test.py`: `ok — 49 mutações mordidas com o marcador certo, controle negativo silencioso` (exit 0).
- Referências §: **0 sem destino**; todas as §S apontam para cabeçalhos existentes nos suplementos.
- Footnotes: 72 definidas, 72 usadas, nenhuma órfã, nenhuma duplicada.
- Abstracts curtos (`abstract.md` §2, `arxiv-metadata.txt`, `techrxiv-metadata.md`): **idênticos byte a byte**, 1.902 caracteres, 281 palavras, ASCII; substância bate com o abstract do manuscrito.
- Paridade numérica F+G: nenhuma medição mudou; toda remoção é errata, número sem lastro, ou mudança de lugar (para `§S6.8`/suplemento). As três trocas de valor da parte F (LoCoMo) conferem com o artefato.
- **Mas há defeitos**: dois cabeçalhos que somem no PDF (já estavam na v1.0.2 depositada), um parágrafo engolido por um bullet, um rótulo errado de knob (desde a v1.0.2), uma lista de "três" gaps com dois itens, e resíduos de linguagem. Lista completa abaixo.

## 1. Referências §, Table, Figure

Script (`scratchpad/checkG/refs.py`): extraiu todo `§x.y`, `§x.y–§x.z` e `§Sx.y`, comparou com os
cabeçalhos do manuscrito e dos dois suplementos. Resultado: nenhum destino inexistente; nenhuma
referência sobrevivente a §5.8.6, §5.7.4 ou ao antigo §5.8.4 sem prefixo S. As 5 referências a §5.8.5
(linhas 216, 641, 849, 1245, 1356) caem em "Honest limitations and open work", que contém os
bullets citados (MemOS não re-executado, l. 922; latência do Zep sem percentil, l. 919). §S3.5, §S5.1.4,
§S5.1.11, §S5.1.12, §S5.5.2–§S5.5.8, §S5.7.4 e §S6.8 existem nos suplementos com o conteúdo prometido
(conferi S5.5.4: tabela com "~8–9%" e a projeção "~12.07%").

Tabelas: Table 1 (l. 48) e Table 2 (l. 1164) existem; "Table 3/4/5" referem-se a tabelas de papers
externos (Beam Retrieval, EverMemBench), correto. Não há figuras.

Desencontros de conteúdo achados: ver D5, D15, D16, D17.

## 2. Footnotes, seções vazias, cabeçalhos órfãos

- Footnotes: limpo (72/72).
- Nenhuma seção vazia. Stubs curtos e intencionais: §5.1.4, §5.3.3, §5.5.3, §5.8.3, §5.1.11–5.1.12.
- **Cabeçalhos que o pandoc não reconhece** (sem linha em branco antes): l. 648 `### 5.2` e
  l. 1239 `#### F3`. Confirmado no `build/paper-tecnico-nox-mem.tex`: aparece como texto literal
  `\#\#\# 5.2 Classical multi-hop QA…` (l. 2289) e `\#\#\#\# F3 ---…` (l. 5068). Presente também na
  v1.0.2 (o `.tex` da v102 tem 2 ocorrências de `\#\#`), ou seja, o PDF depositado não tem o
  cabeçalho da §5.2. Ver D1.
- Parágrafo engolido: l. 985 (`**Zep was a gap of this list…**`) vem colado ao bullet do Letta; no
  `.tex` (l. 3701) virou parte do bullet. Ver D2.

## 3. Paridade numérica

Script (`scratchpad/checkG/nums.py`): conta tokens numéricos (com %, pp, ms, MB, GB, ×) nos dois
textos e lista os que sumiram ou apareceram.

### applyG → atual (parte G): 36 sumiram, 3 apareceram

| Sumiu | Onde estava | Classificação |
|---|---|---|
| 2,375 · 95.7% · 9.83 · 0.4446 · +0.011 · 0.068 | §6.3.2 (a), réplica do Mem0 | Remoção de número sem lastro (script/saída da réplica não retidos); substituído por frase declarando isso |
| 0.48 | §5.5.2, Fisher p retirado | Errata movida ao CHANGELOG |
| 15× | §8 | Errata (número sem suporte) |
| 769 · 2,307 | §5.1.3 | Errata (não reverificável) |
| 50.40% · 50.21% | §5.3.2 | Errata (tabela retirada na v1.0.3 E) |
| 5.7 ms · 706 ms · 70.7k | §5.7.1 correção | Valores retirados encurtados; "2.9 ms"/"653 ms" seguem citados só como retirados |
| 667× · 769× | §5.7.2 | Razão retirada (denominador é modelo, não preço) |
| 50 MB | footnote nox-mem-rss | Histórico de estimativa removido |
| ~800 MB · ~1.5 GB · ~1.2 GB · ~4 GB+ | Table 2 (§6.8) | Movidos para §S6.8, rotulados como estimativa do autor; confere valor a valor com a tabela antiga |
| +22.12 pp, ~10 pp, 84.44, 85.04, 11.60, 12.12, 16.72 (ocorrências) | caixa de headline do §5 | Condensação; os valores seguem nas tabelas (§5.1.10, §5.2.1, §5.2.2) |
| +1.5 pp | §5.8 (gate "NO-REPLICATE") | Frase removida; segue no suplemento |
| 404 | footnote everos-stack | "HTTP 404" → "no longer resolves" (redação) |

Apareceram: "2.9 ms"/"653 ms" (reformatação da errata) e "[−0.5, +0.5]" no novo parágrafo
"Boost composition" (§4.1, l. 438). Conferi a fórmula contra `staged/1.7a/edits/search.ts`
(l. 19–21: deltas `(factor − 1)` somados em `boostSum`; l. 421/540: `score = baseScore * (1 + boostSum)`;
l. 335: salience delta limitado a ±0,5). Descrição correta; não é medição.

### applyF → applyG (parte F): 7 sumiram

| Antes | Depois | Verificação |
|---|---|---|
| LoCoMo single-hop hit@10 71.40% / adj-2 84.13% | 80.36% / 92.03% | `RESULTS-FULL-1986q.json` single_hop 0.80357; `RESULTS-LOCOMO.md` l. 200 |
| LoCoMo temporal 68.94% / 82.31% | 77.96% / 84.74% | temporal 0.77955; `RESULTS-LOCOMO.md` l. 201 |
| LoCoMo overall adj-2 87.10% | 87.44% | `RESULTS-LOCOMO.md` l. 191 |
| HotPotQA "~11.7 points" | 11.67 / 11.07 | aritmética 85.04−73.37, 84.44−73.37 |
| "+2.8 pp" (date normalization) | +15.94 pp (session-date injection) | `RESULTS-LOCOMO-SOTA-PUSH.md` l. 29, 77; `temporal_norm_enabled: false` no JSON |
| LightRAG ~1 GB / ~20 s | "not estimated" | suplemento, errata (17): backends em processo |

Os valores antigos de LoCoMo não batiam com nenhum artefato; os novos batem. É correção de
proveniência, não medição alterada.

### v1.0.2 → atual

147 tokens sumiram e 292 apareceram, acumulando as partes A–G. Re-auditei de forma independente
só F e G (acima). As partes A–E dependem de `NUMBER-PARITY-v102-to-v103E.md`, que **não** reverifiquei.

### Proveniências conferidas

`docs/audits/2026-05-19-salience-distribution-audit.md` contém 99.7%, 90.67% e 99.76%; existem
`RESULTS-PATHB-FULL.md`, `RESULTS-PHASEG-5BATCH.md`, 5 arquivos `analysis-phase{D,3}-batch-*`,
`recompute-rc4-categories.py` e a saída dele; `RESULTS-PRODUCTION-SOTA.json` traz KG p50 2.53 / p95 6.14 /
p99 7.87 (n=120), híbrido 529.21 / 697.7 / 744.24, RSS 399/423/15, `mem0_cloud_overage` 0.001 e
1.3e-06/query. A página de preços do Mem0 (lida por mim em 2026-10-04 via firecrawl) mostra
Free / US$19 / US$249 / Enterprise e "usage-based pricing" sob consulta, sem preço por chamada:
confere com §5.7.2.

## 4. Linguagem de produto e rótulos internos

Zero: moat, GTM, launch, pillar, effectively free, silent killer, WIN, PASS, FAIL, NO-REPLICATE,
DOCUMENTED_INSUFFICIENT, INDETERMINATE, CLEAN, Lab Q, Wave 2, F10, pre-registered/pre-registration,
`\bD[0-9]{1,2}\b`. "Q4" só aparece no nome de arquivo `specs/2026-05-23-Q4-…` (ok). "cheaper" (l. 154)
é "the cheaper half" em sentido técnico (ok). Restos: D7–D13.

## 5. Abstracts

| Arquivo | Caracteres | Palavras | ASCII | Igual ao `abstract.md` |
|---|---:|---:|---|---|
| `paper/abstract.md` §2 | 1.902 | 281 | sim | — |
| `paper/arxiv-metadata.txt` | 1.902 | 281 | sim | sim |
| `publication/techrxiv-metadata.md` (bloco recuado) | 1.902 | 281 | sim | sim |

Substância bate com o abstract do manuscrito (3.283 caracteres): 4+1 sistemas, split 0.469/0.426,
rc4 0.526/0.406 e 0.495/0.441, quatro confounds, EverOS 0.646 vs 0.501 com cross-encoder não medido,
Zep terceiro, 63.28% / +4.01 pp / 72.61%, F_MH 6.02% vs 10.84%. Nenhum número no curto que não esteja
no longo. Defeitos nos metadados ao redor: D18–D20.

## 6. Scripts

```
$ python3 paper/claims_check.py
ok — 21 guardas passaram; 6 alegações retratadas com lista de invalidação      (exit 0)
$ python3 paper/claims_check_mutation_test.py
ok — 49 mutações mordidas com o marcador certo, controle negativo silencioso   (exit 0)
```

Nenhuma das guardas pega D1–D4: são defeitos de renderização e de conteúdo que estão fora do que as
mutações exercitam.

## Defeitos — citação exata e correção

| # | Sev. | Origem | Citação | Problema | Correção |
|---|---|---|---|---|---|
| D1 | alta | v1.0.2 | l. 647–648: `…is stated in §5.4.` ↵ `### 5.2 Classical multi-hop QA…`; l. 1238–1239: `…an automated gate. ` ↵ `#### F3 — Per-method benchmark…` | Sem linha em branco antes do cabeçalho; o pandoc emite `\#\#\# 5.2` como texto. O PDF (inclusive o da v1.0.2) não tem o cabeçalho da §5.2 nem o do F3 | Inserir uma linha em branco antes das l. 648 e 1239; tirar o espaço final da l. 1238 |
| D2 | média | v1.0.2 | l. 984–985: `…in this configuration.` ↵ `**Zep was a gap of this list and no longer is.**` | Continuação preguiçosa: o parágrafo do Zep vira parte do bullet do Letta (`.tex` l. 3701) | Linha em branco antes da l. 985 |
| D3 | média | v1.0.2 | l. 979: `The 2026-06-15 run hit three:`; l. 987: `The entry above describes the version that existed on 2026-06-15.` | Só dois bullets (Zep, Letta); o bullet do EverMind-AI a que "the entry above" se refere não existe | Repor um bullet do EverMind-AI (barreira de 2026-06-15: serviço HTTP, credenciais OpenRouter + DeepInfra, `pip install -e` externo), ou trocar "The entry above" por "This paragraph" e o caput por "hit three (Zep, Letta, EverMind-AI):" |
| D4 | média | v1.0.2 | l. 593: `Three retrieval-augmentation knobs (KG expansion, adjacent-chunk inclusion, multi-query fan-out)` | O knob "AC" é o adaptive query classifier (suplemento S5.1.8.2; tabela §5.5.5 "AC threshold=5"), não adjacent-chunk inclusion. "AC" nunca é expandido no corpo | "(KG path expansion, an adaptive query classifier (AC) that routes queries to cross-encoder rerank, and multi-query fan-out (MQ)); MAP is reported with the combinations in §5.1.9" |
| D5 | baixa | ≤ applyG | l. 589 (final da §5.1.7): `How these knobs combine (Wave B and Wave C) is reported in §5.1.9…`; l. 587–588 duas linhas em branco | Antecedente errado: §5.1.7 trata do rerank; os knobs só aparecem na §5.1.8, que já remete à §5.1.9 | Apagar a frase, ou movê-la para o fim da §5.1.8; deixar uma linha em branco só |
| D6 | baixa | G | l. 532 `(§S5.1.4.)`, l. 771 `(§S5.5.2.)`, l. 775 `(§S5.5.3.)`, l. 779 `(§S5.5.4.) Headline:` | Ponto final dentro do parêntese | `(§S5.1.4).` etc. |
| D7 | baixa | ≤ v1.0.2 | l. 727, cabeçalho da tabela da §5.4: `… \| Verdict \|` | Rótulo interno remanescente | "Position vs references" ou "Note" |
| D8 | baixa | ≤ applyG | l. 884: `deprecated for any ship/reject decision` | Jargão de produto | "deprecated for any decision to enable a change by default" |
| D9 | baixa | ≤ applyG | l. 888: `(1.27× overstatement, still a win but a different narrative)`; `would have been overclaimed in print` | Tom de relato interno | "(1.27× overstatement; the 5-batch margin remains positive)"; "would have overstated both effects" |
| D10 | baixa | G / anterior | l. 1184: `on the autonomy axis`; l. 1156: `an internal product-planning gate` | Resíduo do pilar "Autonomy" e de planejamento de produto | "operationally"; "an internal planning gate" |
| D11 | baixa | anterior | l. 873 `honest caveats`; l. 902 `Honest scope…`; l. 915 `Honest limitations…`; l. 973 `Split result — honest reading`; l. 488 `honest limitations` | Autoelogio em títulos | "Methodology, 5-batch protocol, and caveats"; "Scope of…"; "Limitations and open work"; "Split result" |
| D12 | baixa | anterior | l. 77: `**pain weighting under shadow discipline**` | Slogan de produto em negrito | Tirar o negrito |
| D13 | baixa | anterior | l. 1005: `**That sweep has since closed, and its number is reported in §6.3.3.**` | Linha solta em negrito | Texto normal, unido ao parágrafo anterior |
| D14 | baixa | G | l. 1313: `### Operational-cost table (Table 2) sources` | Table 2 agora é "Services and mandatory third-party keys" | "### Table 2 sources" |
| D15 | baixa | anterior | l. 1109: `the three §6.3.1 gaps likewise do not run under the matched embedder` | A §6.3.1 agora tem um gap (Letta); EverOS e Zep rodaram em 2026-09-10, mas sem quebra por categoria | "Letta produced no number, and the 2026-09-10 EverOS and Zep runs were not broken down by category" |
| D16 | baixa | anterior | l. 1031: `verbosity-constrained, §5.3.2` | A §5.3.2 diz que o gap "is not only verbosity" | Remover "verbosity-constrained" |
| D17 | baixa | anterior | l. 641: `§5.5.4–§5.5.8 measure directly how much backbone choice alone can move these metrics` | §5.5.7 (guardas do adapter) e §5.5.8 (teste abortado) não medem efeito de backbone | "§5.5.4–§5.5.6" |
| D18 | info | metadados | `arxiv-metadata.txt`: `(ASCII-safe, 1824 chars…)`, `Replaced 2026-10-04 (paper v1.0.3 part F)`, `five-system benchmark stated as 2 head-to-head runs + 3 documented non-runs`, `PDF … (v1.0.0, ~389KB…)` | O cabeçalho está velho; o bloco tem 1.902 caracteres e diz 4+1 | Atualizar o cabeçalho (1902 chars, parte G, 4 + 1, PDF v1.0.3) |
| D19 | info | G | `techrxiv-metadata.md`: `81 páginas, 340 KB … MD5 05335e7a…` | `build/*.pdf` (07:45) e `.tex` (07:48) são anteriores à parte G (08:24); PDF e MD5 não correspondem ao `.md` atual | Reconstruir depois de D1/D2 e atualizar páginas/tamanho/MD5 |
| D20 | info | metadados | `abstract.md` §5: `task-type ablation (2026-06-30) confirma vitória arquitetural` | Contradiz a §6.3.2 ("does not … attribute … the rc4 nox-mem lead to the retrieval architecture") | "descarta o task type como causa; não atribui a liderança à arquitetura" |

Layout menor (sem impacto em claim): l. 48–49, a legenda da Table 1 fica separada da tabela pelo
parágrafo "What this table is and is not". Sugestão: mover a legenda para logo acima da tabela.

## O que não mudou e precisava não mudar

Conferi em cada caso acima que nenhum resultado medido mudou de valor. As trocas de valor (LoCoMo, na
parte F) alinham o texto ao artefato. Todas as remoções da parte G são de errata, de número sem
artefato ou de estimativa, e as estimativas foram para o §S6.8 com rótulo.
