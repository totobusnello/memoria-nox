# Preprint com DOI para o Paper 1 — runbook (TechRxiv BLOQUEADO)

> 🔴 **BLOQUEADO em 2026-09-07: o TechRxiv NÃO está aceitando submissões.** Aviso na
> própria home: *"We are currently preparing a transition to a new platform.
> **Submissions are temporarily closed during this process.** All previously published
> content will remain accessible and DOIs will continue to resolve."* Sem prazo
> anunciado. E o sinal que muda a leitura: o preprint mais recente listado é de
> **6 de março de 2026** — **seis meses** sem nada publicado, o que não descreve uma
> janela curta de manutenção.
>
> ⚠️ **Erro de método que produziu este documento, e vale mais que o documento.** Eu
> verifiquei as **regras** do TechRxiv — formato de arquivo, DOI, licença, membership,
> se aceita manuscrito recusado no arXiv — e **não verifiquei se a porta estava
> aberta**. Requisito conferido não é disponibilidade conferida. O §1 abaixo continua
> correto e continua inútil enquanto a submissão estiver fechada.
>
> **Alternativas verificadas no mesmo dia, no navegador:**
>
> | via | estado | DOI | conta |
> |---|---|---|---|
> | OSF Preprints | ✅ aberto (botão "Add A Preprint" ativo; *Engineering* entre os assuntos) | sim | já existe — o pré-registro do Paper 2 vive no OSF `yf7d2` |
> | Zenodo | ✅ aberto, sem moderação | imediato | já usado duas vezes (Paper A e o pré-registro) |
>
> Nenhuma das duas satisfaz a condição do arXiv (endosso de *journal*), então a escolha
> entre elas não afeta aquele caminho — afeta só onde o DOI nasce.
>
> **Estado: PACOTE PRONTO, NADA SUBMETIDO.** O PDF, os metadados e as verificações dos
> §2–§3 **não dependem do veículo** e servem para qualquer um dos três. A submissão é do
> Toto.

## Por que TechRxiv

O arXiv **não aceitou** este manuscrito em 2026-09-03 (`submit/7771319`), com o motivo
literal *"would benefit from additional review and revision that is outside of the
services we provide"* — o arXiv não avalia correção científica, então a frase significa
"precisa de peer review, e nós não fazemos peer review". A apelação é **ativo de uso
único** e, negada, é permanente; e a exigência de endosso de *journal* é discricionária e
foi invocada para este manuscrito. **Nenhum DOI de repositório satisfaz aquela
condição** — depositar em Zenodo não reabre o arXiv.

Consequência: o Paper 1 **não tem DOI nenhum**, e é isso que o TechRxiv resolve.

## 1. Requisitos, verificados em 2026-09-07

Fonte: páginas oficiais IEEE/TechRxiv (`innovate.ieee.org/techrxiv/`,
`ieee.org/publications/techrxiv.html`).

| item | verificado | valor |
|---|---|---|
| formato de arquivo | ✅ | PDF, Word e LaTeX aceitos. **PDF é o caminho mais seguro** |
| DOI | ✅ | atribuído ao publicar — o objetivo desta submissão |
| screening | ✅ | existe, **sem peer review**: checa escopo, se é pré-revisão, e problemas de integridade/legalidade |
| manuscrito recusado noutro lugar | ✅ | permitido — *"authors may post preprints regardless of where they intend to submit or publish"*. A não-aceitação no arXiv **não desqualifica** |
| licença | ✅ | Creative Commons disponível, incluindo **CC BY** |
| membership IEEE | ✅ | **não** exigida |
| escopo de ciência da computação | ✅ | coberto |
| **limite de tamanho do abstract** | ❌ **não estabelecido** no oficial | os 150–250 palavras que circulam são de *journals* IEEE, não do repositório. Não preencher por suposição |
| **rótulo exato da subcategoria** | ❌ **não exposto** no oficial | confirmar na lista do formulário ao vivo |

⚠️ **Restrição que importa:** TechRxiv é para pesquisa **inédita e pré-revisão** e **não**
aceita versão final de artigo já publicado. O Paper 1 é inédito ⇒ elegível.

