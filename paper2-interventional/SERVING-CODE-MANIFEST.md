# Serving code — deposited blobs and their provenance

> Added in **v1.12** to close the defect `AMENDMENT-v1.12.md` §7 declares: until then
> the code carrying the mechanism lived only on a private host and was unauditable by
> whoever read the registration.
>
> **Updated 2026-08-27** for the band-collapse amendment, which describes a *different*
> designation rule than v1.12 did. Two modules changed and one file was added.

Keys are flat because the deposit is flat. The original path is authoritative for
reading each amendment's line citations.

## Current — the rule this amendment describes

Commit **`1da78560`**, `2026-08-26T20:25:01+00:00`, repo `nox-workspace` (private),
message *"feat(nox-mem/paper2): regra de designacao substituta — sorteio com seed
declarada"*.

| deposited as | original path | bytes | sha256 |
|---|---|---|---|
| `serving-brief.ts` | `src/api/brief.ts` | 44748 | `27dbe9962a2903aaa3a5ead432a4f40e31e8f8f0ac5e42796dd4ec914f0e2e95` |
| `serving-brief-outcome.ts` | `src/paper2/brief-outcome.ts` | 21213 | `b3a3b1a8c72fe79144f401003b89a10455eeea9115275a80449679c2c07f48aa` |
| `serving-p2-outcome-test.ts` | `src/__tests__/p2-outcome.test.ts` | 22673 | `62ba78d141aafe4c2ac86795c96b39704518f175e7f9ed3c0c199d0164a4fe6e` |

Unchanged since v1.12, and re-verified at the same commit:

| deposited as | original path | commit | committed | bytes | sha256 |
|---|---|---|---|---|---|
| `serving-brief-diversity.ts` | `src/api/brief-diversity.ts` | `ad2ca37e` | 2026-06-26T15:28:23−03:00 | 8712 | `34c9aee5f80311c8aff5c0ae35f37dd6dbf52f31a9f940b01cdb8d205c69e7a2` |
| `serving-salience.ts` | `src/salience.ts` | `aca868c7` | 2026-08-02T12:37:55−03:00 | 12553 | `083399fc190920ff8f2a590bd74876e25b1f95552515977920edb64025924684` |
| `serving-search.ts` | `src/search.ts` | `aee41849` | 2026-06-07T21:42:53−03:00 | 29622 | `d76034e2b7796744ae5836af02c5a1155ddc5750f0fa2d94875f63b9b1b723d3` |

⚠️ **A coluna `sha256` desta segunda tabela foi acrescentada em 2026-08-30 e não
existia na v1.12 depositada** — ver a nota ao fim desta seção. Os três valores foram
computados sobre os blobs da tag `paper2-v1.12`, byte a byte idênticos aos arquivos em
disco, de modo que pinam exatamente o que foi depositado.

**`1da78560` is the last commit touching `tools/nox-mem/src/`**, and none of the three
files above changed between it and the fetch for this deposit
(`git log 1da78560..HEAD -- <file>` → 0 commits, each). The two source files on disk
on the serving host hash identically to the commit, so what is deposited is what is
serving — not merely what was committed.

⚠️ **`serving-p2-outcome-test.ts` is new to this deposit, and it is not decoration.**
The amendment's §1 claims *"cinco mutações do fonte TS foram confirmadas fazendo os
testes falharem"*. Without the test file that claim is unfalsifiable by a reader. The
file carries the frozen cross-language byte vector for the designation key, the
negative separator test, the S0/NULL exclusion test and the global-invariance test.

## The commit hash the amendment cited first, and why it is wrong

Earlier redactions of the band-collapse amendment pinned the serving code to
**`0087c918`**. **That object does not exist** in `nox-workspace`: not as a commit, not
in any ref, not in the reflog (`git cat-file -t` → *"Not a valid object name"*).

The content is the right content — `1da78560` carries the same committer timestamp
(`2026-08-26T20:25:01+00:00`) and the same message, and the files contain exactly the
functions the amendment describes (`chaveDeDesignacao`, `designadosGlobais`,
`carregarDesignados`; `cDesignacao` appears only inside the comment recording its
removal). What changed was the **name**: `5174e0fa`, *"merge: reconcilia VPS (17
commits, 23-26/ago) com origin"*, at 21:02:13Z that same evening, rewrote the hashes
of the VPS-side commits.

⚠️ **A commit hash is not a stable identifier across a history reconciliation.** A
document that pins code by commit alone acquires a dangling citation the moment
someone rebases, and the failure is silent: the prose still reads as precise. That is
why every row above carries the **sha256 of the file bytes** — that pin survives any
history rewrite, and it is the one a reader can check against the deposited blob
without access to the private repository.

🔴 **Esta frase era falsa na v1.12, e o modo como era falsa é o próprio assunto do
parágrafo.** Três das seis linhas — as da segunda tabela — traziam **só** o hash de
commit, isto é, exatamente o pino que o parágrafo acima acaba de declarar instável. Um
leitor que aceitasse a promessa e tentasse conferir `serving-brief-diversity.ts` contra
o blob depositado não teria contra o que conferir, e precisaria do repositório privado
— que é justamente o acesso que a frase promete dispensar.

A lacuna não era decorativa: `serving-brief-diversity.ts` carrega o
`DIVERSITY_DEFAULTS`, de onde sai o piso 0,7/0,7 que sustenta uma das duas manchetes
do paper. O pino mais fraco cobria o arquivo mais citado.

Os três `sha256` foram computados em 2026-08-30 e acrescentados acima. **A v1.12
depositada permanece como está** — o registro não se reescreve; o desvio está declarado
em `DEVIATIONS-FOR-PAPER.md` e entra no paper, conforme a decisão de 27/08 de não
emendar. Quem for conferir a v1.12 usa os valores desta tabela, que pinam os mesmos
bytes.

⚠️ A lição operacional, para os depósitos seguintes: **uma afirmação de completude
("toda linha acima…") tem de ser verificada contra a tabela, não contra a intenção.**
Escrevi a frase pensando na primeira tabela e ela ficou quantificando as duas. Nenhuma
das seis revisões adversariais pegou, porque todas leram o parágrafo como argumento — e
o argumento está certo. O que estava errado era o alcance do quantificador.

## What this is not

These are the modules, not the whole system. They import from the rest of the package
(`db.js`, the embedding client, the FTS5 layer), which is **not** deposited, so the
blobs are **auditable but not executable standalone**. That is a narrower claim than
reproducibility and it is the honest one. What it buys: whoever reads the citation
`brief.ts:1086` can open line 1086 instead of trusting the transcription.
