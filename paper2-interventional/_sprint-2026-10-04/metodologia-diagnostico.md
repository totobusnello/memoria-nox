# Diagnóstico: o paper de metodologia + honesty-engineering (AI4Math)

> Medido em 2026-10-03, só leitura. Repo lido: `~/Claude/Projetos/7_problems` (o repo registra você como "Luiz").
> Convenção deste arquivo: `(fonte: X)` = artefato ou comando que produziu o número. **NÃO MEDIDO** = não consegui medir, e o motivo vem junto.
> "sd" = session-day: uma sessão longa de trabalho, com os gates rodando, sem contar espera por terceiros nem compute em voo.

## 0. Veredito em seis linhas

1. **Estágio: outline de contribuições, zero prosa.** Não existe esqueleto de seções nem uma linha de manuscrito. "honesty-engineering" aparece só em notas internas (busca: `grep -rIl` em `PNP_AI/drafts`, `PNP_AI/notes`, `*.md` da raiz; nenhum arquivo em `drafts/`). O que o outline chama de "sections" são 4 contribuições, não seções de paper.
2. **O repo discorda de si mesmo sobre o que este paper é**: quatro documentos, três estados (seção 2). Isso precisa ser resolvido antes de escrever.
3. **O que tem artefato é forte** (nível 1 da escada, ledger, gates, painel com recibos, o caso REV-0085). **O que não tem**: o nível 2 (VeriPB), o "nightly certlab prova que o corpus não apodrece" (verifica **1** certificado), e a checagem de máquina "gate-swap não é bijeção" (script não localizado).
4. **O enquadramento do outline (08-09) está superado por ele mesmo** (blocos de 12-09 no topo): a tese que sobra é estreita, "crítica multi-modelo só é confiável onde existe árbitro mecânico". As referências de prior art que a sustentam estão **só dentro do outline**, sem captura arquivada.
5. **Esforço até o primeiro rascunho completo, com todo número rastreado: ~14,5 sd** (escopo cheio) ou **~8,5 sd** (versão workshop curta); mais 2,5 / 1,5 sd de revisão e gates. Cerca de 70% é evidência e verificação, não escrita (seção 7).
6. **Três decisões suas antes de qualquer outra coisa**: objeto/tese, autoria e papel do Krinkin, e a postura sobre o que ainda não existe em código (seção 8).

## 1. Como medi, e o que deixei de fora de propósito

- **Não rodei `bash tools/numbers.sh` inteiro.** Vários gates dele chamam `git` ou escrevem em disco (`digest.py` escreve `.remember/remember.md`; `lastro_claims.py`, `known.py`, `nums_fable_gate.py` e outros usam `subprocess`/`git`), e a regra desta tarefa proíbe git e escrita no repo. Rodei, com `PYTHONDONTWRITEBYTECODE=1`, os gates que eu li antes e que só leem: `nums_ledger.py`, `nums_lean.py`, `nums_drat_claims.py`, `nums_f5.py`, `nums_r1_structural.py`, `nums_lift.py`, mais `tools/lastro-check.sh PNP_AI/10_PNP_CLAIM_LEDGER.md`. Todos saíram com rc=0. Conferi depois: nenhum arquivo novo em `tools/`, `PNP_AI/formal/`, `PNP_AI/verify/` (`find -newermt "-3 hours"`: vazio).
- **VPS de pesquisa (`$NOX_LASTRO_HOST`): só `ls`/`cat`/`crontab -l`** em `~/certlab` e `~/.cargo/bin`. Não abri banco nenhum. A produção (`$NOX_PROD_HOST`) não foi tocada.
- **Web: 3 páginas `arxiv.org/abs`** reconferidas (seção 4). As outras 6 referências de prior art do outline **não foram reconferidas**.
- **Script novo e reutilizável:** `~/Claude/Projetos/memoria-nox/paper2-interventional/measurement/sprint-metodologia-censo-painel.py` (só leitura; imprime JSON). Saída guardada em `_sprint-2026-10-04/metodologia/censo-painel.json`.
- **Limite honesto do censo:** ele dá **denominadores** (quantas chamadas, quais saíram com `exit 0`), não **taxas de acerto**. Classificar uma saída adversarial como "achado verdadeiro" ou "falso positivo" exige alguém ler a saída contra o artefato; contar palavra-chave seria palpite apresentado como medição.

## 2. O estado documental: quatro notas, três estados

