# Plano do depósito v1.13 — preparado 2026-08-27, NÃO executado

> Nada foi enviado ao Zenodo. Este documento é o que se executa depois de você
> decidir os dois pontos abertos no fim.

## Por que **v1.13** e não v1.12-bis

A v1.12 **foi depositada de fato**: `10.5281/zenodo.22110203`, 2026-08-26T14:01Z, 60
arquivos, `version: "1.12"` no registro público. Logo o próximo número é **1.13**, sem
versão fantasma. *(Em 25/08 eu chamei de v1.13 um rascunho reprovado quando a v1.12
ainda não existia; era erro. Agora o incremento tem depósito atrás dele.)*

| | |
|---|---|
| conceito | `10.5281/zenodo.21964093` (não muda) |
| base | record **22110203** (v1.12) — `POST /api/records/22110203/versions` |
| registro emendado | OSF `yf7d2` |

## Base de escrita: a forma RDM, nunca a legada

`deposit/.published.json` é a serialização **legada** (13 chaves, `creators[0].name`,
**sem `publisher`**). Não serve como base: reenviá-la ao `PUT` faz o InvenioRDM
descartar `creators`, `rights`, `subjects` e `resource_type` **em silêncio, com HTTP
200** — foi assim que a v1.11 quase foi publicada sem autor e sem licença.

A base correta é `deposit/.draft-readback-rdm.json` (11 chaves, `person_or_org`,
`publisher: "Zenodo"`), normalizada para escrita: `rights`, `resource_type` e
`languages` reduzidos a `{id}`, e `related_identifiers[].relation_type` a `{id}`.

Muda **só** `version` (1.12 → 1.13) e `description` (bloco novo). Todo o resto é
herdado, incluindo `publisher`, que **não existe na forma legada** e cujo ausência
devolve `HTTP 400: "Missing publisher field required for DOI registration"` no
`publish` — e só no `publish`.

## Arquivos

60 no depósito atual. **6 mudaram**, **39 entram**, nenhum sai → **99**.
São **45 uploads** e ~1,0 MB. Conferido sem token: nenhuma chave duplicada,
nenhuma fonte local ausente, e a conta 60 + 39 fecha com o `NFILES` do script.

### Substituir (6 — delete + reupload; `files-import` traz a versão velha)

| arquivo | por que mudou |
|---|---|
| `claims_check.py` | removida a invariante de sobreposição de IC; `blob_check` e `janela_check` novos; alvo resolvido por conteúdo |
| `SERVING-CODE-MANIFEST.md` | commit corrigido para `1da78560`, `sha256` por arquivo, e a nota do hash pendurado |
| `serving-brief.ts` · `serving-brief-outcome.ts` | regra de designação nova (commit `1da78560`) |
| `DECISION-designacao-2026-08-25.md` | layout da chave corrigido antes de congelar |
| `DEPOSIT-README.md` → `README.md` | ganhou a seção **Start here, for v1.13** e o **mapa de chaves planas** — sem ele a citação `measurement/gap-defs.mjs` da emenda não resolve no depósito |

### Novos (39)

**A emenda e o que a sustenta (10)**

| depositado como | local | por que |
|---|---|---|
| `AMENDMENT-v1.13.md` | `AMENDMENT-DRAFT-band-collapse-2026-08-26.md` | o objeto do depósito |
| `REMEDIATION-2026-08-27.md` · `.json` | idem | as três medições refeitas; o `.json` guarda os dados brutos para recomputo |
| `MEASUREMENT-delta-cut-2026-08-26.md` · `DELTA-CUT-MEASUREMENT-2026-08-26.json` | idem | a medição de 26/08, **com banner de superseded** |
| `DESIGNATION-SEED-2026-08-26.md` · `DESIGNATION-2026-08-26.json` · `p2-verdict-frame-2026-08-26.csv` · `designation_verify.py` | idem | a cadeia da designação do §1 — a sexta leitura rederivou os 19 designados **só** com estes |
| `REVIEWS-PREREG.md` | idem | as 5 FATAIS; o §7 cita F2 e F3 por texto e hoje o leitor não tem o documento |

**Os blobs e o dado da janela (2)**

| depositado como | por que |
|---|---|
| `serving-p2-outcome-test.ts` | o §1 afirma que 5 mutações fizeram os testes falharem; sem o arquivo é infalsificável |
| `p2-serving-CLOSED-WINDOW-2026-08-26T2028-2026-08-27T0900.ndjson` | 352 linhas, 302.470 B, `sha256 5734036…` — torna `11/350` e `19/19 em 350 de 350` recomputáveis **do pacote** |

**`measurement/` (20) → prefixo `measurement-`**

