# APPLY-REPORT-G — revisão Fable aplicada (v1.0.3, parte G)

Data: 2026-10-04. Escopo: os 17 achados CONFIRMADOS de `REVIEW-FABLE.md`, aplicados a
`paper/paper-tecnico-nox-mem.md` com a correção do verificador onde ela difere da Fable (em
especial, a correção de preço da M2 proposta pela Fable **não** foi aplicada). Nenhum comando git.
Nada publicado no Zenodo. Ninguém contatado. Nenhum resultado medido mudou: só redação, lugar,
proveniência ou remoção de número sem lastro.

Backups pré-edição de todos os arquivos tocados e o script das substituições (`edit_paper.py`,
cada troca com contagem exata conferida antes; os blocos retirados em `moved_blocks.json`):
`/private/tmp/claude-501/-Users-lab-Claude-Projetos-memoria-nox/de3857d1-533c-4471-8b2a-ae1c53eff923/scratchpad/applyG/`

## 1. Resultado

| Item | Estado |
|---|---|
| Achados confirmados | 17 de 17 aplicados |
| `python3 paper/claims_check.py` | `ok — 21 guardas passaram; 6 alegações retratadas` |
| `python3 paper/claims_check_mutation_test.py` | `ok — 49 mutações mordidas com o marcador certo, controle negativo silencioso` |
| Palavras do manuscrito | 28.623 → 26.091 (−2.532) |
| Densidade de referências (piso 2,06, teto 2,95) | 2,061 → 2,261 por mil |
| `paper/measurement/recompute-rc4-categories.py` | `ok — §6.4 reproduced from the rc4 outputs` (15 células e os 5 n batem; sha256 das 3 entradas = `MANIFESTO-LASTRO.json`) |
| Abstract standalone (≤ 1.920) | 1.902 caracteres, 281 palavras, ASCII |
| PDF / Zenodo | **não** reconstruído, **não** tocado (ver §4) |

## 2. O que mudou, por achado

**A1 (Mem0 réplica).** Procurei script e saída por query no repositório, em
`~/Backups/memoria-nox-lastro-2026-09-12/`, em `eval/q4-comparison/` e no scratchpad desta
sessão; a memória `project_confound_a_rc4_mem0_versao_medido_12_09.md` descreve a réplica mas não
aponta arquivo. O transcript da sessão de origem (`2bb3f61b…`) nomeia `replay-confound-a.py` e
`replay-full.json`, num scratchpad que **não existe mais**. Sem os dois, cortei os três números
(2.375 / 9,83 / 0,4446) e a frase do "+0,011"; ficou uma frase dizendo que nenhum número de
re-execução é reportado porque o script e a saída não foram retidos. O argumento de versão e
parametrização, que se apoia em artefatos versionados, ficou. Nada foi copiado para
`eval/q4-comparison/output/rc4-replay/` (o diretório não foi criado).

**A2 (tom de produto).** §5.7.4 e §5.8.4 foram ao `supplement-operational-appendices.md`
(§S5.7.4, §S5.8.4, sem mudança de texto); §5.8.5/§5.8.6 viraram §5.8.4/§5.8.5 e as 5 referências
foram trocadas. §5.8.3 virou uma frase. §6.8 = tabela + um parágrafo neutro. §6.9: ficaram a
introdução (neutra), as observações da corrida e a nota de escopo datada; saíram o parágrafo
"deployability penalty" com a tabela, a nota da EverMind-AI, o "Honest bound" e o parágrafo final
com o slogan em negrito. "Verdict: REJECT as default. Ship opt-in" → "Default: off; available
behind a flag". Saíram "effectively free", "~667× cheaper", "silent killer", "the contract that
makes nox-mem composable", "is marketing" (→ "a vendor figure without a stated percentile"),
Notion/git/SESSION-STATE do §3.2, as frases do dashboard no §8, "measured by us, published by
us", "the whole reason §6.8 exists", "honest in the direction that hurts us least".

**A3 (rótulos internos).** Caixa de headline: 18 → 6 bullets, cada um com sua seção. "Lab Q1",
"Wave 2", "F10", "Q3" e WIN/PASS/FAIL/NO-REPLICATE/DOCUMENTED_INSUFFICIENT/INDETERMINATE/CLEAN
estão em zero no manuscrito. Mantidos os nomes de corrida que o texto define (Wave A, Wave B/C,
Phase D/G/H v2, IterB, IterC, rc4).

**A4 (histórico no corpo).** Errata curta mantida só onde número com DOI mudou: §5.7.1 (653 ms,
encurtada) e §6.4 (tabela de categorias). O resto foi para o CHANGELOG (lista completa na parte G).

