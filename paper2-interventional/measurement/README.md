# `measurement/` — os scripts que produziram os números da emenda

Existe para fechar o §9 da `AMENDMENT-DRAFT-band-collapse-2026-08-26.md`, que
declarava a lacuna: *"um terceiro NÃO consegue reproduzir as medições desta emenda
hoje"*, porque os scripts viviam só no repo `nox-workspace`, que é **privado**.

**Cinco dos catorze não estavam versionados em lugar nenhum** — nasceram como
heredoc, foram copiados para `/var/tmp` na VPS e produziram números que entraram na
emenda. `autoextincao.py`, `descontamina.py`, `serie.py`, `rebase.py` e
`pos-regra.py` estão aqui porque a alternativa era depositar um documento cujas
tabelas ninguém pode recomputar.

## O que cada um faz

### Estrutura do pool e os gaps

| script | o que mede | número que sustenta |
|---|---|---|
| `mede-delta.mjs` | pool de cobertura com `last_served` e `salience`, marcando quem é do estudo | pool 108 · 55/55 do estudo · 0 nunca-servidos · 44 grupos |
| `ordem.mjs` | compara as **sequências** servidas, não os conjuntos | 28 casos, 0 com ordem diferente — refuta o canal de reordenação |

### Efeito da dose

| script | o que mede | número |
|---|---|---|
| `dose2.mjs` | dual-compute offline **no caminho de produção** (corpus = snapshot de epoch, serve-state = vivo) | `churn` 0 em `w ∈ {2 · 4 · 7,5}` |
| `controle-positivo.mjs` | doses absurdas, para o nulo não passar sem checagem | `churn` 0 em `w = 100.000`, com 19 boosts emitidos |
| `dose-response.mjs` | ⚠️ **A PRIMEIRA VERSÃO, ERRADA.** Usou o DB vivo como corpus **e** como serve-state, exercitando caminho que produção não usa (`NOX_EPOCH_SNAPSHOT=active`). Versionado como registro do erro, **não para uso.** | — |

### A série de `churn`

| script | o que mede | número |
|---|---|---|
| `baseline.py` | linha de base bruta, janela fechada por `sha256` do NDJSON | 132/3.166 = 4,1693% — **superseded, diluída** |
| `rebase.py` | a mesma janela em três bases: tudo, pós-gate, pré-gate | pós-gate **132/2.212 = 5,9675%**; pré-gate **0/954** |
| `serie.py` | a taxa dia a dia, base pós-gate | 13,64% → 7,29% → 3,13% → 3,57% — **não estacionária** |
| `pos-regra.py` | regra velha × regra nova, e a série horária da nova | **11/310 = 3,5484%** sob a regra nova |

### Contaminação e auto-extinção

| script | o que mede | número |
|---|---|---|
| `descontamina.py` | reconstrói o estado excluindo as 15 linhas das minhas sondas | menor posição qualificável **1** (observado) × **18** (descontaminado) |
| `autoextincao.py` | composição dos grupos de `last_served` reconstruída dia a dia | 61,8% → 65,5% em grupo puro-estudo — **estável, não crescente** |

### Verificação do serving

| script | o que faz |
|---|---|
| `p2-designation-crosscheck.mjs` | lado TS do cruzamento: lê `p2_verdict` ao vivo e emite o `sha256` do conjunto, para comparar com `designation_verify.py`, que lê o CSV depositado |
| `verifica.py` / `verifica2.py` | confirmam por **estado observável** que o log novo traz `designated_ids` e `boost_by_id`, e que `boost_by_id ⊆ designados` |

## Como rodar

Os `.mjs` esperam estar em `tools/nox-mem/scripts/` de uma instalação do nox-mem,
com `dist/` compilado (`npx tsc`), e importam por caminho relativo `../dist/…`.
Os `.py` só precisam de `python3` e leitura do SQLite.

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
