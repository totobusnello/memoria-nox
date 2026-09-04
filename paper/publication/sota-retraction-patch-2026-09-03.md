# Patch de retratação — a alegação "dual SOTA" em MuSiQue/HotPotQA

> **v2 — 2026-09-03, pós revisão adversarial (Fable).** A v1 continha três defeitos
> próprios, dois deles da mesma classe que este patch corrige: rotulava números de
> **test** como **dev** nas tabelas de substituição, e defendia a §5.4 com uma subtração
> **cross-metric** (F1 menos strict EM). Ambos corrigidos abaixo e **registrados em vez
> de apagados**. O censo da v1 também subdimensionou o escopo: são ~26 sítios, não 13.
>
> ⚠️ **Reponderação de causa.** A v1 tratava o "dual SOTA" como causa provável da
> rejeição do arXiv. A revisão argumenta, e eu concordo, que **moderação raramente
> verifica claims de benchmark** — ela triagem por **gênero**. O que ela vê é: abstract
> de 695 palavras num parágrafo, 15 referências para 26 mil palavras, ausência de Related
> Work própria, autorótulo "Technical report" na linha 3, sete seções finais de
> documentação de produto, tabela PASS/FAIL julgando concorrentes, e evidência citada
> como `PR #407`. **Este patch é necessário e insuficiente**: ele conserta o defeito mais
> grave de conteúdo, não o filtro que provavelmente barrou a submissão. A reforma de
> gênero é trabalho separado — e, dado que a apelação é de uso único, é ela que decide se
> o journal aceita.

**Data:** 2026-09-03 · **Motivo:** rejeição do arXiv (`submit/7771319`), motivo declarado
*"would benefit from additional review and revision"*. Este é o defeito de maior risco
encontrado ao reler o paper com a lente da moderação.

> ⚠️ **Não é erro de medição.** 58,62 e 73,37 seguem valendo como medidos. O que não se
> defende é a **atribuição de SOTA** — e, por consequência, um argumento a jusante.

---

## 1. O fato

| benchmark · métrica | paper (**dev**) | SOTA publicado (**test**) | gap |
|---|---:|---|---:|
| MuSiQue-Ans, answer F1 | **58,62** | **69,2** — Beam Retrieval, Table 4, *test set* (NAACL 2024, arXiv:2308.08973) | **−10,58** |
| HotPotQA distractor, answer F1 | **73,37** | **85,04** Beam Retrieval, Table 5, *blind test* · **84,44** FE2H-ALBERT (leaderboard hotpotqa.github.io) | **−11,67** |

⚠️ **Os splits diferem** — nosso número é dev, o do SOTA é test, e não existe answer F1 de
dev publicado para o Beam Retrieval (ver adiante). Isso tem de ser dito em cada citação.
Não altera a retratação: a variância dev/test é ~1 pp contra um gap de 10-12 pp.

**O elo que fecha o caso:** Beam Retrieval reporta a melhora de **49,0 → 69,2** em
MuSiQue. Esse 49,0 é o **EX(SA)** — precisamente o baseline que a §5.2.1 descreve como
*"the strongest specialized multi-hop reader in the MuSiQue paper"*. O baseline foi
superado em 2023, por trabalho peer-reviewed (NAACL 2024 main), três anos antes desta
submissão.

Os parênteses do paper são verdadeiros: 73,37 **está** acima de DPR+FiD, 58,62 **está**
acima de IRCoT e de EX(SA). O rótulo "SOTA" é que não sustenta, e é falsificável em
trinta segundos por qualquer revisor de cs.IR — está no **abstract**, duas vezes.

### 🔴 RESOLVIDO — e ao contrário do que esta seção dizia na v1 deste patch

**Os dois números de SOTA são TEST, não dev.** Verificado no fonte primário
(arxiv.org/html/2308.08973v2), legendas literais:

- **Table 4:** *"Overall performance on the **test set** of MuSiQue-Ans."* → 69,2 = An F1, **test**
- **Table 5:** *"Overall performance on the **blind test set** of HotpotQA..."* → 85,04 = Ans F1, **blind test**
- **Table 3:** *"**Retrieval** performance on the **development set**..."* → o dev do Beam
  Retrieval reporta **retrieval** EM/F1 (77,37/79,31), **não** answer F1

E §4.3 confirma a métrica: *"For MuSiQue-Ans, we report the standard F1-based metrics for
the answer (An) and support passage identification (Sp)"*.

