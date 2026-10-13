# Checagem mecânica final do pacote nox-mem v1.0.6

Data: 2026-10-04 (noite). Checagem independente: rodei tudo de novo e não usei os resultados
do editor. Não editei nenhum arquivo além deste. Não rodei git de escrita, não publiquei nem
toquei nos rascunhos do Zenodo e não contatei ninguém. O Gmail foi só lido, para conferir
datas e citações. Saídas intermediárias ficaram no scratchpad da sessão (`checkfinal/`), fora
do repositório.

Resultado: **2 defeitos** (1 na carta, 1 no lastro da paridade) e **1 observação de redação**.
Fora isso, todos os passos passaram.

## 1. Build e guardas

| conferência | resultado |
|---|---|
| build do PDF | **não** rodei `scripts/build-paper.sh` no lugar, porque ele sobrescreve `paper/build/paper-tecnico-nox-mem.pdf` e mudaria o MD5 que a carta cita (o passo 5b do pacote diz para não reconstruir). Rodei o mesmo `pandoc` (mesmas flags, xelatex, preamble, refs.bib) com saída no scratchpad: exit 0, **0 "Missing character"**, **74 páginas**. O `pdftotext -layout` do rebuild é **idêntico** ao do PDF atual. O PDF atual tem MD5 `5326d437a02d59ccecd2ac22fcac16e1`, 74 páginas, linha "Version v1.0.6 (2026-10-04) · DOI 10.5281/zenodo.23147633", 0 `TOTO`, e foi gerado às 21:35, depois da última edição do `.md` (21:31). O rebuild tem MD5 `8e248363…` (o carimbo de data muda o MD5): isso confirma que rodar o build de novo quebraria o MD5 da carta |
| `paper/claims_check.py` | exit 0, "21 guardas passaram; 6 alegações retratadas" |
| `paper/claims_check_mutation_test.py` | exit 0, 49 mutações mordidas com o marcador certo, controle negativo silencioso |
| `scripts/censo-lastro-do-manuscrito.py` | exit 0 |
| `paper/measurement/recompute-rc4-categories.py --out <scratch>` | exit 0, "§6.4 (v1.0.6 values) reproduced"; o JSON gerado é igual ao `paper/measurement/out/recompute-rc4-categories.json` versionado, sem contar o timestamp. Usei `--out` para não reescrever o arquivo do repo |

## 2. Paridade v1.0.5 → v1.0.6

`parity-v106.py v105-final.md paper/paper-tecnico-nox-mem.md` → **exit 1, PARITY FAILED**.
A causa é o script, não um número fora do lugar. O script é anterior à passagem Codex/Fable:
o regex S2 ainda espera "with a script that recomputes the Section 6 values", que o Codex 5
trocou, e não conhece as 11 linhas de redação. Ver o defeito D2.

Por isso fiz a classificação à mão, diff por linha e multiconjunto de números por linha.
Arquivos: v1.0.5 sha256 `23ddc0e9…be5292` e v1.0.6 sha256 `92c0b8fd…84e2f`. As duas versões
têm 1.441 linhas, e 20 linhas mudaram.

| linha | seção | o que mudou | classe |
|---|---|---|---|
| 7 | front matter | v1.0.5 → v1.0.6, DOI 23146389 → 23147633 | front matter |
| 15 | abstract | 0.406 → 0.403 | substituição do scorer |
| 1016 | §6.3.2 tabela | 0.4061→0.4030, 0.036→0.035, 0.4337→0.4331 | substituições do scorer |
| 1045, 1069 | §6.3.3, §6.3.4 | 0.4337→0.4331, 0.4061→0.4030, 0.5852→0.5842 (×2) | substituições do scorer |
| 1115, 1116, 1120, 1122 | §6.4 | 0.4570→0.4565, +0.093→+0.094, 0.2955→0.2930, +0.142→+0.144 | substituições do scorer |
| 1020 | §6.3.2 Result | +0.119 → +0.123; "declared, and … ablated away" → "declared; with … removed in an ablation, the lead persisted" | scorer + Codex 4 |
| 1024 | §6.3.2 ablação | (0.4337)→(0.4331), 0.4061),→0.4030), + reescrita do parágrafo | scorer + Codex 4 |
| 1022 | §6.3.2 confounds (taxonomia + (e)) | S1 (frase do scorer), S2 reescrita com "132 … twelve groups", Codex 3 (título de (e), "runs against nox-mem", "won anyway", "handicap stands") e Codex 4 ("tested … neutralized" → "probed …, and the lead persisted") | S1/S2 + Codex 3/4/5 |
| 1011, 1018, 1035 | §6.3.2 | "tested/ablated … not to drive the result" → "probed/removed …, the lead persisted" | Codex 4 |
| 1132 | §6.5 princípio 5 | "declared and … ablated away" → "declared; with … removed in an ablation, the lead persisted" | Codex 4 |
| 1156 | §6.7 | "tested … shown not to drive the result" → "probed …, under which … lead persisted" | Codex 4 |
| 1214, 1218 | §7.1 L5, L6 | "ablated and ruled out" → "removed in an ablation, the lead persisted"; "ablated … ruled out" → "probed by ablation, the lead persisted" | Codex 4 |
| 1270 | §8 | "declared and … ablated away" → "declared; with … removed in an ablation, the lead persisted" | Codex 4 |

