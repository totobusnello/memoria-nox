# `measurement/` — os scripts que produziram os números da emenda

Existe para fechar o §9 da `AMENDMENT-DRAFT-band-collapse-2026-08-26.md`, que
declarava a lacuna: *"um terceiro NÃO consegue reproduzir as medições desta emenda
hoje"*, porque os scripts viviam só no repo `nox-workspace`, que é **privado**.

**Cinco dos dezenove não estavam versionados em lugar nenhum** — nasceram como
heredoc, foram copiados para `/var/tmp` na VPS e produziram números que entraram na
emenda. `autoextincao.py`, `descontamina.py`, `serie.py`, `rebase.py` e
`pos-regra.py` estão aqui porque a alternativa era depositar um documento cujas
tabelas ninguém pode recomputar.

## O que cada um faz

### 🟢 A harness canônica — use esta

| script | o que mede | número que sustenta |
|---|---|---|
| **`replay-oportunidade.mjs`** | replay do canal de boost **importando `buildBriefDiverse` do `dist`** — passa por `fetchRankedPool`, `fetchFreshCandidates`, `ordenarCobertura`, `interleaveFresh`, `pinned`, near-dup e as 5 fases do `pickDedup`. Três modos: `ancora`, `campo`, `dose` | fidelidade **350/350** contra a produção (controle, `churn`, `would_enter`); dose monótona 0→17 estados saturando em `w = 7,5`; teto **17/350 = 4,86%**. Ver `../REPLAY-OPORTUNIDADE-2026-08-27.md` |
| **`ciclo-do-lote.py`** | mede o ciclo de vida de um lote de ingestão no canal de cobertura, por dia: quantos do lote foram servidos e a idade **máxima** servida — é a máxima que localiza o corte, não a mínima. Guarda: nenhum dia pode servir algo com idade ≥ o corte declarado (mutação com `--corte 6.5` acusa 2 dias e sai `exit=1`) | lote 09–10/08: 8 dias de serviço, máxima **nunca alcança 7,00** (para em 6,95), encolhe 75→54 em 16/08 e **zera em 17/08 sem voltar** — apesar de 23 dias de elegibilidade global restantes. Ver `../BATCH-CYCLE-2026-08-28.json` |
| **`granularidade-do-teto.py`** | consolida o contrafactual de granularidade da chave de estrato: mesmo replay, mesmo corpus, mesma designação, mesmos 350 estados, variando só a resolução de `served_at`. Guardas testados por mutação: invariância de procedência entre os quatro braços, rótulo × procedência, e reprodução da âncora nativa | teto **4,86% → 36,29% → 80,29% → 99,43%** de segundo a dia. Conjuntos **não** aninhados (3 estados saem), por dois mecanismos opostos — redundância e inalcançabilidade. Ver `../CEILING-GRANULARITY-2026-08-28.json` |
| `replay-resumo.py` | emite as tabelas daquela nota e as **trava** com `--assert-json` | 9/9 mutações detectadas |
| `irmaos-no-segundo.py` | exposição ao defeito de resolução de `served_at` | **46,9%** dos 350 briefs dividem o segundo com outro |

### 🟢 Os gatilhos do item 7 — em produção desde 27/08

| script | item | cadência | o que dispara |
|---|---|---|---|
| `gatilho-saturacao.sh` | 7(a) | diária 05:41Z | `churn(w_servido) == churn(w_absurdo)` ⇒ RED (dose não identificada); folga ≥ 0,9 ⇒ YELLOW |
| `gatilho-composicao.mjs` | 7(b) | horária :09 | **um** chunk elegível para `agentFresh` ⇒ RED (a escala de dose pressupõe vazio) |
| `teste-gatilho-active.sh` | — | sob demanda | 10 casos de mutação do caminho `--modo active` do (a) |

**`--modo active` do (a), implantado 28/08.** A dose deixa de vir de flag e passa a
vir do `ASSIGNMENT.json` (caminho + `sha256`, o mesmo par que o `resolverBraco` usa);
a janela deixa de ser o dia UTC e passa a ser o epoch `[E 09:00Z, E+1 09:00Z)`, **só
se já fechado**. E o gatilho **cruza o log com o ASSIGNMENT** — epoch, braço e dose —
porque `resolverBraco` devolve controle em toda falha, o que torna "controle no log"
ambíguo entre sorteio e `ASSIGNMENT` ilegível. A segunda hipótese enviesa para o nulo,
e sem o cruzamento é silenciosa.