⇒ **Não existe answer F1 de dev publicado para o Beam Retrieval.** A instrução da v1
deste patch — "pinar o dev do arXiv" — era **inexequível**, e a afirmação "para MuSiQue o
69,2 já é dev, comparação limpa" era **falsa**.

> 🔴 **Este patch continha o defeito que ele corrige.** A v1 colocava 69,20 e 85,04 sob
> os cabeçalhos `Dev F1` e `Dev distractor ans_F1` das tabelas de substituição — isto é,
> reintroduzia a comparação cross-split enquanto retratava uma comparação cross-metric.
> Achado por revisão adversarial independente (Fable), não por mim. Registra-se aqui em
> vez de se apagar, porque a taxa em que uma correção introduz o próprio defeito que
> corrige é ela própria um dado — é o argumento do §6 do Paper A.

**Como fica:** citar como **test**, com o split declarado em cada célula, e declarar que
a comparação é dev(nosso) × test(SOTA). A variância dev/test em HotPotQA é da ordem de
~1 pp, muito menor que o gap de 10-12 pp, então **a retratação não muda** — o que muda é
que ela passa a ser honesta sobre o próprio split.

### ⚠️ Diferença de protocolo, a declarar junto

Beam Retrieval opera com candidate set **por pergunta** de `n` entre 10 e 20 (§5, "the
candidate set size n ranges from 10 to 20"); nox-mem usa `top_k=20` sobre "full paragraph
corpus". Pode ou não ser o mesmo conjunto efetivo (MuSiQue-Ans fornece ~20 parágrafos por
pergunta). **Não verificado.** Não ressuscita o rótulo SOTA em nenhuma direção — mas é
mais uma razão para a comparação ser qualificada em vez de rotulada.

### O confundidor metodológico, que um revisor vai levantar de todo modo

nox-mem usa **GPT-4.1-mini** como backbone de geração. IRCoT (2022), EX(SA) (2022) e
DPR+FiD (2020) são leitores especializados de época anterior. Bater um leitor de 2022 com
um backbone de 2025 mede sobretudo **progresso de backbone**, não a contribuição do
desenho de retrieval. Os deltas de +22,82 pp e +8,92 pp não são atribuíveis ao retrieval.
Isso precisa estar escrito, não só o número.

---

## 2. Substituições exatas

### 2.1 Abstract (linha 15)

**DE:**
> On classical multi-hop QA, nox-mem achieves dual SOTA without specialized fine-tuning: **MuSiQue dev F1 58.62%** (+22.82 pp over IRCoT, +8.92 pp over EX(SA); §5.2.1) and **HotPotQA dev distractor ans_F1 73.37%** (above DPR+FiD reader SOTA; §5.2.2).

**PARA:**
> On classical multi-hop QA, general-purpose hybrid retrieval with an off-the-shelf backbone and no benchmark-specific fine-tuning reaches **MuSiQue-Ans dev answer F1 58.62%** and **HotPotQA distractor dev answer F1 73.37%** — above the specialized multi-hop readers these datasets are conventionally compared against (EX(SA) 49.70, IRCoT 35.80, DPR+FiD 65–72), and roughly 10 and 12 points below the current published state of the art (Beam Retrieval, 69.2 on MuSiQue-Ans test and 85.04 on the HotPotQA blind test; split-matched dev answer F1 is not published for that system). Because our reader is three years newer than those baselines, the margins over them are not attributable to the retrieval design (§5.2).

### 2.2 §5.2 título (linha 598)

**DE:** `### 5.2 Classical multi-hop QA — MuSiQue and HotPotQA dual SOTA`

**PARA:** `### 5.2 Classical multi-hop QA — competitive without fine-tuning, below current SOTA`

### 2.3 §5.2 abertura (linha 602)

**DE:**
> The result: nox-mem achieves SOTA on both benchmarks without specialized fine-tuning.

**PARA:**
> The result: on both benchmarks nox-mem performs multi-hop QA competently without any benchmark-specific fine-tuning, landing above the specialized multi-hop readers conventionally used as reference points for each dataset, and below the current state of the art. The purpose here is diagnostic — establishing whether multi-hop composition is a capability floor for the system — not a leaderboard claim.

⚠️ Não escrever "readers published with the benchmark" englobando DPR e FiD: **DPR
(2020) e FiD (2021) não foram publicados com o HotPotQA (2018)** — são sistemas
posteriores e de propósito geral. O leitor original do dataset é o BERT reader (~58). A
formulação da v1 deste patch cometia esse erro; achado pela revisão adversarial.