Os 19 scripts + README. O §9 promete que estão públicos. Três vão marcados como
**registro de erro** (`dose-response.mjs`, `descontamina.py`, `pos-regra.py`).

**`receipts/` (7) → prefixo `receipts-`**

5 recibos + o recibo cunhado + **1 saída integral** (Codex decisório, 358.342 B).
⚠️ A emenda declara que as outras 4 saídas não existem (retratação 44).

⚠️ **Chaves são planas no depósito** — é a convenção que `SERVING-CODE-MANIFEST.md`
já usa (`src/api/brief.ts` → `serving-brief.ts`). `measurement/README.md` viraria
`measurement-README.md`, e o `DEPOSIT-README.md` (depositado como `README.md`) precisa
carregar o mapa, senão a citação `measurement/gap-defs.mjs` da emenda não resolve no
depósito.

### Não vão, e por quê

Notas de trabalho e planejamento: `CONCEPT.md`, `DECISIONS.md`, `NEXT-STEPS.md`,
`PLAN-2-TRILHAS.md`, `REVIEWS.md`, `OSF-SUBMISSION.md`, `METHODOLOGY.md`. Medições de
fases anteriores já superadas e não citadas pela emenda nova. `.remember/` — log de
sessão, **nunca**. `deposit/` — o mecanismo do depósito, não o objeto.

## Procedimento, e o que o torna seguro

```
export ZENODO_TOKEN=…                    # escopos deposit:write + deposit:actions
./deposit-v1.13.sh prepare               # cria draft, importa, sobe os 45, grava metadados. PARA.
./deposit-v1.13.sh sync                  # se o texto mudar depois do prepare
./deposit-v1.13.sh check                 # readback DUPLO + md5 dos 99. Não escreve nada.
./deposit-v1.13.sh publish               # IRREVERSÍVEL
```

**Readback duplo, e é obrigatório.** Uma conferência de 15 campos passou verde na
v1.12 e o `publish` devolveu 400: a verificação lia a forma legada, que **não contém**
`publisher`. Campo ausente da serialização é **invisível, não ausente**. Então:

1. `GET` default (legado) — pega apagamento de `creators`/`rights`/`subjects`;
2. `GET` com `Accept: application/vnd.inveniordm.v1+json` — pega `publisher` e conta
   as chaves de metadata contra a v1.12 publicada (a contagem é o detector).

**Nunca `curl -sf` no `publish`.** `-f` descarta o corpo do erro e, com `set -e` dentro
de `$(...)`, a saída fica **indistinguível de sucesso**: na v1.12 o script imprimiu
"publicando", voltou ao prompt, e só um `GET` público sem token revelou o 404. O
`publish` captura corpo e status separados, exige 2xx e imprime `errors[].field`.

**`POST /files` uma chave por vez.** Em lote com 2 chaves dá 400; uma por vez dá 201.

**Estado por consulta independente:** ao fim, `GET` público sem token no DOI novo.

## Antes de publicar — checklist de bloqueio

- [ ] `python3 claims_check.py` verde **depois** do rename para `AMENDMENT-v1.13.md`
      *(testado em 27/08: as duas checagens que prendiam o nome foram trocadas por
      resolução via conteúdo — uma delas **falhava aberta**)*
- [ ] `version` = `1.13` nas **duas** serializações do readback
- [ ] `publisher` = `Zenodo` presente na forma RDM
- [ ] `creators`, `rights`, `subjects`, `resource_type` intactos na forma legada
- [ ] 99 arquivos, md5 de cada um igual ao local
- [ ] nenhum arquivo com IP, hostname de tailnet ou token *(`receipts/` já redigido)*
- [ ] `git status` limpo e tag `paper2-v1.13` apontando para o commit depositado

## Duas decisões que são suas

**1. A saída do Codex (358.342 B) entra no registro permanente?**
A favor: é a única saída adversarial que existe, o Anexo B faz afirmação sobre ela, e
sem ela a revisão da 3ª rodada é inverificável como as outras quatro. Contra: são 358
KB de log de raciocínio de um modelo num registro científico permanente, e ela cita
trechos de prompts anteriores meus. **Minha recomendação: entra.** O custo é tamanho; o
ganho é a única auditabilidade real que a revisão tem.

**2. `measurement/` e `receipts/` entram, ou só a emenda + artefatos?**
Entrando, o depósito vai de 60 para 99 arquivos e cumpre o que o §9 promete. Não
entrando, o §9 tem de ser reescrito para dizer que os scripts vivem **só** no GitHub
(que é público, mas mutável — e um registro imutável apontando para repo mutável é
exatamente o defeito da retratação 1 da v1.12). **Minha recomendação: entram.**