| documento | o que diz do P2 / P4 | observação |
|---|---|---|
| `methodology_paper_outline.md` (topo, bloco "DECISÃO DO LUIZ, 12-09") | **P2 e P4 são um paper só, o de AI4Math.** A escada entra como mecanismo, não como manchete | o corpo do mesmo arquivo ainda é o de 08-08/09: título de síntese de circuitos, venues IWLS/FMCAD |
| `methodology_paper_outline.md` (bloco "PRIOR ART, 12-09") | três das quatro contribuições já foram publicadas por terceiros; "a contribuição de circuitos é mais defensável que a de metodologia" | o próprio outline diz que está "de cabeça para baixo" |
| `STATUS.md` (tabela de papers) | P2 = "o paper de AI4Math", mora neste repo, P4 fundido | |
| `fila_papers_completa.md` e `rota_submissao_krinkin.md` | 🅿️ **EM ESPERA 12-09, candidato a SEÇÃO DO P1, não paper.** Gatilho para reabrir: a excisão do P1 | |
| `PLANO.md` §1.11 | "P2 vira seção do P1? **O GATILHO DISPAROU**" (excisão fechou 21-09, entregue 23-09); pergunta aberta para você | |
| `PLANO.md` §4 | ainda lista P2 como "externo/não autônomo" e P4 como "PERTO e oportuno": as duas linhas que o outline de 12-09 já corrigiu | |

(fonte: leitura direta dos seis arquivos, linhas citadas acima.) Resultado: **ninguém reconciliou**. O gatilho do PLANO 1.11 disparou e a pergunta está sem resposta.

## 3. O que existe, contribuição por contribuição

Legenda: **ARTEFATO** = há arquivo/comando que sustenta; **PARCIAL**; **SEM ARTEFATO** = só prosa; **CONTRADIZ** = o artefato diz outra coisa.

### Contribuição #1: a escada de certificação

| alegação do outline | situação | evidência |
|---|---|---|
| Nível 1: DRAT puro sem SB, preferido | **ARTEFATO** | `cert_nosb.py` + `tools/certify.sh` (preflight, exit codes 0-4); `PNP_AI/verify/manifest.csv`: 48 linhas de dado (fonte: `wc -l`=49 menos cabeçalho); `recert_nosb_n4.csv`: 34 linhas = **28** `VERIFIED` + **4** `NAO_VERIFICADO` + **2** `timeout@25200s` (fonte: contagem em python do CSV). Os 4 `NAO_VERIFICADO` (`0x0168`, `0x0661`, `0x166a`, `0x16ac`) foram re-verificados: `s VERIFIED`, bytes de SHA idêntico, 1785-2079 s (fonte: `revalida_nao_verificado.csv`); o original era OOM. Os 2 timeouts (`0x1669`, `0x1683`) continuam sem fechar. Mais 2 classes `opt = 10` ausentes do CSV: **NÃO VERIFICADO** por que (PLANO 2.5). `nums_drat_claims.py`: 133 classes creditadas a DRAT, nenhuma frase credita `VERIFIED` sem linha `VERIFIED` |
| "Todo resultado promovido está no nível 1" | **ARTEFATO, com ressalva** | `atlas_n4.csv`: 48 forced, dos quais 36 nasceram com `+sb`, 10 `sat_tested`, 2 `nosb_*s` (fonte: contagem do CSV). Hoje 32 dos 36 têm cadeia sem SB (28+4 acima) e **as 36 têm veredicto por via que não usa o WLOG** (o teorema de estrutura do `R_1`, solver-free: `nums_r1_structural.py` → "220 classes, 48 forced-multi, zero divergências"). Ou seja: vale, mas por **duas rotas diferentes**, e uma delas é do Krinkin |
| Nível 2: VeriPB por dominância | **SEM ARTEFATO (e o outline admite)** | `tools/certify.sh:4` "Level 2 (TODO)"; `tools/setup-veripb.sh` (cabeçalho de 08-08): VeriPB checker DONE, RoundingSat TODO, BreakID + certified SB TODO. **Zero** arquivos `*.pbp`/`*.opb` em `PNP_AI/`, `tools/`, `verify_repo_stage/` (fonte: `sprint-metodologia-censo-painel.py`, campo `veripb_artifacts`; escopo da busca declarado no JSON). Na VPS: `veripb` e `roundingsat` existem em `~/.cargo/bin`, e `~/certlab/sbdev/tiny.pbp` é um brinquedo de **7 linhas** (`red`+`rup`+`conclusion UNSAT`). Se o `roundingsat` da VPS roda de fato: **NÃO MEDIDO** (o cabeçalho do setup diz TODO; não executei nada lá) |
| Nível 3: prova de WLOG à mão por 3 famílias | **PARCIAL** | `07_MODEL_CALL_LOG.md` linhas 93-96 (REV-0085/86/87/88); teste de regressão no código (`sb_run_b.py:45`, "Codex counterexample circuit, must stay SAT"); CNFs `n4_*_sb_UNSOUND_amo.cnf` em `verify/_generated/`. O **verbatim** do REV-0085 não está arquivado: não há arquivo `rev0082`..`rev0088` em `notes/reviews/` (busca por nome) |
| "Gate-swap adjacente nem é bijeção nas variáveis do encoder, logo é dominância, não simetria" ("machine-confirmed") | **SEM ARTEFATO localizado** | só prosa (`12_MODEL_REVIEW_PROTOCOL.md` §"Correção 2026-08-08", e o outline). Busquei `bijection`/`automorphism`/`gate-swap` em `exp_krinkin_cor6/*.py`, `tools/`, `PNP_AI/notes`, `*.md` da raiz: só prosa. **Se você disser "zero script" estaria exagerando: não procurei em `.rev_logs/` nem no histórico git (proibido).** Tem de ser achado ou refeito antes de virar frase de paper |
| "Aplicação nova de proof logging (revisão de prior art de duas fontes)" | **SUPERADO** | o próprio outline (12-09) diz que a revisão cobriu só a #1 e que a #2 "nunca foi buscada" até 12-09. Não há captura em `capture_manifest.csv` nem em `notes/reviews/` com nome `perplex*`/`nexus*`/`prior*` para essa busca |