### 2.4 §5.2.1 título (linha 604)

**DE:** `#### 5.2.1 MuSiQue — F1 58.62% beats IRCoT and EX(SA)`

**PARA:** `#### 5.2.1 MuSiQue-Ans dev — answer F1 58.62%, above EX(SA), below Beam Retrieval`

### 2.5 §5.2.1 tabela (linhas 608-612) — acrescentar a linha do SOTA

| System | Split | Answer F1 | Δ vs nox-mem | Source |
|---|---|---:|---:|---|
| Beam Retrieval (Zhang et al., NAACL 2024) | **test** | **69.20%** | **+10.58 pp** | Table 4 (arxiv:2308.08973) |
| **nox-mem (hybrid, no rerank)** | **dev** | **58.62%** | — | §5.2.1 |
| EX(SA) (Trivedi et al. 2022) | dev | 49.70% | −8.92 pp | MuSiQue paper (arxiv:2108.00573) |
| IRCoT (Trivedi et al. 2023) | dev | 35.80% | −22.82 pp | IRCoT paper (arxiv:2212.10509) |

⚠️ A linha do Beam Retrieval é **test**; as demais são dev. Beam Retrieval publica dev
apenas para **retrieval** (Table 3: EM 77,37 / F1 79,31), não para answer — logo não há
linha split-matched a citar. Declarar isso na legenda da tabela, não omitir.

### 2.6 §5.2.1 prosa (linha 614)

**DE:**
> The +22.82 pp gap over IRCoT and +8.92 pp gap over EX(SA) (the strongest specialized multi-hop reader in the MuSiQue paper) are unambiguous SOTA on the dev set. nox-mem's gain stems from two structural factors:

**PARA:**
> nox-mem lands above both readers published with the benchmark, and 10.58 pp below Beam Retrieval, the current published state of the art on this split and metric. Two cautions apply to the margins over EX(SA) and IRCoT. First, both are 2022 systems, while nox-mem's reader is GPT-4.1-mini: the comparison confounds retrieval design with three years of backbone progress, and we do not claim the delta measures the former. Second, EX(SA) at 49.70 is the baseline Beam Retrieval itself improved upon (49.0 → 69.2), so "strongest specialized reader in the MuSiQue paper" is a statement about that paper, not about the field. What the number does support is narrower and sufficient for §5.4: multi-hop composition is not a capability floor for this pipeline. Two structural factors contribute:

### 2.7 §5.2.2 título (linha 621)

**DE:** `#### 5.2.2 HotPotQA — ans_F1 73.37% above DPR+FiD reader SOTA`

**PARA:** `#### 5.2.2 HotPotQA distractor — answer F1 73.37%, above DPR+FiD, below Beam Retrieval and FE2H`

### 2.8 §5.2.2 tabela (linhas 625-629) — acrescentar as linhas do SOTA

| System | Split | Answer F1 | Δ vs nox-mem | Source |
|---|---|---:|---:|---|
| Beam Retrieval (Zhang et al., NAACL 2024) | **blind test** | **85.04%** | **+11.67 pp** | Table 5 (arxiv:2308.08973) |
| FE2H on ALBERT | **blind test** | 84.44% | +11.07 pp | hotpotqa.github.io leaderboard |
| **nox-mem (hybrid, no rerank)** | **dev** | **73.37%** | — | §5.2.2 |
| DPR+FiD reader (range, published) | dev | 65–72% | −1.37 to −8.37 pp | DPR (arxiv:2004.04906) + FiD (arxiv:2007.01282) |
| BERT reader, original dataset baseline (Yang et al. 2018) | dev | ~58% | −15+ pp | HotPotQA paper (arxiv:1809.09600) |

⚠️ As duas linhas de topo são **blind test** — o leaderboard oficial do HotPotQA só
reporta test. Declarar na legenda.

### 2.9 §5.2.2 prosa (linha 631)

**DE:**
> The ans_F1 of 73.37% sits above the published DPR+FiD reader SOTA range without specialized training or HotPotQA-specific fine-tuning. The result corroborates §5.2.1: nox-mem's general-purpose hybrid retrieval + GPT-4.1-mini generation achieves classical multi-hop QA SOTA without bespoke pipelines.