Implantados em `/root/.openclaw/scripts/p2/`; status em `/var/lib/nox-mem/p2/`, lido pelo
`morning-report.sh`. **A fonte é aqui** — a cópia na VPS carrega um `PROCEDENCIA.md`
dizendo isso, porque repo e produção divergindo em silêncio é o defeito que o item 8
existe para evitar.

Nenhum dos dois sonda `/api/brief`: o endpoint **escreve** em `brief_log` o estado que
mede. Status **velho** conta YELLOW e linha ilegível conta RED — e o (a) reporta a
própria morte por sinal, porque gatilho parado é indistinguível de gatilho sem achado.

⚠️ **Todo script abaixo desta linha mede ORDENAÇÃO sobre pool reimplementado.** Serve
para inspecionar coordenadas, não para sustentar oportunidade, `N`, poder ou estimando —
e dois deles produziram números que o replay refutou. Três obrigações da harness canônica
que nenhum deles cumpre: corte de serve-state por **`brief_log.id`** (temporal não
reproduz), `T_REF` transladado no knob de idade (o serving lê `julianday('now')`), e
reprodução de âncora **nas duas** configurações de sonda.

### Os anteriores, por coordenada

### Estrutura do pool e os gaps

| script | o que mede | número que sustenta |
|---|---|---|
| `mede-delta.mjs` | pool de cobertura com `last_served` e `salience`, marcando quem é do estudo | pool 108 · 55/55 do estudo · 0 nunca-servidos · 44 grupos. ⚠️ usa `julianday('now')` e o **DB vivo** como corpus — produção serve do snapshot de epoch |
| `gap-defs.mjs` | o mesmo pool, mas **determinístico**: corpus = snapshot explícito, `T_REF` obrigatório (entra na elegibilidade, no serve-state **e** no `calculateSalience`), sondas excluíveis por `brief_id` — e as **três** definições de "par" lado a lado | reproduz as 6 âncoras publicadas; a definição certa é **adjacentes dentro do grupo de empate**: 38 pares · 11 zeros · 27 positivos · máx. 0,031808734967844865 (bate na 9ª decimal) |
| `ordem.mjs` | compara as **sequências** servidas, não os conjuntos | 28 casos, 0 com ordem diferente — refuta o canal de reordenação |

### Efeito da dose

| script | o que mede | número |
|---|---|---|
| ~~`dose2.mjs`~~ | 🔴 **REFUTADO 27/08 pela mesma razão.** "Caminho de produção" ali era o corpus certo com a **ordenação reimplementada** — não passava por `interleaveFresh` nem `pickDedup`. O real dá 11 / 15 / 17 estados em `w ∈ {2 · 4 · 7,5}`. Registro do erro. | — |
| ~~`controle-positivo.mjs`~~ | 🔴 **REFUTADO 27/08 — media o instrumento, não o sistema.** Reimplementava a ordenação do sub-pool global; o pipeline real dá `churn` **20** em `w = 100.000`, não 0. Este `0` virou a retratação central da emenda. Versionado como registro do erro, **não para uso.** | — |
| `dose-response.mjs` | ⚠️ **A PRIMEIRA VERSÃO, ERRADA.** Usou o DB vivo como corpus **e** como serve-state, exercitando caminho que produção não usa (`NOX_EPOCH_SNAPSHOT=active`). Versionado como registro do erro, **não para uso.** | — |

### A série de `churn`

| script | o que mede | número |
|---|---|---|
| `baseline.py` | linha de base bruta, janela fechada por `sha256` do NDJSON | 132/3.166 = 4,1693% — **superseded, diluída** |
| `rebase.py` | a mesma janela em três bases: tudo, pós-gate, pré-gate | pós-gate **132/2.212 = 5,9675%**; pré-gate **0/954** |
| `serie.py` | a taxa dia a dia, base pós-gate | 13,64% → 7,29% → 3,13% → 3,57% — **não estacionária**. Superseded por `tendencia.py` (que exclui sondas e traz Wilson) |
| ~~`pos-regra.py`~~ | ⚠️ **janela ABERTA por cima** (`ts >= REGRA`, sem teto) — o `11/310` envelheceu para 359 linhas em 12 h. Registro do erro. | — |
| `tendencia.py` | série diária com Wilson, sondas excluídas | 13,6364% → 7,2917% → 3,1250% → 3,4843%; 23+24/08 = 69% dos eventos em 44% do n |
| `remedia-serie.py` | janela **fechada e declarada**, `sha256` + bytes + linhas, soma das horas conferida contra o total | **11/350 = 3,1429%** (Wilson [1,76; 5,54]) sob a regra nova |

