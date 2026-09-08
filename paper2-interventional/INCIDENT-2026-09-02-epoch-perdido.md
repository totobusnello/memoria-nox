# Epoch 2026-09-02 nunca foi servido; 2026-09-03 é parcial

> Descoberto 2026-09-08 ao medir o estado vivo do ensaio para redigir a errata da
> descrição do Paper A. **Não é o defeito que eu procurava** — apareceu no caminho.
> Causa **não** estabelecida. O que está abaixo é medido; a explicação não é.

## O que está medido

Log de serving: `/root/.openclaw/logs/p2-serving.ndjson` (7,2 MB, vivo).

| epoch | briefs | w servido |
|---|---:|---|
| 2026-09-01 | 672 | 2 **e** 4 — dia da virada shadow→active (10:25:39Z) |
| **2026-09-02** | **0** | **— nunca abriu** |
| 2026-09-03 | 441 | 0 (controle) — parcial, começa 17:23:39Z |
| 2026-09-04 | 672 | 2 |
| 2026-09-05 | 672 | 2 |
| 2026-09-06 | 672 | 7,5 |
| 2026-09-07 | 462 | 0 (controle) — ainda acumulando em 09-08 01:22Z |

**Lacuna:** último registro `2026-09-02T08:52:06.139Z` (ainda sob epoch `2026-09-01`,
coerente com a fronteira de 09:00 UTC), primeiro seguinte
`2026-09-03T17:23:39.777Z`. **32,5 horas.**

Dias completos servem **672** briefs. O epoch 09-03 tem 441 ⇒ ~66%.

## Três negativos que descartam as explicações fáceis

1. **Não foi queda do serviço.** `provider_telemetry` mostra tráfego **contínuo e plano,
   2 chamadas/hora, sem um único buraco** ao longo das 32,5 h. O processo estava vivo o
   tempo todo.
2. **Não foi desenho.** Dias de controle **logam** — 09-03 (441) e 09-07 (462) são ambos
   `w=0` e estão no log. Ausência de dose não produz ausência de linha.
3. **Não foi modo degradado.** `degradados=0` em todos os 17 epochs do log. Se tivesse
   caído para degradado, teria servido controle **e registrado**.

## O fato que aponta para onde olhar, sem provar nada

O systemd registra **um único** `Stopping/Stopped/Started` na janela inteira:
`2026-09-03T17:23:30Z`. Nenhuma parada no **início** da lacuna, só no **fim**. E a
primeira linha de log volta **9 segundos** depois desse restart.

⇒ O serviço entrou num estado em que continuava atendendo tráfego mas não produzia brief
com registro p2, e **saiu desse estado por restart**. Isso é consistente com handler
travado ou com resolução de snapshot de epoch presa, e é **inconsistente** com o produtor
de brief externo ter parado — se fosse externo, reiniciar a API não o traria de volta.

⚠️ Consistente ≠ estabelecido. Nenhuma das duas hipóteses foi testada.

## Por que importa para o registro

O ensaio tem 234 epochs randomizados prospectivamente (`ASSIGNMENT.json`, drand
31774052). **Um deles não tem dado nenhum e outro tem ~66%.** Numa unidade de
randomização, isso é dado faltante em unidade sorteada — não é ruído dentro da unidade.

Precisa entrar em `DEVIATIONS-FOR-PAPER.md` **antes** da análise, com a regra de
tratamento declarada antes de olhar o resultado: epoch 09-02 é perda total, 09-03 é
parcial. A pergunta que a regra tem de responder — e que **não** vou responder aqui,
porque decidir isso vendo os números é exatamente o que o pré-registro existe para
impedir — é se epoch parcial entra, entra com peso, ou sai.

## Guarda que faltava, e a classe

Não existe alarme para "o log de serving parou". A lacuna durou 32,5 h e só apareceu
porque fui medir outra coisa, seis dias depois.

Classe conhecida, terceira vez: **guarda cujo predicado exige o dado que falta não cobre
a falta do dado.** Um monitor que lê o último epoch e confere a dose não dispara quando
não há epoch nenhum. O guarda precisa de perna própria: *nenhuma linha nova em N horas*,
medida contra o relógio, não contra a última linha.

Related: `docs/INCIDENTS.md` · `DEVIATIONS-FOR-PAPER.md`