**PARA:**
> The answer F1 of 73.37% sits above the DPR+FiD reader range without specialized training or HotPotQA-specific fine-tuning, and 11.7 points below the leaderboard's leading entries. The result corroborates §5.2.1 in the narrow sense that matters for §5.4: general-purpose hybrid retrieval with an off-the-shelf reader clears classical multi-hop QA competently, well short of purpose-built systems that optimize the retrieval chain end-to-end for these datasets.

### 2.10 §5.2.3 título e prosa (linhas 633, 639)

**Título DE:** `#### 5.2.3 Why classical-QA SOTA matters for the F_MH narrative`
**Título PARA:** `#### 5.2.3 What the classical-QA results do and do not license for the F_MH narrative`

**Prosa DE (linha 639):**
> On benchmarks where multi-hop reasoning quality is the question and corpus structure is friendly to general-purpose hybrid retrieval (MuSiQue, HotPotQA), nox-mem is SOTA. The EverMemBench F_MH gap is therefore not a reasoning ceiling — it is a structural challenge specific to the EverMemBench task setup. §5.4 develops this in detail.

**Prosa PARA:**
> On benchmarks where multi-hop reasoning quality is the question and corpus structure is friendly to general-purpose hybrid retrieval (MuSiQue, HotPotQA), nox-mem performs in the same regime as published specialized systems, without matching the leaders. That licenses a bounded claim — multi-hop composition is not where this pipeline fails — and not an unbounded one. The 10–12 pp shortfall against Beam Retrieval means classical multi-hop still has headroom for this system too, so the EverMemBench F_MH gap cannot be attributed to task structure alone on the strength of these two results. §5.4 develops what remains.

---

## 3. 🔴 §5.4 — o argumento que depende da premissa retratada

Este é o motivo pelo qual o patch não pode parar na §5.2. A linha 696 é um *modus
tollens* cuja premissa é o SOTA, e a conclusão dele aparece **no abstract**.

### 3.1 Tabela da §5.4 (linhas 688-694) — a coluna "Reader SOTA range" está errada

As duas primeiras linhas omitem Beam Retrieval e FE2H, e o veredito é falso:

| Benchmark | nox-mem | ~~Reader SOTA range~~ | ~~Verdict~~ |
|---|---|---|---|
| MuSiQue dev | 58,62% | ~~35,80–49,70~~ → **69,20 (Beam Retrieval)** | ~~**nox-mem SOTA**~~ → **−10,58 pp vs SOTA; +8,92 vs EX(SA)** |
| HotPotQA dev distractor | 73,37% | ~~65–72 (DPR+FiD)~~ → **85,04 (Beam Retrieval)** | ~~**nox-mem SOTA**~~ → **−11,67 pp vs SOTA; acima de DPR+FiD** |

Renomear a coluna de `Reader SOTA range` para `Published SOTA (split/metric-matched)` e
acrescentar uma coluna `Original benchmark reader`, para que as duas comparações fiquem
visivelmente separadas — foi a fusão delas numa só coluna que produziu o veredito falso.

### 3.2 Prosa da §5.4 (linha 696)

**DE:**
> **If nox-mem's multi-hop reasoning were structurally weak, the MuSiQue and HotPotQA SOTA results would not be possible.** They demonstrate the reverse: nox-mem's hybrid retrieval + GPT-4.1-mini reader pipeline is SOTA on the canonical multi-hop QA benchmarks. The LoCoMo retrieval ceiling at 74.52% strict (82.21% multi-hop sub-track) further confirms that multi-hop retrieval over long conversations is achievable.

**PARA:**
> If nox-mem's multi-hop reasoning were structurally weak, the MuSiQue and HotPotQA results would sit near the original benchmark readers rather than well above them. They do not: the pipeline composes multi-hop answers competently on both. That rules out a wholesale reasoning failure as the explanation for F_MH, which is what the F_MH argument requires. It does **not** establish that classical multi-hop is saturated for this system — the 10–12 pp shortfall against Beam Retrieval says the opposite — so the contrast with EverMemBench F_MH is a contrast between *competent-with-headroom* and *3–7%*, not between *solved* and *broken*. The LoCoMo retrieval ceiling at 74.52% strict (82.21% multi-hop sub-track) further confirms that multi-hop retrieval over long conversations is achievable.

### 3.3 O que sobrevive, e o que precisa da sua decisão

**Sobrevive, mas NÃO pelo argumento que a v1 deste patch usou.**