### Contaminação e auto-extinção

| script | o que mede | número |
|---|---|---|
| ~~`descontamina.py`~~ | ⚠️ **NÃO descontamina — ver `REMEDIATION-2026-08-27.md` §1.** A linha 9 corta por **tempo** (`served_at < 19:58`), removendo **3.735** linhas para excluir **25** de sonda: **149,4× o necessário**, ou 148,4× *a mais* que o necessário. Esta descrição, que dizia "excluindo as 15 linhas das minhas sondas", era falsa no mecanismo **e** no número. Fica versionado como registro do erro. | — |
| `remedia-descontamina.py` | exclusão exata por `brief_id` (5 sondas, 25 linhas), `T_REF` fixado | muda `posicao_primeiro_estudo` (3 → 0) e `grupos` (44 → 43); **nenhuma** estatística de gap muda |
| `asof-sonda-vs-tempo.py` | 2×2 que separa efeito de sonda de efeito de tempo | efeito das sondas em 27/08 09:00Z: **nenhum** (12 h de tráfego orgânico lavaram) |
| `autoextincao.py` | composição dos grupos de `last_served` reconstruída dia a dia | 61,8% → 65,5% em grupo puro-estudo. ⚠️ **Não testa auto-extinção sob tratamento** — toda a série é controle/shadow. E usa `julianday('now')`: população elegível muda a cada execução |

### Verificação do serving

| script | o que faz |
|---|---|
| `p2-designation-crosscheck.mjs` | lado TS do cruzamento: lê `p2_verdict` ao vivo e emite o `sha256` do conjunto, para comparar com `designation_verify.py`, que lê o CSV depositado |
| `verifica.py` / `verifica2.py` | confirmam por **estado observável** que o log novo traz `designated_ids` e `boost_by_id`, e que `boost_by_id ⊆ designados` |

## Como rodar

Os `.mjs` esperam estar em `tools/nox-mem/scripts/` de uma instalação do nox-mem,
com `dist/` compilado (`npx tsc`), e importam por caminho relativo `../dist/…`.
Fora dali eles são **auditáveis, não executáveis** — a lacuna está declarada, não
resolvida. Os `.py` só precisam de `python3` e leitura do SQLite.

⚠️ **O caminho do snapshot é parâmetro obrigatório, e isso não é preciosismo.**
`resolveCorpus` (`src/lib/epoch-serving.ts`) resolve o corpus pelo snapshot **mais
recente** de `epochsDir()`. Hoje isso é `e20260827T060001Z.db`, não o
`e20260826T060003Z.db` que o `DELTA-CUT-MEASUREMENT-2026-08-26.json` declara. Quem
rodar "o mesmo script" amanhã sem passar o caminho usa **outro corpus** e não recebe
aviso nenhum. Por isso `gap-defs.mjs` exige snapshot e `T_REF` como argumentos, sem
default:

```
node gap-defs.mjs /var/lib/nox-mem/epochs/e20260826T060003Z.db "2026-08-26 20:35:00" sem-sondas
```

**Antes de variar qualquer coisa, reproduza âncora publicada.** Foi assim que o
descasamento de definição apareceu (67 pares × 38): sem âncora, eu teria reportado
o número da definição errada como correção. `gap-defs.mjs` imprime as seis âncoras.

Os caminhos absolutos de servidor (`/root/.openclaw/…`) estão como estavam quando
rodaram — **de propósito**. Trocá-los por placeholders faria o script parecer
reproduzível sem ser: quem for reproduzir tem de apontar para o próprio banco, e
ver o caminho original diz qual arquivo era.

⚠️ **Nenhum destes escreve em `brief_log`.** `buildBriefDiverse` não faz tracking —
quem faz é `handleBrief` — logo a medição não contamina `last_served`. Essa
distinção é o motivo de as sondas via `/api/brief` (que **passam** por
`handleBrief`) terem contaminado, e os scripts, não. Ver §4.2 da emenda.

## O que estes scripts NÃO cobrem

Declarado porque a lacuna é a mesma que o §4.1 da emenda registra: nenhum deles faz
**replay do pipeline completo**. Não exercitam `interleaveFresh`, `pickDedup`,
`pinned`, near-dup, nem o corte do `LIMIT 400` com pool acima de 400. Logo medem a
**ordenação**, não a **seleção**, e a definição de oportunidade que sai deles é
aproximada por construção. O replay completo é item 1 do protocolo prospectivo.