**M1 (pre-registered).** "Pre-specified (execution plan committed to the public repository before
the first run; not registered with an external registry)" no abstract, §6.1 e §8; título do §6
"(Pre-specified)"; §6.7 virou "Pre-specification" e passou a dizer que o plano é documento interno
de execução, com faixas de versão, o all-Gemini como side experiment e o critério de sucesso usado
como gate interno de produto (conferi no spec: l.6, l.23, l.142). Espelhado em `abstract.md`,
`arxiv-metadata.txt`, `techrxiv-metadata.md` e no bloco V103 do `deposit-v103.py`.

**M3 (boost).** §4.1 define `score = base × (1 + Σδ)`, δ = w − 1, w ∈ {2,0; 1,5; 0,8}, salience
δ ∈ [−0,5; +0,5], conferido em `staged/1.7a/edits/search.ts` (cabeçalho l.19–20, `boostSum`
l.408–421). Corrigidos §2.5, §5.1.3 ("weights"), §5.7 e §8.

**M4 (§6.4).** Script novo `paper/measurement/recompute-rc4-categories.py` + saída
`paper/measurement/out/recompute-rc4-categories.json`. Ele re-deriva o balde de cada pergunta do
LoCoMo a partir da categoria nativa em `cache/raw/locomo10.json`, confere que todo rótulo gravado
na saída é o mapa velho da categoria nativa (o join está certo) e só então exige os valores do
§6.4. `category_labeler.py` não foi tocado.

**M5, M2, M6, M8, M9, M10, L1, L2, L3, L5.** M5: proveniência dos ICs pareados no §5.1.7. M2:
coluna de razão removida e o $0,001/call atribuído à leitura gravada no artefato em 2026-05-29,
que a página atual não mostra. M6: "ranks third, behind EverOS and nox-mem and ahead of Mem0".
M8: Tabela 2 só com serviços e chaves; RAM, cold start e setup dos concorrentes no suplemento
(§S6.8) como estimativas do autor; headline "~10× less RSS" retirada; setup = 2 comandos. M9:
frases retiradas do `[^everos]`. M10: §3.4 "Write-Side Maintenance: Rule-Based Mechanisms", sem
"first-class subsystem" e sem "four" (são cinco subseções). L1, L2, L3, L5 como listados.

## 3. Escolhas que você deve conhecer

- **"breakthrough" ficou no §5.8.2.** O A3 o lista, mas ali é citação de overclaim com a
  retratação na mesma frase, e a isenção `RETRATACAO` e um caso da suíte de mutação dependem dela.
  Tirar quebraria a mutação "marcador de RETRATACAO quebrado no guarda".
- **O ~95k do F6 ficou** (encurtado), pelo mesmo motivo: a mutação de `populacao_check` precisa de
  uma segunda população no texto para morder. É dado do corpus, datado, não histórico de revisão.
- **Censo `q4-corridas-census.json`:** saíram 4 sítios (`penalidade-1286`, `bound-68a`,
  `bound-68b`, `bound-final`) porque as frases saíram; a nota no próprio censo registra os
  templates. A perna L5 (completude) segue varrendo o manuscrito.
- **`[^beamretrieval]`** só era citada na caixa velha; a caixa nova a cita (sem isso a footnote
  ficaria órfã).
- **"committed on 2026-05-23"** não entrou: sem git eu não posso conferir a data do commit; o texto
  diz "committed to the public repository before the first run on 2026-05-24".
- A cópia da fórmula multiplicativa no `supplement-wave2-and-cross-backbone.md` (bloco verbatim)
  não foi mexida.

## 4. O que fica para você

1. **PDF e Zenodo estão na parte F.** Não reconstruí o PDF porque a carta, o rascunho 23130276 e o
   `paper/build/` concordam hoje no MD5 `05335e7afc3819532cb86278752ef05f`, e um rebuild quebraria
   isso sem o depósito. Ordem para sincronizar: `scripts/build-paper.sh`, depois
   `deposit-v103.py` (ele agora troca "pre-regist*" na descrição herdada e **para** se sobrar
   alguma ocorrência; como a descrição da v1.0.2 não está no repositório, não sei quantas há),
   depois o MD5 e `Pages` nos lugares operativos da carta.
2. **Carta.** Não dizia "pre-registered" (o item 2 diz "written down in a plan dated 23 May 2026,
   before the first run", que segue verdadeiro). Só a linha de lastro da tabela foi atualizada, e
   a nota da parte G no topo do pacote traz uma frase proposta para o item 4, para entrar junto
   com o PDF novo.
3. **Réplica do Mem0.** Se você quiser os três números de volta, é refazer a réplica com script e
   saída por query versionados em `eval/q4-comparison/output/rc4-replay/`; isso reembeda queries
   (custa chamada Gemini), então não rodei.