> 🔴 **Retratação dentro da retratação.** A v1 defendia a §5.4 assim: *"um sistema 10 pp
> abaixo do SOTA em MuSiQue ainda está a ~55 pp dos 3–7% — assimetria de ordens de
> magnitude"*. Essa aritmética **subtrai F1 (partial credit) de strict EM**. É uma
> subtração cross-metric usada para defender uma retratação de overclaim cross-metric —
> e o próprio paper lista *"strict scoring"* como mecanismo #2 do gap F_MH (linha 701),
> ou seja, contradiz a conta na mesma seção. Achado pela revisão adversarial (Fable).
> **Não usar aritmética de pp entre F1 e EM em nenhuma versão do texto.**

**O que sobrevive é o argumento qualitativo:** uma falha grosseira de composição
multi-hop apareceria também em MuSiQue e HotPotQA, e não aparece. Isso exclui falha
atacadista de raciocínio como explicação do F_MH — que é tudo de que a §5.4 precisa.

**✅ Âncora melhor, same-metric, custo zero de medição** (proposta pela revisão
adversarial e adotada): a dificuldade do F_MH já tem comparador no **mesmo benchmark e na
mesma métrica** — **MemOS a 18,88%** (linha 694, MemOS Table 4). Um teto de 18,88% em
strict EM no F_MH, contra 3–7% nosso, situa o gap sem sair da métrica e sem depender de
MuSiQue. Usar essa âncora como quantificação e o resultado clássico apenas como
exclusão qualitativa de falha de raciocínio.

A §5.4 já termina dizendo *"the paradox is therefore refined rather than dissolved"*,
então o gancho para a versão mais fraca já existe no texto.

**🔴 Precisa da sua decisão:** o abstract afirma que a §5.4 *"shows the 3–7% absolute is
a corpus-structural property, not a multi-hop reasoning ceiling"*. Com a retratação, o
"not a reasoning ceiling" continua defensável, mas o "corpus-structural **property**"
fica mais forte do que a evidência permite — havendo 10–12 pp de headroom no cenário
clássico, parte do gap pode ser do sistema e não do corpus. Duas saídas, e a escolha é
sua porque muda o que o paper afirma, não só como afirma:

- **(a) conservadora** — "is not primarily a multi-hop reasoning failure" e retirar
  "corpus-structural property" do abstract, mantendo os quatro mecanismos da §5.4 como
  explicação *proposta*;
- **(b) manter a força** — e então a §5.4 precisa de evidência nova que separe corpus de
  sistema (ex.: rodar o mesmo pipeline em F_MH com o backbone que fecha o gap clássico).
  É trabalho de medição, não de redação.

Recomendo **(a)**: é honesta, não custa medição, e o argumento sobrevive por margem
larga. A (b) é um experimento legítimo, mas não deve bloquear a submissão.

---

## 4. `refs.bib` — entradas a acrescentar

Os cinco baselines estão sourceados inline por arXiv ID, mas **nenhum está no
`refs.bib`** (15 entradas, nenhuma de MuSiQue, HotPotQA, IRCoT, EX(SA), DPR, FiD). Não é
fabricação — é citação inline sem entrada bibliográfica. Um journal devolve por isso.

```bibtex
@inproceedings{zhang2024beamretrieval,
  author    = {Zhang, Jiahao and Zhang, Haiyang and Zhang, Dongmei and Liu, Yong and Huang, Shen},
  title     = {End-to-End Beam Retrieval for Multi-Hop Question Answering},
  booktitle = {Proceedings of NAACL 2024},
  year      = {2024},
  eprint    = {2308.08973},
  archivePrefix = {arXiv},
  url       = {https://aclanthology.org/2024.naacl-long.96/}
}

@article{trivedi2022musique,
  author  = {Trivedi, Harsh and Balasubramanian, Niranjan and Khot, Tushar and Sabharwal, Ashish},
  title   = {{MuSiQue}: Multihop Questions via Single-hop Question Composition},
  journal = {Transactions of the Association for Computational Linguistics},
  volume  = {10}, year = {2022}, eprint = {2108.00573}, archivePrefix = {arXiv}
}

@inproceedings{trivedi2023ircot,
  author    = {Trivedi, Harsh and Balasubramanian, Niranjan and Khot, Tushar and Sabharwal, Ashish},
  title     = {Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions},
  booktitle = {Proceedings of ACL 2023},
  year      = {2023}, eprint = {2212.10509}, archivePrefix = {arXiv}
}

@inproceedings{yang2018hotpotqa,
  author    = {Yang, Zhilin and Qi, Peng and Zhang, Saizheng and Bengio, Yoshua and Cohen, William W. and Salakhutdinov, Ruslan and Manning, Christopher D.},
  title     = {{HotpotQA}: A Dataset for Diverse, Explainable Multi-hop Question Answering},
  booktitle = {Proceedings of EMNLP 2018},
  year      = {2018}, eprint = {1809.09600}, archivePrefix = {arXiv}
}

@inproceedings{karpukhin2020dpr,
  author    = {Karpukhin, Vladimir and O\u{g}uz, Barlas and Min, Sewon and Lewis, Patrick and Wu, Ledell and Edunov, Sergey and Chen, Danqi and Yih, Wen-tau},
  title     = {Dense Passage Retrieval for Open-Domain Question Answering},
  booktitle = {Proceedings of EMNLP 2020},
  year      = {2020}, eprint = {2004.04906}, archivePrefix = {arXiv}
}

@inproceedings{izacard2021fid,
  author    = {Izacard, Gautier and Grave, Edouard},
  title     = {Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering},
  booktitle = {Proceedings of EACL 2021},
  year      = {2021}, eprint = {2007.01282}, archivePrefix = {arXiv}
}
```

