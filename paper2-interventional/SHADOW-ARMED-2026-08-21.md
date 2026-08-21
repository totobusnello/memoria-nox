# Shadow armado: mecanismo vivo, medindo zero pela razão certa

**Data:** 2026-08-21 · **PR:** `nox-workspace#47` (gate de maturidade), merged
**Precede:** `LAMBDA-RESULTS-2026-08-21.md`

## O que está no ar

| | |
|---|---|
| `p2_verdict` | **280** linhas — 225 S0 (sem chunk), 33 S1, 22 S2 |
| Invariante chunk ⟺ veredito | **55 / 55**, todos os chunks existem |
| `pain` dos chunks | exatamente `SEVERITY_PAIN` (S1 0,25 · S2 0,50), `importance` 0,90 |
| `NOX_P2_OUTCOME` | **shadow** |
| `NOX_P2_SHADOW_W` | **2.0** — o braço mais baixo da banda |
| `NOX_P2_SERVING_LOG` | `/root/.openclaw/logs/p2-serving.ndjson`, recebendo linhas |
| `abort-check` | `exit 4` — 7 dias de histórico contra o gate de 14, **recusa avaliar** |

O drop-in tem `[Service]` (a falha de 19/08 foi exatamente sua ausência) e a env foi
conferida **no processo**, não no arquivo.

## `churn = 0`, e por que isso NÃO é resultado sobre a dose

Medido nos 6 agentes: zero deslocamento. A causa não é o boost ser fraco:

```
snapshot servido : /var/lib/nox-mem/epochs/current.db
takenAt          : 2026-08-21T09:00:51Z
chunks do estudo NO snapshot : 0
tabela p2_verdict NO snapshot: 0
```

Os 55 chunks foram escritos ~13 h **depois** do snapshot. `NOX_EPOCH_SNAPSHOT=active`
faz o corpus servido ser o snapshot da fronteira — que é o estimando registrado —
então conteúdo escrito no meio do epoch não pode agir. O `churn = 0` mede a
ausência da população, não a força da dose.

⚠️ Registro isto porque a leitura tentadora — "ativação zero a `w = 2.0`" — seria
falsa, e é exatamente a classe de erro que me pegou três vezes hoje: concluir sobre
um mecanismo a partir de um número cujo referente não conferi.

## O defeito que só apareceu com chunks reais

A implementação de #45 impulsionava **qualquer** chunk de `p2_verdict` no pool, sem
gate de idade. Contradiz o registro:

- §3:642 — `Opportunity` exige o episódio *"written ≥ 1 epoch length before the
  epoch start"*
- §2:550 — *"the chunk cannot act in the epoch it is written"*

**O dano não estava onde parecia.** Um chunk impulsionado no epoch em que nasceu não
cria `Opportunity` pelo §3, logo não entra no desfecho — mas **muda o brief**, e
pode deslocar do slot de cobertura um chunk mais velho que *sim* geraria
oportunidade. Contamina o contraste sem aparecer na medição.

Consertado em #47: corte `written_at <= inicio_do_epoch − 24 h`, na própria query.
Âncora é o **instante da escrita**, não o da falha (lock de 2026-08-16, §2:202).

## Previsão verificável

Chunks escritos em **2026-08-21T~22:45Z**. Pelo gate:

| epoch | corte (`início − 24 h`) | entram? |
|---|---|---|
| início 2026-08-22T09:00Z | 2026-08-21T09:00Z | **não** — escritos 13 h depois do corte |
| início **2026-08-23T09:00Z** | 2026-08-22T09:00Z | **sim** |

**A primeira ativação possível é o epoch iniciado em 2026-08-23T09:00Z.** Se o log
de decisão mostrar `churn > 0` antes disso, o gate está furado. Se mostrar
`churn = 0` depois disso com os 55 chunks no snapshot, aí sim é resultado sobre a
dose a `w = 2,0`.

## O que medir quando chegar lá

1. `churn` por agente no log de decisão — a **fração de ativação**, que é o número
   que faltava para decidir banda e `N`.
2. Quem ocupa os 2 slots de cobertura: chunk do estudo ou incumbente de
   `lessons.md`. Com 55 nunca-servidos e elegíveis, o estoque incumbente que
   drenou em 20/08 foi reposto pelo próprio estudo.
3. Se a designação morde: 55 chunks em quantos grupos de assinatura distintos.
   Um por grupo é impulsionado; o resto compete sem boost.