### Contribuição #2: painel adversarial multi-família + governança de claims

| alegação | situação | evidência |
|---|---|---|
| Ledger datado e aditivo | **ARTEFATO** | `10_PNP_CLAIM_LEDGER.md`; `nums_ledger.py`: próximo ID livre `7P-PNP-CLM-0091` (máx. em uso 0090) |
| `lastro-check` exige artefato em todo claim promovido | **ARTEFATO, e é sintático** | `lastro-check.sh` → "OK: todo claim promovido (não-grandfathered) tem lastro", **9 claims pré-LASTRO grandfathered** (corte 2026-08-03). O próprio `.github/workflows/lastro-check.yml` diz: "O lint é sintático (existe referência apontável?), não semântico (o certificado é válido?)". O paper não pode vender isso como verificação |
| Bateria de gates (`numbers.sh`) | **ARTEFATO** | 49 arquivos `nums_*.py`, 48 referenciados em `numbers.sh`; o não referenciado é `nums_gates_executados.py` (fonte: censo). O cabeçalho do `numbers.sh` diz "34 dos 36 gates passam sem estado local", **medição congelada de 04-09**, então "36" é histórico, não atual. A bateria é obrigatória no CI desde 2026-09-04 (comentário do workflow) |
| Painel de famílias distintas, recibo verificável | **ARTEFATO** | 07_MODEL_CALL_LOG: 134 linhas numeradas, última de **2026-08-29**; depois disso **132 recibos** em `.remember/` de 2026-08-30 a 2026-10-03 (tabela abaixo); 67 capturas em `notes/reviews/`, 23 em `notes/adjudications/`, 124 linhas em `capture_manifest.csv` (fonte: censo) |
| "Catch real documentado": família independente refutou SB que autor e confirmador tinham "provado" | **ARTEFATO** | call log #93 (REV-0085, Codex, MCP): contraexemplo `0x80008000`, g1=x2∧x3, g2=x1∧g1, tuplas `(2,0,3,0) > (1,0,6,0)`; Kimi REV-0082 propôs, Grok REV-0083 confirmou. Teste de regressão e CNFs unsound no repo. É o melhor ativo do paper. Ressalva: o verbatim do REV-0085 não está arquivado (acima) |
| "O painel **não decide nada**; levanta hipótese que um certificado mata ou confirma" | **CONTRADIZ o protocolo escrito** | `licoes_alphaproof_nexus.md` §1 admite que até 12-09 as vozes devolviam `VEREDICTO: ENVIAR` e eram tratadas como decisão, e lista a reforma como feita (`nums_fable_gate.py`; não rodei esse gate). Mas `12_MODEL_REVIEW_PROTOCOL.md` ainda diz (linha 151) que a rodada é "decisiva" quando "o veredito dela muda o tier de um claim", e `grep -i ranking` nesse arquivo não acha nada. **O protocolo pós-reforma não está escrito em lugar nenhum**: o paper precisa dele, e ele é trabalho (seção 7, §5) |

Recibos do painel, 2026-08-30 a 2026-10-03 (fonte: `censo-painel.json`, campo `receipts`; 132 recibos, 0 não parseados):