⚠️ Conferir autor/venue de cada entrada contra o arXiv antes de compilar — escrevi a
partir dos IDs que o paper já cita, e entrada bibliográfica errada é o mesmo defeito
numa camada diferente.

---

## 5. Varredura executada — 11 alegações de SOTA próprio, em 37 linhas com a palavra

Censo em `measurement`-style (frase a frase, separando SOTA **próprio** de SOTA de
terceiros, que é legítimo e fica):

| linha | sítio | coberto pelas §§2-3? |
|---|---|---|
| 598, 602, 631, 639 | §5.2 títulos e prosa | ✅ §2 |
| 688, 690, 691, 696 | §5.4 tabela e *modus tollens* | ✅ §3 |
| **594** | 🔴 **terceiro sítio da cadeia §5.2→§5.4** | ❌ **ver §5.1** |
| **15, 579** | 🔴 **claim SEPARADO: "both SOTA" vs MemOS** | ❌ **ver §5.2** |
| **327-331, 336, 341** | 🔴 bloco de highlights — inclui o SOTA cross-metric que o honesty pass matou | ❌ **ver §5.4** |
| **550, 556, 557, 562** | 🔴 **§5.1.10 — a seção-FONTE do claim MemOS** | ❌ **ver §5.4** |
| **749, 891, 1004, 1005, 1017** | 🔴 "12 SOTA-tier dimensions", "above published reader SOTA", cross-metric | ❌ **ver §5.4** |

### 5.1 🔴 Linha 594 — o sítio que eu havia perdido

A cadeia de dependência tem **três** pontos, não dois. Eu patchei §5.2.3 (639) e §5.4
(696) e a varredura mecânica achou um terceiro:

Lida por inteiro, é **a forma canônica** da inferência — com `therefore`, e usando a
mesma expressão "corpus-structural property" que a §3.3 questiona no abstract:

**DE:**
> **Reframing (see §5.4):** the §5.2 classical multi-hop QA results (MuSiQue F1 58.62%, HotPotQA ans_F1 73.37%) demonstrate that nox-mem's multi-hop reasoning **is SOTA on standard benchmarks** — the EverMemBench F_MH 3–7% absolute is **therefore** a *corpus-structural* property (very long conversation chains + strict scoring + entity-anchor sparsity), not a multi-hop reasoning ceiling. The §5.4 section resolves this paradox in detail.

**PARA:**
> **Reframing (see §5.4):** the §5.2 classical multi-hop QA results (MuSiQue-Ans dev answer F1 58.62%, HotPotQA distractor answer F1 73.37%) place nox-mem's multi-hop reasoning well above the readers published with each benchmark and 10–12 points below current SOTA — competent, with headroom. That rules out a wholesale multi-hop reasoning failure as the explanation for the EverMemBench F_MH 3–7% absolute, and points to the task setup (very long conversation chains + strict scoring + entity-anchor sparsity) as the leading candidate; it does not establish that the corpus accounts for the whole gap. The §5.4 section develops what the evidence supports.

⚠️ Esta é a linha que fixa a versão de **§3.3**: se você escolher a saída (a), o
`therefore ... corpus-structural property` sai daqui, do abstract **e** da §5.4 — os três
dizem a mesma coisa e têm de mudar juntos, senão sobra um cache não invalidado.