## 2. O artefato, e como reconstruí-lo

    paper/build/paper-tecnico-nox-mem.pdf     77 páginas, 345 KB
    ./scripts/build-paper.sh                  pandoc 3.9 + xelatex, a partir do .md

O PDF anterior era de **12 de julho** — anterior à *honesty pass* de 03–04/09 e ao
abstract reescrito em 07/09. Foi **reconstruído** em 2026-09-07.

### Verificações feitas no PDF reconstruído

| checagem | esperado | obtido |
|---|---|---|
| abstract novo presente (`Three findings cut against our own headline`) | ≥1 | ✅ 1 |
| `above every MemOS Table 4 number` (com backbone nomeado) | ≥1 | ✅ presente |
| `above every published MemOS number` (quantificador universal) | **0** | ✅ 0 |
| claim dual-SOTA retratado (`state-of-the-art on both`) | **0** | ✅ 0 |
| Beam Retrieval declarado como **test set** | sim | ✅ `Beam Retrieval (69.2, test set` |

⚠️ Duas notas honestas sobre essas checagens:

1. `above every MemOS Table 4 number` aparece **duas** vezes no `.md` (abstract e §5.1.10)
   e o `grep` no texto extraído acha **uma** — a outra ocorrência foi quebrada em duas
   linhas pelo `pdftotext`. É artefato de extração, não do PDF;
2. o build emite `Missing character: There is no ⚠ (U+26A0) in font [lmroman10-regular]`.
   Os glifos `⚠️` são **descartados** do PDF. O texto da ressalva permanece, então o
   sentido se preserva — mas o marcador visual não chega ao leitor. Não bloqueia; fica
   registrado para ninguém "descobrir" isso depois como defeito novo.

## 3. Metadados

Em `techrxiv-metadata.md`, pronto para colar.

🔴 **O bloco de metadados NÃO é o que foi ao arXiv, e isto é correção, não estilo.** O
`paper/arxiv-metadata.txt` (local, gitignored porque carrega código de endosso) afirma
*"architecture is the leading explanation"*, e o corpo do paper diz o oposto em §6.3.2 —
*"this is embedding-matching, **not** a clean architecture isolation"*. Aquele bloco
também dizia *"not **yet** significant"* e omitia o número da comparação em que nox-mem
**perde** (LoCoMo nativo, 0.469 vs 0.426). As três correções estão no bloco novo. É a
mesma classe da retratação de 03/09: campo de metadados é lido **isolado**, sem as seções
que o qualificam, então o limitador tem de viajar dentro dele.

## 4. Passos

1. criar conta em `techrxiv.org` (sem membership IEEE);
2. upload de `paper/build/paper-tecnico-nox-mem.pdf`;
3. colar título, autor e abstract de `techrxiv-metadata.md`;
4. **confirmar na lista ao vivo** a subcategoria (information retrieval / machine
   learning) — o rótulo não está no oficial;
5. licença **CC BY 4.0**;
6. keywords do §"Keywords sugeridas";
7. declarar inédito e não sob revisão;
8. submeter.

## 5. Depois do ID sair

- atualizar `CITATION.cff` com o DOI;
- badge no `README`;
- ⚠️ o PR no `AgentMemoryWorld/Awesome-Agent-Memory` ficou travado por falta de
  identificador estável — com o DOI do TechRxiv ele **destrava**;
- ⚠️ **não** reabrir o arXiv com base neste DOI: a condição de lá é endosso de *journal*,
  e DOI de repositório não a satisfaz. Isso está medido, não suposto.

## 6. O que este runbook NÃO resolve

O motivo declarado da recusa no arXiv foi *"needs additional review"*. Um preprint no
TechRxiv dá **DOI e citabilidade**, não *peer review*. O caminho que atende à condição do
arXiv continua sendo submissão a *journal* — e o candidato com trilha real é extrair o §6
(a comparação pré-registrada entre sistemas) como paper próprio de 8–10k palavras para
TMLR. Isso é trabalho separado e não está feito.