| voz | exit 0 (com saída > 0 bytes) | exit 1 | exit 124/143 |
|---|---|---|---|
| codex | 29 (29) | 6 | 1 |
| kimi | 25 (25) | 9 | 2 |
| glm | 18 (18) | 2 | 0 |
| grok | 14 (14) | **13** | 0 |
| deepseek | 6 (6) | 2 | 0 |
| gemini | 3 (3) | 2 | 0 |

`exit 1` ou `124` não é veredito (regra do seu `CLAUDE.md`: ler a causa). Mas o fato é que **13 de 27 recibos do grok (48%)** saíram `exit 1`, e isso entra na seção de limitações: o painel que o paper descreve tem canal frágil.

### Contribuição #3: o artefato reproduzível ("certlab")

| alegação | situação | evidência |
|---|---|---|
| "um script reconstrói a toolchain" | **ARTEFATO** | `tools/setup-veripb.sh` (idempotente; mas o cabeçalho de 08-08 ainda lista itens TODO) |
| "um script reverifica **todo** certificado" | **ARTEFATO** | `tools/reverify.sh` (drat-trim e veripb; sai `!= 0` se algum falha) |
| "regenera byte a byte na VPS" | **ARTEFATO** | `~/certlab/manifest.csv` na VPS: 1 linha (2026-08-08, `0x03de0154`, cnf `ed3b8350f72f8078`, drat `c7ccf7bdb892d3c8`), igual ao outline |
| "**nightly durability check prova que o corpus de certificados não apodrece**" | **CONTRADIZ (superdimensionado)** | cron real na VPS: `23 4 * * * ... reverify.sh ~/certlab/encoders/exp_krinkin_cor6/certs`. Log `~/certlab/reverify.log`: **`PASS=1 FAIL=0 MISS=0`**, todos os dias até `2026-10-03T07:25:08Z` (fonte: `tail` do log). **Ele verifica UM certificado**, o de 08-08 (o diretório tem 2 arquivos: `.cnf` e `.drat`). O paper credita 133 classes a DRAT e há 48 linhas em `manifest.csv` do repo. A frase correta hoje é "1 certificado reverificado toda noite há ≥ 20 dias", não "o corpus". É exatamente o padrão do `CLAUDE.md` de memoria-nox: "medi `PASS=1`" lido como "medi o corpus" |
| DRATs de "30-247 MB" | **CONTRADIZ** | as cadeias de `opt = 9` em n=4 têm **5,15 a 5,61 GB** cada (fonte: coluna `drat_bytes`, `revalida_nao_verificado.csv`). O `VERIFY.md` já diz "30 MB to several gigabytes"; o outline ficou para trás |
| `VERIFY.md` para revisor externo | **ARTEFATO** | existe na raiz; `PNP_AI/verify/` com `reproduce_witness.py`, `manifest.csv`, `sample_certs/`. P1 §9 (`09_reproducibility.md`, 1396 palavras) já descreve o desenho "reproducibility, not blobs" |

### Contribuição #4: o estudo de caso (a família BK, hoje `F_n`)

| alegação do outline | situação | evidência |
|---|---|---|
| Refutação do Thm 7 de Krinkin; preprint retirado creditando nosso contraexemplo | **ARTEFATO, reconferido hoje** | `arxiv.org/abs/2603.08033`: "withdrawn by Kirill Krinkin", v4 em 4 Aug 2026; comentário: "Theorem 2 (the Unit Gap Theorem) is false ... Counterexample and certificates: L. A. Busnello, doi:10.5281/zenodo.21630762". Nota: o **teorema** que a página chama de falso é o Thm 2 (Unit Gap); o outline fala de "Thm 7" (a consequência sobre "exatamente um gate compartilhado"). O texto da v3 (que o outline diz creditar também "diagnóstico e reparo") **eu não reli** |
| `BK₄ = 6` completo | **ARTEFATO** | `atlas_n4.csv`: 6 classes forced com gap = 1; 48 forced no total; 42 com gap ≥ 2 (fonte: contagem em python das 222 linhas) |
| Lift Theorem para todo n ≥ 4 | **ARTEFATO (prova em papel + corroboração)** | `proof_lift_lemma.md`; `nums_lift.py`: "§5.10 bate com `lift_inherit.csv`: opt 12/12, 12/12 preservados, 0 indecisos". É prova em papel; o DRAT em n = 4, 5, 6 é corroboração (o outline de P1 é explícito) |
| `BK₅ ≥ 7` | **SUPERADO** | hoje `F₅ = 74` classes distintas (11 de lift + 63 non-lift) (fonte: `nums_f5.py`). Lean: 8 arquivos, 0 `sorry`, 11 declarações citadas conferidas (fonte: `nums_lean.py`); 5 deles têm `native_decide` na base de confiança e os outros 3 são `kernel` (declarado em `lean_check.csv`) |
| nome "BK" / "Busnello-Krinkin" | **política mudou** | o outline de P1 diz que o epônimo só aparece **depois que ele aceitar**; artefatos públicos usam `F_n` / "forced-reconvergence family". O outline de metodologia ainda escreve BK |

