# O regime da fila: o efeito da dose depende de uma coincidência de fila

**Data:** 2026-08-21 · **Depende de:** `BAR-RETRACTION-2026-08-20.md`,
`AMENDMENT-v1.12-DRAFT.md` (§1 retratado)

## 1. Re-ingest **recria** os chunks — e zera o histórico de serve

`ingest-entity.ts:196` executa `DELETE FROM chunks WHERE source_file = ?` antes de
inserir. Consequência medida em `memory/lessons.md`:

```
ids: 308114 … 308165   span = 52   n = 52     <- perfeitamente contíguos
created_at: 2026-08-20 02:02:03  (1 única janela de minuto para os 52)
```

Ids contíguos + `created_at` idêntico = **DELETE + INSERT em lote**. Cada
re-ingest do arquivo dá **ids novos**, portanto **nenhuma linha em `brief_log`**,
portanto os 52 voltam a ser **nunca-servidos**.

Corolário: `access_count` e o histórico de serve são destruídos no re-ingest. A
barra que medi (0,684477) é o valor **pós-re-ingest**, com `access = 0`. Antes do
re-ingest esses chunks tinham `access > 0` e salience mais alta.

⚠️ **Isto é um gerador de confundimento.** O estoque incumbente não é um fluxo
suave — é uma **função degrau** disparada por um evento operacional (re-ingest de
arquivo). Se esse evento correlacionar com qualquer coisa (por exemplo, sessões em
que lições são escritas sendo sessões com falhas), a barra fica correlacionada com
a própria população de tratamento. Precisa ser pré-registrado como ameaça.

## 2. A capacidade de dreno é ~600 picks/dia contra um estoque de 0

Volume de briefs medido:

| dia | briefs | slots servidos |
|---|---|---|
| 17/08 | 349 | 6.776 |
| 18/08 | 357 | 6.744 |
| 19/08 | 302 | 6.930 |
| 20/08 | 296 | 6.950 |

~300 briefs/dia × 2 slots de cobertura = **~600 picks/dia**. Contra um estoque de
52. Daí o dreno completo em um dia — não foi anomalia, foi a razão
capacidade/estoque.

## 3. O estoque está em 0 e não está reabastecendo

Observado, e declaro o limite do que verifiquei:

- estoque nunca-servido elegível: **0**
- `memory/lessons.md`: `mtime` **2026-08-20 22:04:12**, mas seus chunks ainda
  datam de **02:02:03** e mantêm os ids contíguos originais
- o DB está ativo (47 chunks criados com id > 308165; `max(id) = 308212`)
- o watcher (`nox-mem-watch`) está `active`, vigia `WORKSPACE/memory`, aceita
  `.md`, e **nenhum `SKIP_PATTERNS` casa** com `memory/lessons.md`

Ou seja: um arquivo vigiado mudou e não foi re-ingerido. **Não diagnostiquei a
causa** (pode ser `fs.watch` não-recursivo, debounce, falha silenciosa de ingest
ou reinício do watcher) e não vou afirmar qual — registro só o observável.

## 4. A consequência para o estudo

Juntando: no regime esperado, um chunk do estudo é escrito, é **nunca-servido**,
não há incumbentes nunca-servidos para disputar, e ~600 picks/dia o servem quase
imediatamente. Ele entra nos slots de cobertura **sem oposição, a `w = 0`**.

Então o único canal vivo é o que as duas vozes adversariais identificaram —
**designado vs não-designado entre chunks do próprio estudo** — e ele exige **≥ 3
chunks do estudo simultaneamente nunca-servidos** na mesma janela de brief. Com
~600 picks/dia, essa janela é curta.

**O efeito da dose não é nulo (isso foi retratado), mas é fino, e sua magnitude
depende de uma coincidência de fila.** Quantificá-la exige a taxa de chegada de
falhas adjudicadas — λ.

⚠️ Isso torna a rodada do painel **mais** necessária, não menos: λ deixou de ser
um parâmetro de dimensionamento e passou a ser o que determina se existe contraste.

## 5. O que isto NÃO estabelece

- Não estabelece que o efeito seja pequeno demais para detectar — não há λ ainda.
- Não estabelece a frequência dos degraus de re-ingest. Antes de 20/08 o mecanismo
  global estava inerte (prefixo órfão), então re-ingests anteriores não deixaram
  rastro em `brief_log` — os 100 ids órfãos totais não medem a frequência futura.
- Não diagnostica o watcher (§3).