- **Substituições do scorer:** as 22 esperadas aparecem no diff de palavras com a contagem
  exata de `EXPECTED`: 0.406;, 0.4061 ×3, 0.4061), 0.036, 0.4337 ×3, (0.4337), +0.119,,
  0.5852 ×2, 0.4570, 0.4570;, +0.093, (+0.093)., 0.2955, 0.2955;, +0.142, (+0.142), +0.142).
  Nenhuma está faltando.
- **Linhas de redação:** são 11 (1011, 1018, 1020, 1022, 1024, 1035, 1132, 1156, 1214, 1218,
  1270), exatamente as 11 do `APPLY-CODEX-FABLE.md` (§6.3.2 ×6 contando a taxonomia, §6.5,
  §6.7, §7.1 ×2, §8).
- **Números que entraram** fora das substituições:
  - 1022: S1 (3, 0.004, nove valores, §6.3.2–§6.4, v1.0.6), S2 (DOI 23146656, 132, 6), 20,
    17, 2,482 e 6,822;
  - 1024: 33 e 504.
- **Números que saíram:** só a referência "§6.3 → §6.3.2" da frase removida.
- Nenhum outro número mudou. O "0.34" continua no texto, agora como "The 0.34 pp difference
  does not isolate or bound".

**Números novos conferidos na fonte:**

| número | conferência | resultado |
|---|---|---|
| 20 / 17 (e 3) | `output/rc4/mem0.json`, top 10 por query | 20 listas com id repetido: 3 com id gold repetido e 17 só com não-gold. n = 2.482, k = 10 em todas |
| 33 dense-search errors (504) | `payload/evidence/rc4-ablation-run.redacted.log` | 33 linhas `dense search error: 504 Deadline Exceeded`, e nenhum outro erro denso |
| "fused the FTS5 list alone for that pass" | `adapters/nox_mem.py` (except → `dense_rows` vazio → RRF só com `fts_rows`) | confere |
| "at most 0.004" e "nine printed values" | maior delta: +0.119→+0.123. São 9 valores distintos: R11 e A05 são o mesmo 0.4331 | confere |
| 99.03%, 23 de 2.370 | já estavam na v1.0.5 | sem mudança |

## 3. Varredura das frases antigas

| arquivo | resultado |
|---|---|
| `paper/paper-tecnico-nox-mem.md` | 0 para "ruled out", "at most 0.34", "can only lower", "neutraliz", "ablated away", "won anyway", 0.4337, 0.4061 e +0.119. "rules out" aparece 1× (l.728, multi-hop MuSiQue/HotPotQA, sem relação com o §6). "architectural" aparece 7× (l.268, 287, 482, 735, 791, 793, 912): schema, decisões e composabilidade do §5, nada que atribua o resultado do §6 à arquitetura |
| `paper/abstract.md`, `paper/arxiv-metadata.txt`, `paper/publication/techrxiv-metadata.md` | 0. O 0.403 já está no techrxiv |
| `README.md` | 0 frases antigas. A tabela rc4 e a de n = 2.482 têm 0.4030/0.4331/+0.123; quatro confounds; "the lead persisted" |
| `docs/COMPARISON.md` | 0 frases antigas no bloco rc4 (0.4030/0.4331/+0.123). "Architectural trade-off framing" (l.303) e "architecturally stronger" (l.324, sobre o Zep) não falam do resultado do §6 |
| `docs/*` (resto) | ocorrências só em contextos sem relação (GLOSSARY, plano Q1, press kit) ou em registro datado (HANDOFF l.1496, 2481) |
| README do dataset e `zenodo-metadata.json` | 0.4061/0.4337/+0.119 aparecem só na tabela "old → new" da correção e no exemplo "0.4061 to 0.4030" da descrição, como descrição da correção. Correto |
| `paper/CHANGELOG.md` | ocorrências na entrada v1.0.6 (descrição da correção) e nas entradas históricas rc4 de 2026-06-29/30 (l.192-212: "A vitória é arquitetural", "neutralizado"). São registro datado, não defeito |
| `paper/publication/paper-abstract.md`, `arxiv-submit-metadata.md`, `paper/arxiv-submission-ready.md` | "silent architectural degradation" (tese, sem relação com o §6). O `arxiv-submission-ready.md` está marcado como SUPERSEDED |