### Outras alegações do outline

- **"Berkeley IWLS'19 lista L(f)→C(f) como future work"**, "222 classes AND/XOR balanced", etc.: **NÃO REVERIFICADO** (só está no outline).
- **Prior art da #2** (EviBound 2511.05524, `Inspectable AI` 2604.11261, MathLedger 2601.00816, `Auditable AI-Assisted Research Writing` 2608.10858, `LLMs Have Made Failure Worth Publishing` 2604.06236, `Context Engineering` 2604.04258, `Self-Correction Illusion` 2606.05976, Nexus 2605.22763): essas IDs aparecem **só** em `methodology_paper_outline.md` (busca: `PNP_AI/notes`, `PNP_AI/drafts/p1_math`, `*.md` da raiz). Reconferi 2 hoje (seção 4).

## 4. Números do outline contra o artefato de hoje

| item | outline (snapshot 08-09, + blocos de 12-09) | hoje | fonte |
|---|---|---|---|
| tamanho do que o BK atinge em n = 4 | `BK₄ = 6` | **6** (gap = 1, forced); 48 forced; 42 com gap ≥ 2 | `atlas_n4.csv` |
| em n = 5 | `BK₅ ≥ 7` | **74** (11 lift + 63 non-lift) | `nums_f5.py` |
| tamanho de DRAT | 30-247 MB | até **5,61 GB** em n=4 `opt = 9` | `revalida_nao_verificado.csv` |
| certificados na checagem noturna | "o corpus" | **1** | `reverify.log` + `manifest.csv` da VPS |
| gates | não cita | **49** arquivos / **48** referenciados | censo |
| claims | não cita | próximo ID **0091** | `nums_ledger.py` |
| Lean | "formalização Lean" | **8** arquivos, **0** `sorry` | `nums_lean.py` |
| chamadas externas ao painel | não cita | **134** no log (até 08-29) + **132** recibos (08-30 a 10-03) | censo |
| arquivos de postmortem | não cita | `14_PROCESS_POSTMORTEM.md`: 1540 linhas, **21** títulos `### E<n>`, **14** `## Padrão` (contagem de títulos, **não** de erros) | censo |
| métrica de eficácia do processo | não cita | `15_PROCESS_INVARIANTS.md` §"Métrica de eficácia": tabela com **2 linhas** (08-10 e 08-11), nenhuma depois | leitura das linhas 163-166 |

Reconferência externa feita hoje (firecrawl, `maxAge: 0`):

- `arxiv.org/abs/2603.08033`: withdrawn, v4 em 4 Aug 2026, comentário credita L. A. Busnello e cita o DOI Zenodo acima. **Confere com o outline.**
- `arxiv.org/abs/2608.10858` (Zhou, Yu; 11 Aug 2026): o resumo traz *git sealing*, *hash-bound provenance*, *red-line gates that refuse non-compliant artifacts and log every refusal*, *cross-model role separation*, e um caso em que o teste confirmatório pré-registrado deu **No-Go e a regra de parada interrompeu o projeto contra os próprios operadores**. **Confere, e é um caso de honestidade mais forte que o nosso gate** (eles pararam o projeto; o nosso gate recusa publicar).
- `arxiv.org/abs/2605.22763` (Tsoukalas et al.; 21 May 2026, v2 8 Jun): "9 of 353 open Erdős problems", "44/492 OEIS conjectures", geração de prova em Lean com verificação em Lean. **Confere com o outline**; o nome "AlphaProof Nexus" não aparece no resumo (título arXiv: *Advancing Mathematics Research with AI-Driven Formal Proof Search*).
- **Não reconferidas:** as outras 6 IDs. O próprio outline avisa que "prior art de 2026 envelhece em semanas".

## 5. O que falta para o primeiro rascunho completo