> ⚠️ Isto é a lição `a-defect-class-does-not-stay-fixed-where-it-was-found` acontecendo
> **dentro deste próprio patch**: eu localizei o defeito por leitura, corrigi dois
> sítios, e só o censo mecânico achou o terceiro. Revisão adversarial e censo mecânico
> pegam classes disjuntas — não substituir um pelo outro.

### 5.2 🔴 Claim separado: "both SOTA" contra MemOS (linhas 15 e 579)

Mesma classe de defeito, benchmark diferente, e **não coberto** por nada acima:

> **63.28% Overall + 88.42% Memory Awareness composite with Gemini-3-flash — both SOTA versus the published MemOS Table 4 baseline (GPT-4.1-mini)** (+20.73 pp Overall, +32.74 pp MA)

O parêntese é honesto e nomeia o backbone do baseline — e é exatamente ele que invalida
o rótulo: compara **nox-mem em Gemini-3-flash** contra **MemOS em GPT-4.1-mini**. Bater
o número publicado de alguém rodando num backbone mais forte não é SOTA, é comparação
cross-backbone. O próprio paper mede esse efeito na §5.5.4-§5.5.8 (transferência de 0-40%
entre backbones), então o rótulo contradiz a sua própria seção de composabilidade.

✅ **Crédito onde é devido, e isto alivia o conserto:** a linha 579 vive dentro de um
parágrafo intitulado **"Important caveats on backbone choice"** que já faz o trabalho
honesto — explicita que o Full Context do Gemini-3-flash foi zona de catástrofe para
MemOS (−13 a −21 pp), que nox-mem não regride, e **declara qual comparação considera
válida** ("spans Gemini-2.5-flash, GPT-4.1-mini, and Gemini-3-flash"). O defeito é
apenas as **duas palavras finais**. Acrescentar prosa explicativa aqui duplicaria o que o
parágrafo já diz.

**Conserto mínimo na 579:** `but reaches 63.28% Overall and 88.42% MA composite, both
SOTA.` → `but reaches 63.28% Overall and 88.42% MA composite — above every MemOS Table 4
number, which were obtained on GPT-4.1-mini.`

**Distinção importante — os dois claims não têm o mesmo status:**

| | MuSiQue / HotPotQA | MemOS / EverMemBench |
|---|---|---|
| status | 🔴 **demonstravelmente falso** — abaixo de SOTA publicado em leaderboard oficial | ⚠️ **rótulo metodologicamente inválido** — cross-backbone, não falsificável em leaderboard |
| conserto | retratar e citar o SOTA real | retratar o rótulo; o número e o delta ficam, com a diferença de backbone explícita |

Sugestão de texto para 15 e 579: trocar `both SOTA versus the published MemOS Table 4
baseline (GPT-4.1-mini)` por `above the published MemOS Table 4 numbers, which were
obtained on GPT-4.1-mini; the backbone differs and §5.5.4-§5.5.8 measure how much that
alone can account for`.

### 5.4 🔴 Os ~15 sítios que o meu censo ACHOU e o meu classificador DESCARTOU

Isto não foi falha de `grep`. O censo da v1 **encontrou todas estas linhas** e as jogou
num balde rotulado *"SOTA de terceiros / ambíguo — 26 linhas, legítimo"*, que eu reportei
**sem inspecionar uma única**. A heurística de regex decidia "é SOTA de terceiro" pela
presença de `MemOS|Mem0|DPR|IRCoT|published|baseline` na frase — e quase toda alegação
própria menciona o baseline que ela alega bater. O filtro estava **anticorrelacionado**
com o que devia detectar.

> ⚠️ `invariante verificado sobre o conjunto errado`. Não basta o censo varrer o corpus
> certo: o **classificador** tem de ser testado contra casos que ele deve pegar. Zero dos
> 26 foram lidos antes de eu escrever "legítimo".

| linha(s) | o que está lá | por que importa |
|---|---|---|
| **327-331, 336, 341** | bloco de highlights: "MuSiQue SOTA", "HotPotQA SOTA", "LoCoMo retrieval@10 SOTA ... above Mem0 SOTA F1 66.88%", "prove multi-hop reasoning is SOTA" | 🔴 O terceiro é o **SOTA cross-metric retrieval@10-vs-answer-F1** que o honesty pass de 07-01 registrou como MORTO. Sobreviveu no bloco de highlights — quinta ocorrência da classe |
| **550, 556, 557, 562** | §5.1.10: título "SOTA on EverMemBench", células "+20.73 pp SOTA" / "+32.74 pp SOTA", prosa "yield SOTA" | 🔴 É a **seção-fonte** do claim que §5.2 deste patch trata nas linhas 15 e 579. Consertar o derivado e deixar a fonte é literalmente a lição que este patch cita |
| **749, 891, 1004, 1005, 1017** | "12 SOTA-tier dimensions", "above published reader SOTA", cross-metric de novo | inventário superlativo disperso; tratar com o mesmo critério das §§2-3 |