Arquivos públicos editados: nenhum host, IP, token nem caminho pessoal. Só aparece o regex
`FORBIDDEN` do `strip_outputs.py` e o e-mail de contato que já estava no `abstract.md`.

## 4. Dataset

| conferência | resultado |
|---|---|
| `verify_dataset.py --manuscript paper/paper-tecnico-nox-mem.md` no `payload/` | exit 0, "135/135 Section 6 values checked and equal to the paper; 12 groups declared not recomputable" |
| idem num unzip novo do `nox-mem-section6-evidence-1.0.0.zip` | exit 0, 135/135 |
| `shasum -a 256 -c SHA256SUMS` (payload e zip extraído) | 0 linhas não-OK. Os 29 arquivos listados cobrem todos os arquivos, exceto o próprio SHA256SUMS. O zip extraído é igual ao `payload/` byte a byte (`diff -rq`) |
| zip | sha256 `993c3453a5af3aebf4b0a6c7bb86fe746e4e9afce62ef2a6e30302408fdcd284` e md5 `3abd9a47823d561ca392f1bb30f0e4e6`, iguais ao pacote. Reconstruí o zip no scratch com o passo 4 do `deposit_draft.py` (determinístico) e cheguei ao **mesmo** sha256, então rodar o passo 5d não muda o hash citado |
| verificador antes de rodar | sem `__pycache__` nem `.DS_Store` no payload depois das execuções |

## 5. Carta (§3.3 do pacote)

**Forma.** O bloco vai de `Submission:` até a assinatura: 1.428 palavras e 8.985 caracteres
(8.986 com o `\n` final). Contagem de caracteres proibidos:

- 0 travessão (e 0 meia-risca);
- 0 asterisco, 0 sublinhado, 0 chave, 0 colchete, 0 `|`;
- 0 `+`, 0 til, 0 crase, 0 aspas curvas;
- 0 caractere não-ASCII;
- nenhum padrão de emoticon ou tachado do Jira.

**Citação da recusa.** "would benefit from additional review and revision that is outside of
the services we provide" está presente, entre aspas retas. Conferi palavra por palavra contra o
e-mail MOD-103264 de 2026-09-03 16:09 UTC no Gmail.

**Fatos conferidos:**

| afirmação | fonte | resultado |
|---|---|---|
| Submitted 1 July 2026 | Gmail, recibo `e-prints@arxiv.org` 2026-07-01 16:04 UTC | ok |
| Declined 3 September 2026, MOD-103264 | Gmail | ok |
| MOD-97655 sent 25 July, answered 11 August | Gmail: pedido 2026-07-25 11:20 UTC, resposta "no final decision" 2026-08-11 | ok |
| MOD-98296 sent 31 July, answered 3 August | Gmail: abertura 2026-07-31 10:27 UTC, resposta 2026-08-03 | ok |
| v1.0.6 (4 October 2026), DOI 10.5281/zenodo.23147633, MD5 5326d437… | front matter e `md5` do PDF | ok, mas o DOI ainda é rascunho (Codex 2, coberto pelos passos 5e/8b) |
| 135 = 132 + 3; 12 grupos; 3 de 2.482; nove valores; ≤ 0.004 | verificador, docstring (X01-X03) e diff | ok |
| 0.6455 / 0.5013 / 0.4546 / 0.4331; 2.482 = 1.982 + 500 | §6.3.3 l.1045 e §6.3.4 l.1068-1069 | ok |
| 0.6237, 99.86% (5.1.3), 58.62, 73.37 (5.2), L8, 3.4.3, 1.4/1.5 | cabeçalhos e corpo do `.md` | ok |
| plano 09c8311, 21 May local, 00:21 UTC 22 May; primeira corrida 23 May | `git show`: 2026-05-21 21:21:58 -0300, 2026-05-22 00:21:58 UTC; §6.7 l.1156 | ok |
| claims_check em 4 September, 21 checks | `9c11c33` 2026-09-04 08:56 -0300; 21 guardas verdes | ok |
| seis revisões de 4/9 a 4/10; seis versões sob 22649268 | CHANGELOG v1.0.1 (04/09) … v1.0.6 (04/10); concept no front matter | ok, mas só vale depois de publicar a 1.0.6 |
| 0.6237 e 0.5013 iguais desde a submissão | último commit do `.md` antes das 14:04 BRT de 1/7 = `5a2071f`: 0.6237 ×7, 0.5013 ×2 | ok |
| agentmemory: só a corrida de 15/06, n = 100 | §6.3 l.951/959/970 | ok |
| **Categories requested: cs.IR (primary), cs.LG (cross-list)** | Gmail, recibo do arXiv de 1/7: **"Categories: cs.IR"** | **diverge: D1** |