1. **Resolver o objeto e a tese** (decisão D1). Sem isso, qualquer seção é redigida para um paper que pode não existir (mesma lição do B1 no PLANO 3.2).
2. **Um esqueleto de seções.** Não existe. Proposta na seção 7.
3. **Prior art refeito e arquivado.** Capturar verbatim as 8 IDs e fazer uma busca nova de 12-09 para cá, no formato do `tools/lit_first.py` (captura datada no `capture_manifest.csv`). A busca de 12-09 não deixou captura.
4. **O protocolo do painel, pós-reforma de 12-09, escrito** (ranking + preocupação decisiva + teste discriminante; nunca campo que o gate leia como aprovação). Hoje vive só em `licoes_alphaproof_nexus.md` e no comportamento de `nums_fable_gate.py`.
5. **Os denominadores do painel viram um quadro de "o que pegou o quê".** Os catches documentados têm origens diferentes (painel, humano, gate, checador de prova): REV-0085 (Codex), Krinkin achou 10→11 classes de lift lendo artefato sem solver (VERIFY.md), Rychkov 2025 fechou o caso n=6 que o repo lia como aberto (`tools/lit_first.py`, cabeçalho), 12 defeitos de prosa que nenhum gate lê (`fila_papers_completa.md`). Sem esse quadro o paper vira anedota, que é a objeção hostil do próprio outline ("gênero já nomeado").
6. **Localizar ou refazer a checagem "gate-swap não é bijeção"**, ou cortar a frase.
7. **Corrigir a frase do certlab** (ou tornar verdadeira: estender o `reverify.sh` noturno aos 31 certificados de `sample_certs/`, 231 B a 27,9 MB).
8. **Reconciliar a nomenclatura**: BK → `F_n` até o Krinkin aceitar o epônimo.
9. **Contar uma vez a história de honestidade com números que fecham.** O `15_PROCESS_INVARIANTS.md` diz que a coluna de eficácia "só aceita contagem se o artefato carregar a data por entrada"; com 2 linhas preenchidas, **o repo não tem série temporal de melhora do processo**. O paper não pode afirmar que o processo melhora; pode afirmar o catálogo.
10. **O que não depende de ninguém e já existe como matéria-prima**: P1 `09_reproducibility.md` (1396 palavras) e `11_appendix_revision_record.md` (3970 palavras); `licoes_alphaproof_nexus.md`; `14_PROCESS_POSTMORTEM.md`; `07_MODEL_CALL_LOG.md`.

## 6. Dependências de outros papers

| dependência | tipo | detalhe |
|---|---|---|
| **Paper conjunto com o Krinkin** | **mole**, com um ponto duro | (a) Se o paper usar "as 36 dívidas de SB pagas por rota solver-free" como exemplo de regime de certificado, **o teorema de estrutura do `R_1` é dele** e vive no rascunho conjunto (`drafts/joint_krinkin/01_rk_forced_reconvergence.md`, 6054 palavras; `02_parity_tower.md`, 1206 palavras). Citar como "em preparação, conjunto" resolve. (b) A história da retratação dele é o caso central; o texto da retratação é público (arXiv, conferido hoje), mas ler a passagem antes de postar é cortesia e evita erro de atribuição. (c) A bola do paper conjunto está com ele desde 12-09; o último email nosso saiu em 02-10 12h02 BRT (`krinkin_queue.md`, linha do `krinkin_reply_2026_10_02_body.txt`). Se ele respondeu depois disso: **NÃO VERIFICADO** (só li o repo). (d) Ordem: `PLANO.md` 1.10 inclina P1 a sair depois do conjunto; P2 não precisa esperar nenhum dos dois |
| **Resultados da família BK (P1)** | **duro nos números, mole na submissão** | O estudo de caso só pode citar o que já está certificado: `F₄ = 6` (atlas), Lift (prova + corroboração), `F₅ = 74` (gate). Não precisa do P1 publicado: pode citar o DOI Zenodo `10.5281/zenodo.21630762` (contraexemplo + certificados) e "P1, in preparation". O que muda se o P1 mudar: os números do caso, que o gate `numbers.sh` já vigia. Regra do próprio P1 (`math_paper_outline.md`): "se um parágrafo é sobre *como sabemos*, e não *o que é verdade*, é do P2" |
| **VeriPB nível 2 / "P7"** | **nenhuma, se declarado como desenho** | O outline de 12-09 faz disso virtude: o paper diz que o nível 2 "existe em desenho e não em código", e isso é a tese em exercício. O P7 saiu do caminho crítico em 31-08. **Só vira dependência se você quiser o nível 2 como resultado**, e aí é pesquisa: `12_MODEL_REVIEW_PROTOCOL.md` lista três rotas (R1 regra `dom` do VeriPB, R2 reformular o encoder, R3 força bruta no-SB). Não dou faixa estreita de esforço: **NÃO ESTIMADO com base em evidência**; como julgamento, algo da ordem de 10 sd com chance real de não fechar |
| **B1 / SPbSAT (Kulikov)** | **nenhuma, mas é um segundo caso** | auditoria de 614 187 entradas, 10 449 melhoradas (`fila_papers_completa.md`) é outra história de "verificação independente por máquina". Está bloqueada pela resposta dele (`PLANO.md` 3.2). Não usar no P2 antes de saber que paper o B1 é |
| **Compute em voo** (8 kissat no Mac, 4 réplicas na VPS) | **nenhuma** | `ESTADO_2026_10_03.md`: reavaliação marcada para ~2026-10-12; a certificação por LRAT (PLANO 2.11) é extensão do nível 1. O rascunho não deve depender desses veredictos |
| **Prior art externo** | **externa e perecível** | refazer logo antes de redigir e de novo antes de submeter |