**Verificado por leitura direta** (não aceito de segunda mão):

- **329** — `**MuSiQue SOTA (multi-hop QA, classical):** dev F1 **58.62%** = **+22.82 pp vs IRCoT 35.80%** ... (PR #407).` ✅ confere
- **336** — `MuSiQue 58.62% F1 and HotPotQA 73.37% ans_F1 **prove multi-hop reasoning is SOTA**` ✅ confere, e é **pior que a 594**: usa `prove`. **Quarto** ponto da cadeia
- **550** — título `#### 5.1.10 Backbone Matrix — Gemini-3-flash SOTA on EverMemBench` ✅
- **556** — célula de tabela `| **+20.73 pp SOTA** |` ✅
- **1004** — na **Conclusão** (§15): `both above published reader SOTA ... validating the architecture's multi-hop reasoning quality` ✅ **quinto** ponto da cadeia
- **891** — ⚠️ **não confirmado.** A revisão citou "12 SOTA-tier dimensions"; a linha que
  eu li fala de *"five paper-worthy findings"*. Pode estar adiante na linha (é longa) ou
  ser citação trocada. Reler antes de editar.

⇒ **A cadeia §5.2→§5.4 tem CINCO sítios** (336, 594, 639, 696, 1004), não três. A versão
adotada em §3.3 tem de ser escrita em todos os cinco, ou sobra cache não invalidado.

**Ordem de conserto:** §5.1.10 (550-562) **antes** das linhas 15 e 579, porque estas
derivam dela. Depois o bloco de highlights (327-341), que é o que um revisor lê primeiro,
e por último a Conclusão (1004).

### 5.4-bis 🔴 Defeito independente achado no caminho: a evidência é citada como "PR #407"

As linhas 329, 606 e 623 sourceiam números de manchete a **`PR #407` / `PR #408`** —
identificadores internos de pull request. Nenhum leitor externo pode resolvê-los, e num
repo privado nem existiriam. Não é overclaim; é **evidência não-arquivável**, e o
sintoma que um moderador vê é o mesmo de referência inventada.

**Conserto:** trocar por artefato citável (o `audits/2026-05-30-musique-dev-full.md` que
a §5.2.1 já menciona serve, se for depositado junto) ou por commit `sha256`-pinado, no
padrão que o Paper A usa. Achado pela revisão adversarial.

### 5.5 Guarda contra reincidência

O honesty pass de 2026-07-01 já matou esta mesma classe **três vezes** (coluna Δ de
retrieval@10-vs-answer-F1; SOTA cross-metric da tabela §5.4; "Production SOTA" da §5.7).
A quarta ficou por decisão — e a §5.4 acima mostra que uma delas **ressuscitou** no bloco
de highlights (linha 329). É a lição
`a-defect-class-does-not-stay-fixed-where-it-was-found`, e o custo desta foi a submissão.

**O guarda NÃO pode ser "SOTA perto de nox-mem sem baseline nomeado"** — foi exatamente
essa a heurística que falhou na §5.4, porque toda alegação própria nomeia o baseline que
alega bater. Especificação correta, no estilo do `claims_check.py` do Paper A:

1. **Lista fechada:** manter um arquivo com as linhas onde `SOTA` é permitido e o motivo.
   Qualquer ocorrência fora da lista **falha**. Reduz o problema de classificar (frágil)
   a enumerar (verificável).
2. **Split e métrica obrigatórios:** toda comparação numérica contra sistema externo tem
   de citar split (`dev`/`test`) e métrica na mesma célula. Falha se um número de
   terceiro aparecer sem os dois.
3. **Superlativos por extenso também:** varrer `state of the art`, `state-of-the-art`,
   `best-in-class`, `unmatched`, `outperforms all`, `leading` — meu censo procurou só a
   sigla, e alegação escrita por extenso passaria batida.
4. **Teste de mutação que exige a MENSAGEM:** reintroduzir `both SOTA` na linha 579 tem
   de fazer o guarda falhar **citando a linha 579**, não só sair não-zero.