## Defeitos

### D1 (alta, carta): a categoria cs.LG não consta no recibo da submissão

- Texto na carta (cabeçalho): `Categories requested: cs.IR (primary), cs.LG (cross-list)`.
- Texto na carta (item 4): `I listed cs.LG for the ablation methodology and have no objection if moderators prefer to drop it.`
- O recibo automático do arXiv de 2026-07-01 (`e-prints@arxiv.org`, assunto "arXiv
  submission submit/7771319") traz a cópia dos metadados com **`Categories: cs.IR`**, sem
  cross-list. O e-mail de status que você mandou em 25/07 dizia "cs.IR primary, cs.LG and cs.AI
  cross-list". O `paper/arxiv-metadata.txt` e a memória dizem cs.IR + cs.LG. São três versões
  diferentes. O moderador vai ver a submissão com as categorias dela, e uma afirmação errada
  sobre ela, logo no cabeçalho, custa credibilidade.
- Correção: conferir no dashboard do arXiv (`arxiv.org/user/`, submit/7771319) as categorias
  registradas.
  - Se for só cs.IR: cabeçalho `Category requested: cs.IR`, apagar a última frase do item 4,
    e corrigir a §3.5 do pacote (fonte = recibo do arXiv) e o passo 4 do checklist.
  - Se houver cross-list: listar exatamente o que está lá.

### D2 (média, lastro): `parity-v106.py` e `PARITY.txt` não valem para o texto final

- O CHANGELOG (l.76-80) diz: "Parity v1.0.5 → v1.0.6: with the version line and the two
  sentences masked, a word-level diff of the whole document holds exactly the 22 listed
  substitutions and nothing else … output `PARITY.txt` beside it".
- O `PARITY.txt` (20:56) foi medido num texto intermediário (sha256 `76d01388…`). O manuscrito
  final (`92c0b8fd…`) faz o script sair com **exit 1**:
  - S2 não é encontrado ("with a script that recomputes" virou "with a verifier that checks 132");
  - aparecem 22 substituições extras e 31 edições que não são substituição, todas das 11 linhas
    Codex/Fable.
- A classificação manual da §2 mostra que nada fora do previsto mudou. Mesmo assim, o artefato
  que o CHANGELOG público cita não reproduz o que afirma sobre a v1.0.6 que vai ser publicada.
- Correção, antes do PR:
  - atualizar `S2_NEW_RE` para a frase nova;
  - acrescentar uma perna para as 11 linhas de redação (linha permitida + multiconjunto de
    números da linha, com os números novos esperados 132, 20, 17, 33, 504, 6,822, 2,482 e a
    saída de "§6.3 → §6.3.2");
  - regenerar o `PARITY.txt` contra o `.md` final;
  - no CHANGELOG, dizer que a paridade cobre as duas passagens, ou separar "22 substituições
    (texto intermediário `76d01388…`)" de "11 linhas de redação (texto final `92c0b8fd…`)".
- Ajustar também o `SCORER-FIX.md` l.231, que cita o mesmo `PARITY.txt`.

### O1 (baixa, redação, sem número): "known to favor"

- l.1018 e l.1214 trocaram "the one configuration asymmetry that favored nox-mem" por
  "the one asymmetry **known** to favor nox-mem".
- O parágrafo da ablação (l.1024) agora diz que os 0.34 pp "do not isolate or bound the
  task-type contribution". Então o favorecimento é uma premissa de projeto (task types
  otimizados para retrieval), não algo medido, e "known" diz mais do que o texto sustenta.
- Esta troca não está enumerada no `APPLY-CODEX-FABLE.md`, embora fique dentro das linhas do
  Codex 4.
- Correção sugerida: "the one asymmetry that favors nox-mem by design (task type)", ou voltar
  para "that favored".

## Notas sem ação

- O Gmail tem também o **MOD-97656**: ticket duplicado criado pelo mesmo e-mail de 25/07, que
  só recebeu resposta automática. A carta não precisa citá-lo.
- O passo 1 do pedido ("rebuild") não deve ser feito no lugar: o MD5 da carta só continua
  válido se o PDF de 21:35 não for regenerado (passo 5b).
- Os passos 5a a 5e continuam pendentes: merge do PR, troca do PDF e do zip nos rascunhos
  23147633 e 23146656, e publicação. A carta afirma DOIs e "six versions" que só passam a valer
  depois disso.