## 7. Esforço por seção, em session-days

Esqueleto proposto (adaptado ao público AI4Math; a escada é mecanismo, não manchete; título de trabalho do próprio outline: *quando o revisor é um checador de prova*).

| # | seção | escrita | evidência e verificação | total (cheio) | total (workshop curto) | o que consome o tempo |
|---|---|---|---|---|---|---|
| 1 | Abstract + introdução | 0,5 | 0,5 | **1,0** | 0,5 | tese fixada em D1; responder à objeção hostil do outline ("EviBound + 2608.10858 já fizeram governança; qual a contribuição?") |
| 2 | Related work e posicionamento | 0,5 | 1,5 | **2,0** | 1,5 | refazer e **capturar** o prior art (8 IDs + busca de 12-09 até hoje), no formato `lit_first` |
| 3 | Mecanismo: a escada | 0,5 | 1,0 | **1,5** | 1,0 | montar os números de 3.1; achar ou refazer a checagem "não é bijeção"; nível 2 como desenho |
| 4 | Governança de claims | 0,5 | 1,0 | **1,5** | 1,0 | dizer com honestidade que `lastro-check` é sintático; o que cada gate pegou (do postmortem) |
| 5 | Painel adversarial como gerador de hipótese | 0,5 | 3,0 | **3,5** | 2,0 | escrever o protocolo pós-12-09; classificar as 134 + 132 chamadas (versão curta: só ~5 casos curados, sem taxa) |
| 6 | Estudo de caso (a família) | 0,5 | 1,0 | **1,5** | 1,0 | condensar o P1 sem copiá-lo; números via gates; leitura do trecho sobre o Krinkin |
| 7 | Contabilidade de falhas | 0,5 | 1,0 | **1,5** | 0,5 (fundida em 4/5) | destilar 1540 linhas de postmortem em ~6 padrões; sem série temporal de melhora (só catálogo) |
| 8 | Reprodutibilidade e artefato | 0,25 | 0,75 | **1,0** | 0,5 | reescrever a frase do certlab; opcional: estender o reverify noturno aos 31 `sample_certs` |
| 9 | Limitações e discussão | 0,5 | 0,5 | **1,0** | 0,5 | nível 2 sem código; canal do painel frágil (grok 13/27 `exit 1`); um domínio, um operador |
| | **Subtotal: primeiro rascunho completo** | **4,25** | **10,25** | **14,5** | **8,5** | |
| | Integração, gate de números próprio do manuscrito, revisão adversarial com 2 famílias **lendo o PDF renderizado**, ciclo de correção | | | **2,5** | 1,5 | o P1 mostrou que defeito de prosa e de renderização não é pego por gate (12 defeitos, 5 ALTA, em 30-08; enunciados perdidos no PDF até 23-09) |
| | **Total até um rascunho que sobreviveu à revisão interna** | | | **~17** | **~10** | |

Base e margem: não medi nada aqui, é julgamento ancorado em dois fatos do repo. (i) A prosa inteira do P1 (§1-§9 + §7½) foi escrita **em uma sessão** (`15_PROCESS_INVARIANTS.md`, linha 2026-08-11 da métrica, "produção: 10"), então escrever é barato quando a matéria existe. (ii) O mesmo P1 precisou depois de auditoria que achou 12 defeitos de prosa (`fila_papers_completa.md`) e de correção de conversor em 23-09, então verificar é caro. Daí os ~70% em evidência. Margem: ±40%. Fora da conta: espera por você (decisões, leitura), pelo Krinkin, e o nível 2 (VeriPB).

## 8. As três decisões que você precisa tomar primeiro

### D1. Qual é o objeto e qual é a tese?

O repo tem hoje três respostas (seção 2). Escolha uma e registre onde as outras notas vão apontar:

