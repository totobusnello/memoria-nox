# Revisões Codex + Fable do pacote v1.0.6: o que foi confirmado, rejeitado e mudado

Data: 2026-10-04 (noite). Entradas: o relatório do Codex (gpt-6-astra, recibo `exit: 0`, veredito
NOT READY, 6 achados) e o do Fable (seções A a H). Cada achado foi conferido contra o código, os
outputs, o manuscrito e o dataset antes de entrar. Nada foi commitado, nada foi publicado no
Zenodo, nenhum rascunho do Zenodo foi tocado e ninguém foi contatado.

Caminhos relativos à raiz do repositório.

## Codex

| # | achado | veredito | evidência | o que mudou |
|---|---|---|---|---|
| 1 HIGH | `recompute_section6.py` compara a v1.0.6 com ela mesma | **CONFIRMADO** | rodado como estava: `changed at printed precision: 0`, exit 1 (rebuild "legado" do rc4 ≠ arquivo fixado). O zip em `noxmem-evidence/` já tinha o scorer corrigido, então "legacy" = "fixed" | script reescrito: lê o registro v1.0.5 de `legacy-input/nox-mem-section6-evidence-1.0.0.v105-scorer.zip` (extraído num diretório temporário), carrega os dois `verify_dataset.py` (valores v1.0.5 e v1.0.6) e roda três pernas: (A) scorer legado ≠ corrigido em bytes, métricas guardadas do registro v1.0.5 = scorer legado, 135/135 contra os valores v1.0.5, rebuild legado = agregados fixados; (B) payload = scorer corrigido, 135/135 contra a v1.0.6, nenhuma query acima de 1, rebuild corrigido = agregados do payload; (C) mesmos 135 ids, mesmos ids recuperados e gold nos dois registros, e os valores impressos mudam **exatamente** em R07, R08, R11, A05, R17, E10, C13, C14, C18, C19, igual ao que os dois scorers dão. Novo `--check` (não escreve). Resultado: 32/32 entradas fixadas, 10 mudanças (10 esperadas), exit 0. Mutação (apontar de volta para o zip regenerado): 0 de 10, exit 1. `SCORER-FIX.md`: nota no topo, §3 e §7 reescritos (o verificador do dataset sai **0**, não 1) |
| 2 HIGH | a carta afirma DOIs que ainda são rascunho | **CONFIRMADO como condição de ordem** | nota de status do pacote: 23147633 e 23146656 não publicados | sem mudança no texto da carta (ela só sai depois da publicação, e reescrever para "rascunho" tiraria o argumento "pode ser conferido agora"). Checklist do pacote: passos 5a a 5e (merge do PR, troca do PDF e do zip nos rascunhos, publicação) antes do 6 |
| 3 HIGH | direção do confound de colisão (e) não sustentada | **CONFIRMADO** | rc4 `mem0.json`: 20 listas com id repetido no top 10, 3 com id gold repetido, 17 só com id não-gold. Com o scorer corrigido, repetição gasta posição do Mem0; manter os dois documentos pode cobrir um gold que a cópia única do nox-mem perde. O efeito líquido não foi medido | manuscrito §6.3.2: título de (e) sem "against the arm that won"; "runs against nox-mem" → "its net effect on the comparison is not isolated"; "The direction matters more than the magnitude: this asymmetry disfavours nox-mem, which won anyway" → frase que diz que o efeito líquido não está isolado e dá as contagens 20/17; "the handicap stands as stated" → só as contagens (Mem0 6,826 linhas, nox-mem 6,822) |
| 4 HIGH | a ablação de task type não isola nem limita a contribuição | **CONFIRMADO** | `evidence/rc4-ablation-run.redacted.log`: 33 linhas `dense search error: 504 Deadline Exceeded`; `adapters/nox_mem.py` l. 633-641: no erro, `dense_rows` fica vazio e a fusão usa só o FTS5; store genérico com 6,791 de 6,822 ids (23 gold ausentes) | manuscrito (11 linhas: §6.3.2 ×6, §6.3.2 taxonomia, §6.5 princípio 5, §6.7, §7.1 ×2, §8): "at most 0.34 pp", "can only lower", "rules out", "tested and neutralized", "ablated away", "ablated and ruled out", "shown not to drive the result" → "with task types removed from both arms, the lead persisted", e o parágrafo da ablação diz por que os 0,34 pp não isolam nem limitam (cobertura 99,03%, 33 erros densos, documento a menos pode subir ranking). Espelhos: `README.md`, `docs/COMPARISON.md`, linha do checklist do `paper/abstract.md`, README do dataset. O abstract do paper, `abstract.md` §2, `arxiv-metadata.txt` e `techrxiv-metadata.md` não fazem afirmação de task type nem de colisão: sem mudança (1.912 caracteres, abaixo de 1.920) |
| 5 MEDIUM | "a script that recomputes the Section 6 values" exagera | **CONFIRMADO** (com correção da aritmética do Codex) | docstring do verificador: 132 recomputados dos arquivos (116 números, 13 sim/não, 3 strings) + 3 diferenças de valores impressos (X01-X03) = 135; 12 grupos não recomputáveis. O Codex escreveu "132 + 13 booleanos + 3", que somaria 148; a parte "132 valores e afirmações" está certa | manuscrito §6.3.2: "a verifier that checks 132 Section 6 values and statements against the supplied outputs, metadata, logs and store extracts, plus three arithmetic differences of printed figures; twelve groups of Section 6 figures cannot be recomputed from it and are listed there with the reason". README do dataset: linha de `verify_dataset.py` na tabela de arquivos alinhada |
| 6 LOW | agentmemory "medido só na primeira corrida" | **CONFIRMADO** | `eval/q4-comparison/output/agentmemory_full.json`: 20 queries, 2026-05-24 01:16-02:20 UTC | carta, item 2: "The reported canonical comparison for agentmemory is limited to the 15 June run (n = 100 per dataset), and it did not take part in the later full-set comparisons." Linha nova na §3.5 do pacote |

