# As 20 referências que faltam, escolhidas por mineração — não por conveniência

> Medido 2026-09-10, depois de o `regua-simetrica-2026-09-10.md` (#511) estabelecer que
> **corte de prosa não fecha o déficit de densidade — só referência fecha**, e que o alvo é
> 30 → ~50 referências.
>
> O critério não é "achar 20 papers". É: **as obras que os aceitos citam e nós não.** Essas
> são as que um revisor desta área espera ver, e a escolha é verificável.

---

## 1. Método, e a falha de classificador que ele passou primeiro

Baixadas as bibliografias dos quatro aceitos direto do HTML canônico do arXiv — os mesmos
artefatos do §2 do diagnóstico (`ltx_bibitem` = 21, 16, 11, 51). **99 citações.**

⚠️ **A primeira tentativa devolveu "0 obras citadas por ≥2 aceitos", e era falsa.** A chave
de normalização (`sorted(set(palavras))[:14]`) muda quando a formatação do venue muda, então
a mesma obra citada por dois papers gerava chaves diferentes. Controle positivo que derrubou
o resultado:

| obra | em quantas das 4 bibliografias |
|---|---|
| **MemGPT** (Packer et al.) | **4** |
| **LongMemEval** (Wu et al.) | **4** |
| Mem0, Zep, Generative Agents | **3** |
| A-Mem, HaluMem, Lost-in-the-Middle, Reflexion | **2** |

Quatro papers do mesmo subcampo com zero sobreposição é implausível de cara. Método
substituído por *union-find* sobre pares com ≥5 palavras raras em comum (stopwords de venue
removidas), que reproduz o controle: **99 citações → 77 obras distintas**, 26 pares
cross-paper.

## 2. O que reconcilia o `7` do diagnóstico com o `30` do Fable

As nossas **43** definições de footnote não são 43 referências:

| forma | n | é referência? |
|---|---:|---|
| citação de paper (autores/ano ou arXiv ID) | **24** (piso) | sim |
| ponteiro de projeto — URL de repo, **sem localizador** | 7 | conta como referência para nós, **não** para um revisor |
| nota sobre o nosso próprio código, ou sobre o stack de um competidor | 12 | **não** |

⇒ A bibliografia visível a um revisor é **~24**, não 43. O `7` do diagnóstico era de antes de
#491/#492/#494; o `30` do Fable conta definições externas, incluindo ponteiros de repo e notas
de stack. Nenhum dos dois estava errado — mediam coisas diferentes, e nenhum media *"o que um
revisor conta"*.

*(O 24 é piso: o classificador tem falso-negativo — `[^locomo]`, `[^sqlitevec]`, `[^memo]` e
`[^geminiembed]` têm forma de paper e caíram fora porque o padrão de autores exigia iniciais
com ponto. Corrigir o classificador antes de publicar qualquer número absoluto daqui.)*

## 3. Os três defeitos consertados já neste PR

Comparávamos contra o **mem0 no §6 inteiro sem citar o paper do mem0.** Três footnotes
apontavam para o repositório de sistemas que **têm** paper — e cujos papers são citados por
**3 dos 4 aceitos**:

| footnote | antes | agora |
|---|---|---|
| `[^mem0]` | `github.com/mem0ai/mem0` | Chhikara, Khant, Aryan, Singh & Yadav, **arXiv:2504.19413** (2025) + o repo |
| `[^zep]` | `github.com/getzep/zep` | Rasmussen, Paliychuk, Beauvais, Ryan & Chalef, **arXiv:2501.13956** (2025) + o repo |
| `[^everos]` | `github.com/EverMind-AI` | Hu, Gao, Zhou, Xu *et al.*, **arXiv:2601.02163** (2026) + o repo |

É a mesma classe que o diagnóstico já havia apontado para `[^hipporag2]` (*"dar localizador ou
tirá-lo"*). Um baseline de comparação sem citação é defeito de rigor, não de forma.

## 4. As candidatas, ranqueadas por evidência

**Grupo A — citadas por ≥2 aceitos e ausentes do nosso manuscrito (4).** Prioridade máxima:
são o cânone imediato da área.

| obra | aceitos que citam | localizador |
|---|---|---|
| Liu, Lin, Hewitt, Paranjape, Bevilacqua, Petroni & Liang, *Lost in the Middle* | 2 | — |
| *HaluMem: Evaluating Hallucinations in Memory Systems of Agents* | 2 | arXiv:2511.03506 |
| Shinn, Cassano, Gopinath, Narasimhan & Yao, *Reflexion* | 2 | NeurIPS 2023 |
| Xu et al., *A-Mem: Agentic Memory for LLM Agents* | 2 | arXiv:2502.12110 |

**Grupo B — obras que nós já discutimos no corpo e não citamos (15).** As mais baratas: a
discussão existe, falta só a referência. Lista completa em `out/cands.json`.

**Grupo C — ausentes e citadas por 1 aceito (23).** Só entram as que Related Work
efetivamente discuta — o diagnóstico pede a vizinhança *"citada **e discutida**"*, e
referência sem discussão é enchimento.

## 5. Contagem

24 visíveis + 3 promovidas neste PR = **27**. Grupo A (4) + Grupo B (15) levaria a **46**, com
`arXiv IDs citados` de 25 para ~40. Alvo de densidade: **~50** referências no tamanho atual
dão 2,07/mil, no piso da faixa dos aceitos (2,06–2,95).

⚠️ **Nenhuma referência entra sem discussão no texto.** Densidade comprada com citação
decorativa é o mesmo defeito de forma que este trabalho existe para consertar, com o sinal
trocado — e é detectável por qualquer revisor que procure a menção no corpo.