- **(A) Paper autônomo de AI4Math, tese estreita**: "crítica multi-modelo só é confiável onde existe árbitro mecânico (checador de prova, DRAT, Lean, re-simulação); o painel levanta hipótese, o certificado decide", com a refutação de um teorema publicado como validação contra um resultado, não contra benchmark. É a formulação que o próprio outline diz que sobrevive.
- **(B) Seção do P1** (a pergunta do PLANO 1.11). Mantém uma peça só, mas o P1 já tem 97 páginas e está parado esperando sua leitura; a regra do P1 diz que "como sabemos" é do P2.
- **(C) Em espera até depois do paper conjunto.**

Minha leitura: **A, em escala de workshop**, porque não bloqueia nem é bloqueado por P1 ou pelo conjunto, e porque é a única versão cuja objeção hostil tem resposta escrita. **Mas o ônus é seu**: se a resposta à objeção ("o que o EviBound e o 2608.10858 não têm?") não convence você, vá de B ou C. Em qualquer caso, atualize `PLANO.md` §4 e `fila_papers_completa.md` para o mesmo estado.

### D2. Autoria, e o papel do Krinkin neste paper

O paper conta a retratação dele e pode citar a teoria dele (`R_1`). Opções: você como autor com agradecimento e **leitura prévia** das passagens sobre ele; ou convidá-lo (o "Yes, two names" de 14-09 é do paper **conjunto**, não deste: `PLANO.md` 1.9). Também decide se o nome "BK" aparece (política atual: só depois do aceite dele; use `F_n`). E fica registrado se o uso de agentes de IA na produção deste trabalho entra como declaração de método (para o público AI4Math é parte do objeto).

### D3. Qual postura sobre o que ainda não existe em código?

Três pontos concretos, e uma escolha só:

- nível 2 (VeriPB): **(a)** declarar como desenho, custo 0 sd; **(b)** construir antes (P7), ~10 sd com risco, só se você quiser o nível 2 como resultado;
- certlab noturno: **(a)** reescrever como "1 certificado, todo dia, há ≥ 20 dias" (0,25 sd); **(b)** estender aos 31 `sample_certs` (+0,75 sd);
- checagem "não é bijeção": achar o script ou refazer (~0,5 sd), ou cortar a frase.

Minha leitura: **(a) no nível 2 e (b) no certlab**. O outline de 12-09 já diz que dizer "o nível 2 existe em desenho e não em código" é a tese em exercício; um paper sobre honestidade que superdimensiona o próprio certlab se auto-refuta.

*Não é decisão sua ainda, mas precisa ser feita antes de redigir:* levantar venues de AI4Math e prazos. **NÃO MEDIDO** (o outline lista IWLS/FMCAD, que é o enquadramento superado). Posso levantar em ~0,5 sd.

## 9. O que não foi medido

- Se o `roundingsat` da VPS de pesquisa executa (só vi o binário em `~/.cargo/bin`).
- Qual é a taxa de achado verdadeiro do painel (classificação das 266 chamadas): o censo dá só denominadores.
- Se o Krinkin respondeu ao email de 02-10 (só li o repo).
- O conteúdo da v3 do `2603.08033` (só li a página da v4 de retratação).
- 6 das 8 referências de prior art; qualquer paper novo de 12-09 até hoje.
- Quais são as 2 classes `opt = 10` ausentes do `recert_nosb_n4.csv` (PLANO 2.5 também diz NÃO VERIFICADO).
- O script da checagem "gate-swap não é bijeção": busquei em `exp_krinkin_cor6/*.py`, `tools/`, `PNP_AI/notes`, `*.md` da raiz; **não** busquei em `.rev_logs/`, `.job_logs/` nem no histórico git (git proibido).
- Resultado de `numbers.sh` completo (ver seção 1 para o porquê).

## 10. Para o seu site

Hoje **não há nada deste paper para postar**: não existe rascunho, e o outline é interno (cita correspondência do Krinkin e a decisão sobre prior art). O que **já tem DOI público e é citado pela página de retratação do arXiv** é o contraexemplo + certificados, `10.5281/zenodo.21630762` (conferido pelo comentário do arXiv; **não** testei se o DOI resolve). Quando houver rascunho, o ponto de entrada natural para o site é o DOI do Zenodo do próprio paper, e não este repo (privado).

## Anexo: arquivos produzidos

- `~/Claude/Projetos/memoria-nox/paper2-interventional/_sprint-2026-10-04/metodologia-diagnostico.md` (este)
- `~/Claude/Projetos/memoria-nox/paper2-interventional/_sprint-2026-10-04/metodologia/censo-painel.json`
- `~/Claude/Projetos/memoria-nox/paper2-interventional/measurement/sprint-metodologia-censo-painel.py`
- Nada em `/var/tmp` ou `_tmp/`; nenhum arquivo do repo `7_problems` alterado; nenhum comando git.