## Fable

| # | achado | veredito | evidência | o que mudou |
|---|---|---|---|---|
| H1 | o repo público não tem a v1.0.6; parágrafo "Pending" do CHANGELOG desatualizado | **CONFIRMADO** | `git status`: nada da v1.0.6 commitado; último commit é a v1.0.4. O parágrafo dizia que o verificador sai 1 | `paper/CHANGELOG.md`: "Pending" substituído por um parágrafo **Evidence dataset** (regenerado, 135/135, exit 0 no payload e no zip extraído, "to be published together", sem dizer que já foi publicado) e por um bloco com as correções de redação Codex/Fable. O commit e o PR não foram feitos (regra: nenhum git de escrita); viraram o passo 5a do checklist, **antes** de publicar |
| H2 | `README.md` público contradiz o paper | **CONFIRMADO** | l. 58, 309, 311, 313, 326 e `docs/COMPARISON.md` l. 280, 282 com 0.4337/0.4061/+0.119, "three residual confounds", "substantially an OpenAI-embedder effect", "The win is architectural" | valores v1.0.6 (0.4331, 0.4030, +0.123); quatro confounds nomeados, incluindo (e); "não atribui o resultado ao embedder nem à arquitetura"; ablação com "the lead persisted" e a ressalva do Codex 4. **Não** usei o "ruled out" proposto pelo Fable, que o Codex 4 refuta. Também corrigidos: README l. 315 ("same embedder, who wins on architecture" → "same embedder" com confounds declarados) e, no `COMPARISON.md`, o confound (a) que ainda dizia que o 2.0.x "silently swallowed" `user_id`/`limit` (o paper estabelece que a 2.0.10 rodou e rejeita a forma 0.1.x). Varredura do repo por 0.4337/0.4061: o que sobra é descrição da correção (CHANGELOG, metadados, scripts de depósito) ou registro datado (`docs/HANDOFF.md` l. 2481), deixados como estão |
| M1 | "I found a scoring defect" atribui a descoberta errada | **CONFIRMADO** | `noxmem-evidence/REVIEW.md` l. 20: Codex 1 achou | carta: "A review of this check found a scoring defect" (o "Building this check exposed" do Fable ainda sugere que a construção achou) |
| M2 | os marcadores de 4/10 da carta pesam a favor da recusa | aceito | — | entrou pela versão curta (G): um marcador "3 and 4 October" |
| M3 | "material on operations ... moved out" promete demais | **CONFIRMADO**, com correção | o abstract ainda tem a frase de produção. A troca proposta, "seven operational appendices", também é imprecisa: o CHANGELOG registra apêndices C a G (#494) mais o material Wave 2 / cross-backbone (#508), que não são apêndices nem operacionais | a frase saiu do item 1 (versão G); no item 5: "appendices C to G and two blocks of secondary results moved to supplementary material" |
| M4, M5 | abertura defensiva; tese tarde | aceito | — | entrou pela versão G |
| L1 | "nine printed values involving Mem0" | aceito | — | "nine Section 6 values" |
| L2 | "zero query errors" convida escrutínio | **CONFIRMADO** | §6.3.4: 47 falhas de sessão do Zep | cláusula removida (versão G) |
| L3 | data do `claims_check.py` não conferida | **REJEITADO como problema** | `git log -1 9c11c33`: 2026-09-04 08:56 -0300, "instala claims_check com 8 guardas (#458)" | nenhuma: 4 September está certo. Registrado na §3.5 do pacote |
| L4 | "public repository on 21 May" | aplicado | o repo foi tornado público em 2026-05-05 (commit `4a0b8f6`, handoff com teste HTTP sem login), mas nada prova que ficou público sem interrupção até 21/05 | carta: "committed to the repository, which is public, on 21 May 2026" |
| L5 | `jira-text-renderer` é texto puro, não wiki | **CONFIRMADO** | §1 do pacote cita o JSON do formulário | tabela e nota de formatação da §2 do pacote corrigidas |
| L6 | "six versions" só vale depois de publicar | igual ao Codex 2 | — | passos 5e/8b |
| L7 | varredura de caracteres Jira | refeita no bloco final | zero travessões, asteriscos, sublinhados, chaves, colchetes, barras, `+`, padrões de emoticon e de tachado | — |
| E | outras cópias de `ndcg_at_k` creditam cada ocorrência | **CONFIRMADO** | ver abaixo | regra da primeira ocorrência aplicada em 5 cópias |
| F (opcional) | acrescentar oração sobre R07/R11/C13 no README do dataset | não aplicado | opcional, sem efeito em afirmação | — |
| G | versão curta da carta | aplicada com as mudanças acima | a última frase do item 5 (0.6237 e 0.5013 inalterados desde a submissão) conferida no `.md` do commit `5a2071f` (2026-07-01): 0.6237 ×7, 0.5013 ×2 | bloco da §3.3 substituído; skill `avoid-ai-writing` (technical, edit): um achado, o marcador de 3-4 de outubro (frase de 120 palavras com cinco ponto-e-vírgulas), dividido em quatro frases. Contagem: 1.428 palavras / 8.985 caracteres |

### Fable E: as outras cópias do scorer

Regra aplicada em todas: corta no top k, cada id conta uma vez, na posição da primeira
ocorrência, sem re-preencher. Teste de equivalência contra `eval/q4-comparison/aggregate.py`
em 5.000 listas aleatórias com repetição (funções extraídas por `ast`, sem importar os módulos):
0 divergências em nDCG e recall. O `score.ts` foi testado com `node --experimental-strip-types`.

| arquivo | o que mudou | o que alimenta | número publicado muda? |
|---|---|---|---|
| `eval/q4-comparison/run_cap_comparison.py` | `ndcg_at_k` (o `recall_at_k` já usava `set`) | `output/cap_comparison_results.json`, smoke capado do §6.6 (0.0466 / 0.0918 / 0.1835) | não: o arquivo não existe mais (sobrescrito, declarado não recomputável no dataset); só muda uma corrida futura |
| `eval/q4-comparison/scripts/run_efh_ablation.py` | `ndcg_at_k` (recall já com `set`) | `output/efh_ablation_results.json` (2026-05-24, só agregados; o `efh_ablation_raw.json` não está no disco) | não: o paper não cita essa ablação; o arquivo versionado não foi regenerado |
| `eval/q4-comparison/scripts/smoke_baseline_efh.py` | `ndcg10` | só o console | não |
| `eval/longmemeval/score_crossbench.py` | `ndcg_at_k` e `recall_at_k` | `RESULTS-CROSSBENCH-2026-05-29.md`, paper §5.6 (nDCG@10 = R@10 = 1.0000) | não, por construção: `score()` já deduplica os session ids antes (l. 203-213) |
| `eval/locomo/score.ts` | `ndcgAtK` e `recallAtK` | só o console; nenhum resultado versionado | não; o §5.3.1 usa evidence hit@10, que é any-hit e não muda com repetição |

As cópias em `paper/publication/baselines/` não foram auditadas (fora do pedido).

## Outros ajustes que as mudanças acima exigiram

- **README do dataset** (`noxmem-evidence/payload/README.md`): a observação "The query-time
  errors are not mentioned in §6.3.2" ficou falsa e foi reescrita; o cabeçalho "(not stated in
  the paper)" virou "Only the first is also stated in the paper"; a linha de
  `verify_dataset.py` diz "checks the 135 Section 6 values". `SHA256SUMS` e zip regenerados
  **localmente**, replicando os passos 3-4 do `deposit_draft.py` sem rede: só o README mudou
  nos sums; `verify_dataset.py --manuscript` 135/135 exit 0 no payload e no zip extraído;
  zip sha256 `993c3453a5af3aebf4b0a6c7bb86fe746e4e9afce62ef2a6e30302408fdcd284`.
  O rascunho 23146656 ainda tem o zip anterior.
- **PDF**: reconstruído (`scripts/build-paper.sh --pdf-only`), MD5
  `5326d437a02d59ccecd2ac22fcac16e1`, **74** páginas (eram 73), linha de versão v1.0.6
  intacta, zero `TOTO`. O rascunho 23147633 ainda tem o PDF de 73 páginas (`415e9e5d…`).
  Carta, nota de status e checklist do pacote já usam o MD5 novo.
- **Pacote**: nota datada no topo, bloco §3.3, contagem, §3.5 (agentmemory, L3, L4), §2 (L5),
  checklist com 5a (merge do PR antes de publicar), 5b (não reconstruir), 5c (trocar o PDF no
  rascunho com `deposit-v106.py`), 5d (trocar o zip com `deposit_draft.py`), 5e (publicar), e
  MD5 / `Pages: 74` nos passos 6 e 7.

## Conferências finais (todas rodadas depois da última edição)

| conferência | resultado |
|---|---|
| `python3 paper/claims_check.py` | 21 guardas verdes |
| `verify_dataset.py --manuscript paper/paper-tecnico-nox-mem.md` (payload e zip extraído) | 135/135, exit 0; toda citação continua literal no §6 |
| `recompute_section6.py --check` | 32/32 entradas, 10 mudanças = 10 esperadas, exit 0 |
| `tests/test_scorer_dedup.py` | 7 testes OK |
| `scripts/censo-lastro-do-manuscrito.py` | exit 0 |
| diff mecânico do manuscrito (antes → depois desta passagem) | 11 linhas mudadas; notas de rodapé, links e títulos idênticos; números novos no texto: 132, 20, 17, 33, 504, 6,822, 2,482 (todos conferidos acima); saiu só a referência "§6.3 → §6.3.2" da frase removida |
| varredura das frases-alvo no manuscrito | zero "disfavour", "won anyway", "handicap", "at most 0.34", "can only lower", "neutraliz", "ruled out", "ablated away", "against the arm" |
| caminhos pessoais, hosts e tokens nos arquivos públicos editados | nenhum |

## O que ficou para você

1. PR com a v1.0.6 (código, paper, README, docs) e merge no `main` **antes** de publicar.
2. `deposit-v106.py` (troca o PDF do rascunho 23147633; readback `md5:5326d437…`) e
   `deposit_draft.py` (troca o zip do rascunho 23146656). Os dois só mexem em rascunho.
3. Publicar 23147633 e 23146656, conferir que os DOIs resolvem, e então seguir o checklist do
   pacote a partir do passo 6.

## Adendo (2026-10-04, depois da checagem mecânica final, `CHECK-FINAL.md`)

O MD5 `5326d437…` acima foi substituído. "known to favor" (§6.3.2 e §7.1 L5) virou "that favors
nox-mem by design", e o PDF foi reconstruído: MD5 `6bf378c01d8e35b672f5b66e899c6f86`, 74 páginas.
Os passos 2 desta lista já rodaram: o rascunho 23147633 tem esse PDF (readback OK) e o 23146656
tem o zip `3abd9a47…` (readback OK). Nada foi publicado. `parity-v106.py` agora cobre esta
passagem também (`PARITY.txt`, exit 0).
