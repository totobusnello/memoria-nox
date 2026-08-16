# Próximos passos — Paper 2

> **Reescrito 2026-08-15.** A versão anterior abria com *"Nada de execução do Paper 2 começa antes de o Paper 1 sair do hold"* — e a execução tinha começado: o piloto rodou, 7.184 pares foram adjudicados, quatro locks fecharam. O documento afirmava o oposto do estado real, que é a pior coisa que um documento de estado pode fazer. Histórico dos gates originais: `git log -- NEXT-STEPS.md`.

## Onde estamos

O **pré-registro está pronto para o OSF** (v1.7). Nenhum `[TO LOCK]` espera análise. Em 15/08 medir a dose expôs e fechou um termo indefinido no braço de tratamento (`linked`) — ver `LINK-FEASIBILITY-2026-08-15.md`. O estudo **não começou** — nenhum epoch randomizado existe, e tudo que foi medido é pré-tratamento, sobre corpus histórico sem atribuição de braço.

O gate do arXiv ID do Paper 1 **não bloqueia mais o Paper 2**. Ele bloqueava a *publicação*; o pré-registro e o piloto seguiram sem ele, e o moderador respondeu em 13/08 que o atraso é volume — sem ação nossa. Não recontatar.

## O próximo passo, e por que é este

**Registrar no OSF.** É o que transforma o documento de arquivo-no-nosso-repo em ativo público datado. Sem timestamp externo anterior à coleta, a palavra "pré-registrado" no paper inteiro se apoia só no nosso `git log` — que é bom, mas é nosso.

Registrar dispara, em ordem: `T_seed_assign` fica declarável (deve ser posterior ao timestamp OSF e anterior ao primeiro epoch de tratamento) → primeiro epoch randomizado → data-limite de calendário. Os dois `[TO LOCK]` restantes caem por consequência.

## Depois disso

| | O quê | Nota |
|---|---|---|
| 1 | Fixar o operacional da escrita: qual componente escreve o chunk e com que template | Não muda número travado; tem de existir antes do 1º epoch |
| 2 | Executar o estudo — **174 epochs** | ~5,7 meses. Sem análise interina, sem parada opcional |
| 3 | ~~Ler InterruptBench~~ | ✅ 15/08 — `RELATED-WORK.md` §4.2 |
| 4 | ~~Resolver "hypotree"~~ | ✅ 15/08 — era um **MCP server**, não um paper. §4.3 |

## Aberto, e não é trabalho nosso

- **Para quem escrever no Stanford** (`docs/STANFORD-OUTREACH.md`): correspondência do 2606.06448 é da Omri; o cluster que liga ao MemoryArena é He/Pentland. Decisão do Toto.
- **arXiv ID do Paper 1**: sem ação possível.

## Previsões registradas — cobrar depois

Ambas ficaram no registro **antes** do primeiro epoch, e existem para serem verificadas contra o que acontecer, não para serem lembradas seletivamente:

1. **`N = 174` provavelmente é conservador.** Os parâmetros do regime maduro do corpus dariam N=46 a MDE 25% (106 no limite superior do ICC) — e o lock é mais folgado ainda, por dimensionar a 30% no limite superior. Se estiver certo, o estudo chega ao horizonte com mais poder que o planejado. Ver `PREREG-DRAFT.md`, Apêndice B, nota de não-estacionariedade.
2. **O painel não pode provar que julgou com glm-5.2** nos 3.348 vereditos anteriores a 14/08. `model_served` passou a ser gravado, mas não é retroativo. Se a composição do painel virar questão de revisão, esta é a resposta honesta.
