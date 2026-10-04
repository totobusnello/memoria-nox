# Paper A — systematic sweep of aged claims (item 5 of "O que falta")

Sweep date: 2026-10-03 (BRT) / 2026-10-04 (UTC). Target: `paper2-interventional/MANUSCRIPT.md`
(2,058 lines, 137,417 bytes). Nothing in the manuscript was edited; this file and
`_sprint-2026-10-04/A-aging/` are the only outputs.

Method. Every section was **read in full** (Abstract, §1–§9, Appendices A, B, C, D, H, E and the
final "O que falta" list), and every sentence that asserts a state — of the trial, the system,
the code, the data, the artifacts, the deposit or the paper itself — was classified:

| verdict | meaning |
|---|---|
| **still-true** | checked against an artifact or command on 2026-10-03/04 and holds |
| **STALE** | false today (or false when read today), with evidence |
| **NEEDS-DATE** | true at its instant, but written in present/relative tense without the instant, so it reads as a claim about today |
| **IMPRECISE** | not false, but disagrees with the canonical record (Paper B / DEVIATIONS) |
| **NOT MEASURED** | could not be checked; reason given |

After the reading pass, a mechanical grep for temporal/state words was run as a coverage net
(`grep -n -o -i -E '.{0,50}\b(hoje|agora|ainda|atualmente|em vigor|vigente|até que|não existe|existem?|desde|há [0-9]+|semanas|restam|restavam|continua|neste momento|no fechamento|sobreviv[a-z]+|para sempre|sem escritor)\b.{0,40}' MANUSCRIPT.md`,
126 hits); every hit was either already classified below or is a non-state use of the word
(e.g. "existe para", "sobrevive" about a proposition).

Numbers about the study period (67,187 chunks, 583,763 slots, 17/350, …) are **not** stale just
because the corpus is now 43,255 chunks; only claims that read as statements about *now* are.

---

## 0. Facts of today, verified (and one correction to the task brief)

| fact | verified how | result |
|---|---|---|
| dose switched off 2026-09-21 09:43:05Z | `DEVIATIONS-FOR-PAPER.md` §10.29 table; `MANUSCRIPT-B.md:179-180` | confirmed |
| trial went active 2026-09-01 10:25:39Z | `MANUSCRIPT-B.md:179`; `TRIAL-START-2026-09-01.md:16` | confirmed |
| realized window | `DEVIATIONS` §10.31(1), `MANUSCRIPT-B.md:271-291`, `docs/HANDOFF.md` 2026-09-21 | ⚠️ **the task brief's "17 full + 2 partial" is the figure that §10.31(1) retracted the same day.** Canonical: **20 epochs realized, 19 with data = 16 whole + 3 partial (`09-01` mixed, `09-03` 441/672, `09-20` partial by clock, 13.86 h) + 1 empty (`09-02`)**; arms by designation 8 control (`w=0`) + 11 treatment (`w=2`×6, `w=4`×4, `w=7.5`×1) |
| ITT analysis closed 2026-09-21 | `docs/HANDOFF.md` "2026-09-21 (noite)" | confirmed |
| Paper B exists | `MANUSCRIPT-B.md` header "DRAFT opened 2026-09-21"; not deposited (same header: "What is not done: … deposit") | confirmed |
| `e20260826T060003Z.db` exists nowhere | `ssh $NOX_LASTRO_HOST 'find / -xdev -name "e20260826*"'` → 0 hits; first-MB sha256 of the 4 preserved trial DBs (`16d12816…`, `a7b18997…`, `12dbfe57…`, `0a78171f…`) ≠ the pin `56826f69…`; `find ~/Backups ~/Claude ~/Claude-archive -name 'e20260826*'` → 0 hits (non-JSON). Production not searched by me (task rule); `docs/HANDOFF.md:25-27` reports it was searched there | confirmed where searched |
| 4 trial DBs moved to `$NOX_LASTRO_HOST:/var/backups/nox-mem/paper2-bancos-ensaio/` | `ls -la` on the host: the 4 files, mode `0400`, `RECIBO.txt`, `p2-bancos-ensaio.sha256` | confirmed. The manuscript cites **none** of these paths (`grep -n '/var/\|/root/\|srv1\|VPS\|corpus-preservado\|p2-ord' MANUSCRIPT.md` → 0 hits), so the move ages no claim |
| corpus today ~43.3k | `docs/HANDOFF.md` 2026-09-29/30: 43,255 | confirmed (not re-measured; production off-limits) |

Facts found during the sweep that the brief did not list, and that age claims in the manuscript:

1. **Paper A v1.0 is published on Zenodo.** `curl https://zenodo.org/api/records/22181415` →
   `status: published`, version `1.0`, created `2026-08-30T21:39:24Z`, updated
   `2026-09-08T01:37:15Z`, title = this manuscript's, language `por`, 13 files including
   `MANUSCRIPT.md` (126,564 B). `…/versions/latest` redirects to `22181415` itself (no later
   version). Concept DOI `10.5281/zenodo.22181414`. The manuscript never mentions either DOI
   (`grep -n '22181415\|22181414' MANUSCRIPT.md MANUSCRIPT-B.md DEVIATIONS-FOR-PAPER.md` → 0).
   The pre-registration record `22110203` (v1.12) is still its own latest version
   (`…/22110203/versions/latest` → `22110203`).
2. **The "missing" frozen action corpus exists**, at its declared path, on the research host:
   `$NOX_LASTRO_HOST:/var/backups/nox-mem/paper2-corpus/action-archive-20260729T094609Z.tar.gz`,
   111,855,897 B, born 2026-07-29 06:46 −03, `sha256 ba5fcc81f43cede6e40572236be984bc0cc5e450325b115e2b994f5a24cdf382`
   = the pin in `CORPUS-FREEZE.md`; its manifest `manifest-20260729T094609Z.txt` has
   `sha256 2fe8ba2b…6c5638` = the pin, 3,860 lines = the declared count; `verdicts/full.jsonl`
   has 5,547 lines = the declared 5,547 episodes. `DEVIATIONS` §9 (l.255-256) shows the 2026-08-30
   search covered only "toda a máquina de serving".
3. **But the 280 adjudicated episodes were never in that corpus.** `p2_verdict` (read from a
   copy of `corpus-preservado-20260908.db` in `/var/tmp/sprint-A-aging-*` on $NOX_LASTRO_HOST, copy
   deleted after): 280 rows, 280 distinct ids, `adjudicated_at` 2026-08-15T09:30:20Z →
   2026-08-21T02:43:22Z, 14 distinct panel hashes. Of the 280 ids: **0** in the frozen
   `full.jsonl`, **0** in `calib300-FINAL`/`peca3-pass1`/`peca3-novos`, **0** as `episode_id` in
   the trial lastro (`episodios-ensaio-20260921.jsonl`, `episodios-janela-20260921.jsonl`,
   `alvo-painel-20260921.jsonl`). The ids list is saved as `A-aging/p2_verdict_ids-280.txt`.
4. **Per-chunk search telemetry got its writer back on 2026-08-27.** `git -C nox-workspace log -S top_chunk_ids`
   → `32f78109 2026-08-27 22:18:34 +0000 fix(nox-mem): religa a telemetria por chunk…` and
   `ffb02a4f 22:39:34 +0000` (drops `query_text`); `docs/HANDOFF.md:1547-1549`: "commit
   `32f78109` na VPS … busca real gravou". Current `search.ts:641` INSERT lists
   `top_chunk_ids, top_scores`. Production's writer state today: NOT MEASURED.
5. **Ingestion was broken during the measured window.** `DEVIATIONS` §10.5: `MAX(created_at)`
   stuck at 2026-08-24 01:06:35 until 2026-09-07T14:06:13Z (watcher invoking a missing binary;
   zero chunks created 08-25…09-06). §10.7: zero `sessions/%` chunks created 2026-08-11 → 09-07
   (VPS migration moved address and schema of transcripts; cron reported `ok`); after the repair,
   per-agent fresh eligibles 219 → 285 (`docs/HANDOFF.md` 2026-09-09).

---

## 1. Claim-by-claim table

Line numbers are of `MANUSCRIPT.md` as of this sweep.

### Header

| l. | claim | verdict | evidence |
|---|---|---|---|
| 3-10 | title changed 2026-08-29 | still-true | dated |
| 12-16 | "🟡 **ESQUELETO, 2026-08-27** … onde não há [número], está escrito `[FALTA]`" | **STALE** | v1.0 published 2026-08-30 (fact 1); only one `[FALTA]` left (`grep -n FALTA` → l.15 rule, l.1837, l.2044 mention) → **F4** |
| 18-20 | source list | still-true | all 5 files exist (`find` per name) |

### Abstract

| l. | claim | verdict | evidence |
|---|---|---|---|
| 26-33 | survey 218 papers, 12 weeks, 6 agents, brief 10 items | still-true (historical) | 84.67 days from `out/superficie.json` (`desde`/`ate`) |
| 34-47 | 583,763 slots, 67,187, 1,635 / 2.43%, 83.78%, 9,755 / 10,899 | still-true (study-period numbers) | `out/superficie.json` |
| 49-54 | 3 chunks in 100% of 4,632 briefs, "last accessed 90, 30, 42 days ago (measured at window close, 2026-08-28)" | still-true (dated) | 2026-08-28 − {05-30, 07-29, 07-17} = {90, 30, 42} |
| 55-60 | coverage pool of 108, exhausted every day | still-true as measured; **context aged** | measured inside the broken-ingestion regime (fact 5) → **F13** |
| 66-69 | "estados de produção; a intervenção não foi servida … o que o agente recebeu foi sempre o controle (§7)" | **NEEDS-DATE** | true for the measured window; the trial served treated briefs 2026-09-01 → 09-21 (fact table) → **F7** |
| 69-74 | saturation, 4.86%, 7.43%, 36%, 80% | still-true | artifacts exist (`CEILING-*`), numbers unchanged |
| 74-77 | "🔴 **Um terceiro eixo existe e não foi medido** … o teto foi computado sem excluí-las" | **STALE (internal)** | §5.7.2 l.1312-1321: measured 2026-08-30, 17 → 13/350 (4.86% → 3.71%), artifacts `out/CEILING-PROBE-EXCLUSION-{none,probes}-2026-08-30.json` exist → **F1** |
| 79-92 | what we do not claim | still-true | scope statements |

### §1

| l. | claim | verdict | evidence |
|---|---|---|---|
| 96-100 | "julgado, hoje, pela qualidade da recuperação" | still-true | generic present, about the field |
| 108-116 | 84.7 days, 583,763, 8.7×, 1,635, 83.78% | still-true (historical) | `out/superficie.json` |
| 129-135 | "calendário … medimos cinco dias seguidos com zero itens novos … +1,00 por dia" | still-true as observed; **cause aged** | the per-agent lot of 09–10/08 expired ~08-16/17; `sessions/%` ingestion produced 0 chunks 08-11 → 09-07 by defect (fact 5) → **F13** |
| 141-145 | replay over 350 states, "intervenção não servida (modo shadow, §7)" | **NEEDS-DATE** | → **F7** |
| 159-182 | survey counts, sha256 of PDF | still-true | `measurement/survey-string-count.py` exists |
| 191-207 | contributions; 17 defects, 8 that changed a number | still-true | Appendix E/§6 count unchanged |

### §2

| l. | claim | verdict | evidence |
|---|---|---|---|
| 211-213 | "frota de 6 agentes … em operação contínua, servindo ~670 briefs/dia" | **NEEDS-DATE** | present tense; measured week = 4,632 briefs / 7 d = 661.7/day (`superficie.json` `briefs_7d`); today's rate NOT MEASURED (production off-limits) → **F19** |
| 213-214 | "no instante da medição, 67.187 chunks" | still-true (dated by "instante", but the instant is not named) | `superficie.json` `gerado_em 2026-08-28T10:02:23Z`; today 43,255 → **F18** |
| 222-224 | brief "sempre com 10 itens" | already flagged by the paper itself (§4.3 l.613-625) | not an aging issue |
| 237-238 | `freshSlots = 2` "por default de configuração sem override" | NEEDS-DATE | → **F16** |
| 248-256 | Figure 0 from `out/superficie.json` | still-true | both files exist |

### §3

| l. | claim | verdict | evidence |
|---|---|---|---|
| 267 | `brief_log` "sem poda — a única `DELETE FROM brief_log` do repositório está num teste" | still-true (source) | `grep -rn 'DELETE FROM brief_log'` in `nox-workspace/tools/nox-mem/src` → only `__tests__/epoch-serving.test.ts:74` (commit `11296e3c`, 2026-09-29). Production table not inspected |
| 268 | `access_count` incremented only by search; brief never writes it | still-true (source) | only `search.ts:396` has the `UPDATE … access_count + 1`; same line in the deposited `serving-search.ts` |
| 277-279 | "a telemetria por chunk … **está** sem escritor desde 2026-05-19 (§6)" | **STALE** | writer restored 2026-08-27 22:18Z (fact 4) → **F6** |
| 300-302 | replay "importa a função de composição do binário de produção" | NEEDS-DATE (minor) | production code changed since (nox-workspace PRs #49–#53, 2026-09-29/30); the replay imported the binary of 2026-08-27/28 → **F24** |
| 304-313 | fidelity table, command | still-true | `out/c-350-v3.json`, `out/c-350.json` exist; their corpus input does not → **F11** |

### §4.1 / §4.1.1

| l. | claim | verdict | evidence |
|---|---|---|---|
| 319-332 | table "corpus **vivo** 67.187", union, complement | NEEDS-DATE (label) | "vivo" = live at 2026-08-28; live today = 43,255 → **F18** |
| 350-356 | predicate at `brief.ts:642`; values at `brief-diversity.ts:59-60`, env at `:88-89`; "Verificado no processo servidor em 2026-08-29" | still-true (dated; line refs resolve) | current source: l.59-60 `freshMinImp/Pain: 0.7`, l.88-89 env parse, `brief.ts:642` predicate |
| 381-405 | cohort table; "Um chunk criado na semana 11…" | still-true (historical) | `out/EXPOSURE-BY-COHORT-2026-08-29.json` exists |
| 409-422 | slots not fungible; "estaria vinculante *hoje*" | still-true | hypothetical "hoje", not a state claim |
| 439-443 | intersection 491, "Acrescentado em 2026-09-21" | still-true | dated |
| 445-449 | "o complemento conta o que existe *hoje* e nunca foi" | **NEEDS-DATE** | "hoje" = 2026-08-28; today the corpus is 43,255 → **F18** |

### §4.2

| l. | claim | verdict | evidence |
|---|---|---|---|
| 459-473 | type table | still-true (historical) | |
| 475-480 | filter "continua no código" | still-true | `superficie-de-exposicao.py` still has the filter (not re-checked line-by-line; script exists) |
| 538-541 | "`pending` tem 6 dias de idade" | NEEDS-DATE | relative to 2026-08-28 → folded into **F18** |
| 574-590 | Figure 1 guard "agora recusa o artefato filtrado" | still-true | `measurement/fig1-capacidade.py` exists; guard not re-executed |

### §4.3 / §4.3.1 / §4.3.2

| l. | claim | verdict | evidence |
|---|---|---|---|
| 598-611 | closed window `[2026-08-20, 2026-08-27)` numbers | still-true (dated) | `superficie.json` `janela_7d` |
| 613-626 | 25 missing slots = 5 probes × 5 (open, dated 2026-09-21) | still-true | open item, not aging |
| 647-655 | "Em 30/08, 10.899 … o mais novo tem 20,5 dias … a ingestão dessa família **parou há três semanas** … **Metade do canal de cobertura está inerte por idade, não por desenho**" | **STALE in cause / NEEDS-DATE** | relative time; cause later established as an ingestion defect (fact 5) → **F13** |
| 657-662 | "estava registrada … desde 27/08 e não tinha sido cumprida" | still-true | dated |
| 664-686 | `POOL-ELEGIVEL-2026-08-28.json` covers one day (declared 2026-09-21) | still-true | file exists; `"dia": "2026-08-28"` per the text |
| 676-682 | "servidos no dia 108 — 100% do pool, em 26, 27, 28 e 29/08" | still-true as measured; **context aged** | those four days are inside the total ingestion freeze 08-24 01:06Z → 09-07 14:06Z (`DEVIATIONS` §10.5) → **F13** |
| 723-726 | channel attribution, 40 briefs of 29/08 | still-true | `measurement/CHANNEL-ATTRIBUTION-2026-08-29.json` exists; its corpus was the live main DB of 2026-08-29 (procedencia), no longer reproducible — a property of all live-DB measurements, declared in **F11** |
| 737-739 | "o corpus cresceu para fora deles" | still-true as of window; context → **F13** |
| 741-744 | 20/08: 33 vs 85, "52 não existem mais" | NEEDS-DATE (minor) | "mais" = at 2026-08-28/29 → **F17** |
| 761-770 | 3 chunks table; "**há 90, 30 e 42 dias — e ganham todos os briefs de hoje**" | **NEEDS-DATE** | the Abstract dates it (2026-08-28), §4.3.2 does not → **F17** |
| 789-799 | "**52 foram apagados desde então**" | NEEDS-DATE | → **F17** |
| 819-821 | "dos 9.755 … **7.908 (81%) estão há mais de 60 dias** sem serem acessados" | NEEDS-DATE; **no artifact found** | `grep -rln '7908\|7\.908'` over `out/*.json`, `*.json`, `measurement/*.json`, `SUPERFICIE-2026-08-27.md` → 0 files → **F17** |
| 831-838 | `search.ts:396`; brief header "read-only sobre `chunks`" | still-true (source) | verified in current source and in the deposited snapshot |

### §4.4 / §4.5

| l. | claim | verdict | evidence |
|---|---|---|---|
| 859-864 | "A coluna `w = 2` é a **dose em vigor** no *shadow* … **nunca entregue a agente nenhum**" | **STALE (reads as today)** | `w = 2` was served `active` in 6 trial epochs (`DEVIATIONS` §10.29: 09-04, 05, 08, 09, 16, 19); "em vigor" ended with the trial → **F7** |
| 877 | "a dose em vigor no *shadow* reproduz a taxa publicada" | **NEEDS-DATE** | → **F7** |
| 904-907 | "0 linhas — medido em 2026-08-30 e não re-verificado após o fecho do ensaio em 2026-09-20" | IMPRECISE | dose off 2026-09-21 09:43:05Z, window closed at the 09-20 epoch (Paper B l.179-180) → **F8**. Re-verification: NOT MEASURED (needs production) |
| 908-910 | "a telemetria de busca **registra** sobretudo a sonda de saúde … em janela fechada de 7 dias, 325 de 343" | NEEDS-DATE | window from the 2026-08-27 incident analysis (`docs/INCIDENTS.md` 2026-05-19 entry) → **F6** |
| 910-911 | "das 25 colunas … **16 não têm escritor hoje**, entre elas a única com identificação por chunk" | **STALE** | fact 4 → **F6** |
| 915-919 | "estudo interventivo, que não está reportado aqui" | still-true | could point to Paper B (→ **F10** proposes the pointer) |
| 923-925 | `last_served` realimenta | still-true | analytic |

### §5

| l. | claim | verdict | evidence |
|---|---|---|---|
| 941-948 | comparator verbatim `brief-diversity.ts:130-140` | still-true | current l.130-140; file sha256 `34c9aee5…` = the 2026-08-30 pin in `SERVING-CODE-MANIFEST.md` |
| 955-960 | `brief.ts:612-614` | still-true | current l.612, 614; also in deposited `serving-brief.ts` |
| 965-971 | `D` = 19 chunks, rederived by third party | still-true | |
| 1005-1012 | "`NOX_BRIEF_DIV_FRESH_SLOTS` … **não há override** nem na unit systemd nem no `.env` — verificado" | **NEEDS-DATE** | verification source `SUPERFICIE-2026-08-27.md:103`; the unit later carried the trial drop-in `zz-p2-active.conf` (8th of 8, `TRIAL-START-2026-09-01.md:12`) → **F16** |
| 1061-1066 | item 7 trigger reimplemented | still-true (past) | triggers retired 2026-09-21 (→ **F22** for Appendix D) |
| 1149-1155 | "**Procedência da rodada.** Corpus = snapshot de epoch `e20260826T060003Z.db`…" | **STALE (omission)** | the DB exists nowhere (fact table); `MANUSCRIPT-B.md:447-450` declares it, this line does not → **F11** (the known item) |
| 1162-1171 | `served_at` resolution from `datetime('now')`; "tem um único consumidor vivo no serving"; `serveCounts` uncalled (`brief.ts:588`) | still-true (source) | `brief.ts:293` default `datetime('now')`; `served_at` read at l.571 (`serveCounts`), 679, 730 (both `MAX(served_at)` = stratum key); `grep -rn 'serveCounts('` outside tests → only the definition (l.557) |
| 1180-1184 | granularity table "byte a byte os mesmos" | still-true | `out/gran-*.json` exist; corpus input gone → **F11** |
| 1213-1217 | 8 alternative designations | still-true | `out/sens-*.json` exist; corpus input gone → **F11** |
| 1301-1305 | "Existiam, no repositório, dois artefatos gravados em 27/08" | still-true | `out/ancora-sondas.json`, `out/ancora-sem-exclusao.json` exist |
| 1312-1321 | measured 30/08: 13/350, 3.71% | still-true | `out/CEILING-PROBE-EXCLUSION-*-2026-08-30.json` exist |
| 1350-1363 | paired design "sobre o mesmo corpus de 30/08" | still-true as run; **input now perishable, undeclared** | artifacts' `procedencia.corpus = /var/lib/nox-mem/epochs/e20260830T060001Z.db` (first-MB `3679bca8…`); not on $NOX_LASTRO_HOST (`find / -xdev -name 'e20260830*'` → 0), not on the Mac dirs, not among the 4 preserved DBs (hash mismatch); production NOT searched → **F12** |
| 1365-1369 | "o corpus do replay … foi rotacionado; em 30/08 restavam apenas os de 28 a 30/08" | still-true (dated) | |
| 1375-1376 | "o log de janela fechada com os 350 estados **sobreviveu**" | still-true | `p2-serving-CLOSED-WINDOW-2026-08-26T2028-2026-08-27T0900.ndjson` exists (352 lines) |
| 1381-1388 | "**Existem** na máquina de serving um `campo-churn.json` e um `campo-churn-sem-exclusao.json`" | **NEEDS-DATE / NOT MEASURED** | not in the repo, not in the Mac lastro (`find` → 0); production not inspected → **F21** |

### §6 / §6.1 / §6.2

| l. | claim | verdict | evidence |
|---|---|---|---|
| 1431 | table: telemetry "**muda** desde 2026-05-19 … e **nulo para sempre depois**" | **STALE** | fact 4 → **F6** |
| 1449-1454 | `claims_check.py`; 19 of 32 on 29/08 | still-true (dated) | |
| 1456-1458 | "**hoje** ele diz **10 de 32 — 31,2%**" | still-true, NEEDS-DATE | `out/CLAIM-COVERAGE-2026-08-29.json`: `pct_sem_guarda 31.2`, mtime 2026-08-29 10:03 → **F20** |
| 1467-1470 | 30/08 round closed the remaining 10, "0 das 32" | still-true per text; **no artifact for the 0** | the coverage artifact was not rerun after 30/08 (it still says 31.2%) — out of scope for aging, noted |
| 1493-1505 | 583,973 → 583,763; "a grandeza **cresce ~7.500 por dia**"; corrected 2026-09-21 | NEEDS-DATE | present tense on a live series → **F20** |
| 1507-1511 | 2.66% → 2.43%, corrected 2026-09-21 | still-true | dated |
| 1530-1534 | table row 1: corpus of the ceiling replay rotated | still-true | |
| 1533 | row 2: three serving modules repinned by sha256 on 30/08 | still-true | `serving-brief-diversity.ts` and `serving-salience.ts` sha256 = pins; current `nox-workspace` `brief-diversity.ts`/`salience.ts` = pins too; `search.ts` changed after the pin (expected: telemetry restore) |
| 1534 | row 3: "corpus congelado do estudo interventivo … **não existe** — procurado por nome, tamanho e hash; nem o diretório. Com ele foram os **280 episódios adjudicados**, dos quais **zero** sobrevivem no archive vivo" | **STALE / MISATTRIBUTED** | the corpus exists, hash-identical, on the other host (fact 2); the 280 were never in it (fact 3) → **F5** |
| 1542-1547 | "o material julgado sumiu. Sobrou **veredito sem evidência**" | still-true for the 280; wrong in implying it went with the frozen corpus | fact 3 → **F5** |
| 1554-1560 | "Tudo correto, e o arquivo não existe … só a tentativa de usar o artefato distingue" | **STALE** | the file exists at the declared path, on a host the search did not cover → **F5** |

### §7, §8, §9

| l. | claim | verdict | evidence |
|---|---|---|---|
| 1564-1580 | n = 1, small types, `access_count`, regime break explained | still-true | |
| 1581-1582 | "a intervenção **correu** em modo **shadow**: … nada foi servido tratado" | **STALE (reads as the whole intervention)** | trial served 11 treatment epochs (fact table) → **F7** |
| 1588-1598 | related work | still-true | |
| 1655-1660 | "Rodou — de 2026-09-01 a 2026-09-20, 20 epochs designados, 19 servidos" | IMPRECISE | dose off 2026-09-21 09:43:05Z; 19 with data = 16 whole + 3 partial; 11 treatment + 8 control → **F8** |
| 1662-1667 | "ficou falsa por três semanas"; "a varredura que o item 5 … declara aberta" | still-true | this sweep is the varredura; item 5 stays open until findings are applied |
| 1678-1683 | reading dates 13/08, 15/08, 28/08 | still-true | dated |
| 1692-1694 | "583.763 slots — a série viva **no instante do congelamento, 2026-08-29**" | **WRONG DATE** | `superficie.json`: series `ate 2026-08-28 09:52:08`, `gerado_em 2026-08-28T10:02:23Z` (84.67 days from `desde 2026-06-04 17:51:26`) → **F15** |
| 1709-1711 | `freshSlots = 2` default without override | NEEDS-DATE | → **F16** |
| 1734-1737 | "Dezanove epochs foram servidos … **a intervenção correu sem o mover**" | **IMPRECISE + UNSUPPORTED** | 8 of the 19 were control; no artifact measures the ceiling under the trial (`grep -n -i 'ceiling\|4\.86\|4,86' MANUSCRIPT-B.md` → 2 hits, neither a measurement) → **F9** |
| 1745-1748 | "**16 colunas de telemetria sem escritor** … uma delas exatamente a que registrava quais chunks a busca devolveu" | NEEDS-DATE | true for the window; writer restored 2026-08-27 → **F6** |

### Appendices

| l. | claim | verdict | evidence |
|---|---|---|---|
| 1760-1763 | prereg OSF `yf7d2`, Zenodo `22110203`; trial "começou em 2026-09-01 10:25:39Z e **fechou em 2026-09-20**, com 20 epochs designados (19 servidos…)" | IMPRECISE | → **F8**; `22110203` still latest of its concept (Zenodo API) |
| 1765-1767 | "**Os resultados interventivos não estão aqui**: são o Paper B, e vivem em `DEVIATIONS` §10.29–§10.34 **até que ele exista**" | **STALE** | `MANUSCRIPT-B.md` exists (draft opened 2026-09-21) → **F10** |
| 1786 | "(v1.12 §5) a designação é defeito aberto" | still-true | v1.12 is still the latest prereg version |
| 1796-1798 | full deviation list "pertence ao paper interventivo" | still-true | |
| 1802-1805 | drand round 31657512, 1,056 s | still-true | historical |
| 1809-1813 | panel κ "pertencem ao estudo interventivo e **são reportados lá** — inclusive … κ agregado de 0,874" | PARTIAL | Paper B l.853-854 reports the split κ (0.87–0.93 vs 0.31–0.53); `grep -n '0\.874\|0,874' MANUSCRIPT-B.md` → 0 → **F23** |
| 1822-1835 | Appendix D artifact table | still-true (files) / **inputs gone** | every listed artifact exists (per-name `find`; `out/gran-*`, `out/gran3-*`, `out/sens-*`, `measurement/implantacao/` all present); the replay inputs (`e20260826…`) do not → **F11**; triggers retired → **F22** |
| 1837-1838 | "**[FALTA]** DOI de um depósito que contenha **este** manuscrito … **Hoje o último depósito é a v1.12, anterior a tudo isto.**" | **STALE** | fact 1 → **F2** |
| 1847-1851 | "87 marcadores … 77 dos 288 parágrafos — 26,7%" (before cleanup, 30/08) | still-true (dated) | `out/WARNING-DENSITY-2026-08-30.json` |
| 1853-1856 | "No corpo … **restam 91 de 297** parágrafos marcados (30,6%)" | **STALE** | that artifact was computed on a 1,914-line text; recomputed 2026-10-03 with the same script on the 2,058-line text: body **100 of 307 (32.6%)**, all paragraphs 119 of 363 (32.8%), 133 markers (`A-aging/WARNING-DENSITY-recomputed-2026-10-03.json`) → **F14** |
| 1860-1868 | "Medido em 30/08, o §4.2 tinha 12 marcadores…" | still-true (dated) | |
| 1870-1873 | densidade script "promete classificar … e não classifica" | still-true | script header unchanged (read l.1-40) |
| 1983 | 16 columns census | still-true (dated by "ao longo de 10 dias" / incident) | |
| 1984 | "`requesting_agent` … é nulo para todo mundo desde 2026-05-18" | still-true (source) | current INSERT (`search.ts:641`) does not list `requesting_agent`; production NOT MEASURED |

### "O que falta"

| l. | claim | verdict | evidence |
|---|---|---|---|
| 1991-2000 | "Feito em 28/08" list | still-true (dated) | |
| 2018-2026 | item 3 done 2026-09-21 (Kimi); "o Paper B levou três" | still-true | `REVISAO-ADVERSARIAL-2026-09-21.md:14` "Paper B — três vozes" |
| 2031-2032 | item 4 "**depósito** com o manuscrito + artefatos" listed as pending | **STALE** | v1.0 deposited 2026-08-30 (fact 1); what is pending is a new version → **F3** |
| 2034-2039 | item 5 PARTIAL | still-true until this sweep is applied | |
| 2041-2045 | open items incl. "o `[FALTA]` do DOI no Apêndice D" | **STALE (part)** | → **F3** |
| 2047-2051 | item 6 | still-true | |
| 2053-2058 | old item 5 | still-true (historical) | |

---

## 2. Findings (stale / needs-date only), with drop-in English

Severity: 🔴 a reader or reviewer checking the public record would find the sentence false ·
🟡 misleading without the date · ⚪ hygiene.

- **F1 🔴** Abstract l.74-77 — third axis "not measured"; it was measured on 2026-08-30 (§5.7.2).
- **F2 🔴** Appendix D l.1837-1838 — "[FALTA] DOI … latest deposit is v1.12"; Paper A v1.0 is `10.5281/zenodo.22181415` (2026-08-30).
- **F3 🔴** "O que falta" l.2031-2032, l.2044 — deposit listed as not done.
- **F4 🟡** Header l.12-16 — "ESQUELETO" banner.
- **F5 🔴** §6.2 l.1534, l.1542-1547, l.1554-1560 — frozen corpus "does not exist"; it exists hash-identical on $NOX_LASTRO_HOST, and the 280 were never in it.
- **F6 🔴** §3.1 l.277-279, §4.5 l.908-911, §6 l.1431, §9 l.1745-1748 — telemetry "has no writer"; restored 2026-08-27 22:18Z.
- **F7 🔴** Abstract l.66-69, §1 l.142-143, §4.4 l.859-861 and l.877, §7 l.1581-1582 — "never delivered / shadow / dose em vigor" read as the whole intervention.
- **F8 🟡** §4.5 l.906, §8.3 l.1657-1658, Appendix A l.1761-1763 — trial end date and epoch accounting.
- **F9 🔴** §9 l.1734-1737 — "19 epochs served … ran without moving it".
- **F10 🔴** Appendix A l.1765-1767 — "until Paper B exists".
- **F11 🔴** §5.6 l.1149-1151 (+ Appendix D) — replay corpus `e20260826T060003Z.db` gone, undeclared (the known item, generalized to all 8 replay artifacts that cite it).
- **F12 🟡** §5.7.2 l.1350-1363 — the paired-design corpus `e20260830T060001Z.db` is not preserved.
- **F13 🔴** §4.3.1 l.653-655 (+ §1 l.129-133, table l.676-682) — "ingestion stopped three weeks ago … inert by age, not by design"; cause later established as an ingestion defect.
- **F14 🟡** Appendix H l.1853-1856 — 91/297 (30.6%) is stale; today 100/307 (32.6%).
- **F15 🟡** §9 l.1692 — 583,763 dated 2026-08-29; the artifact says 2026-08-28 09:52:08Z.
- **F16 🟡** §5.3 l.1005-1007 — "no override — verified" undated (2026-08-27).
- **F17 ⚪** §4.3.2 l.769-770, l.796-797, l.819-821 — relative times ("hoje", "desde então", "há mais de 60 dias"); the 7,908 has no artifact.
- **F18 ⚪** §4.1 l.321 and l.445-449, §2 l.213-214, §4.2 l.540 — "corpus vivo" / "hoje" without the instant.
- **F19 ⚪** §2 l.211-213 — "servindo ~670 briefs/dia".
- **F20 ⚪** §6.1 l.1458, l.1498-1499 — "hoje ele diz", "cresce ~7.500 por dia".
- **F21 ⚪** §5.7.2 l.1381-1382 — "Existem na máquina de serving".
- **F22 ⚪** Appendix D l.1835 — monitoring triggers listed without their retirement.
- **F23 ⚪** Appendix C l.1811-1813 — "são reportados lá", but Paper B does not carry the 0.874 aggregate.
- **F24 ⚪** §3.3 l.300-302 and the code line citations — not pinned to a commit.

The exact proposed English text for each finding is in the structured output returned to the
orchestrator (field `proposed_en`), so the translation can drop it in.

---

## 3. NOT MEASURED, and why

- **Anything requiring the production host (`$NOX_PROD_HOST`)**: the task asks to avoid it. Not
  measured: current `search_telemetry` writer state per column; whether `brief_log` was ever
  pruned in production; whether the 3 agent-quality tables still have 0 rows after the trial
  (§4.5); current `freshSlots`/`freshMin*` environment of the serving process; current brief
  rate (§2); whether `campo-churn*.json` still exist there (§5.7.2); whether
  `e20260830T060001Z.db` or `e20260826T060003Z.db` survive there (HANDOFF 2026-10-04 reports the
  latter searched there; the former was not searched by anyone, as far as the records show).
- **The 16-column census today**: needs production data; only the source-level INSERT was read.
- **Whether the 280 adjudicated episodes exist anywhere**: searched the frozen corpus and its
  verdict files on $NOX_LASTRO_HOST and the trial lastro on the Mac (0/280). Not searched: the live
  action archive on production, the Pesquisa copy of the trial lastro
  (`/var/backups/nox-mem/paper2-lastro-ensaio/`, assumed identical to the Mac copy by its
  manifest, not re-read).
- **The 7,908 figure (§4.3.2)**: no artifact found; its instant cannot be recovered from files.

## 4. Out-of-scope observations (not aging; recorded so they are not lost)

- §5.6 l.1153 says the divergent first run excluded "**6** sondas"; everywhere else there are
  **five** probes (25 rows). One of the two is wrong or they refer to different counts.
- §6.1 l.1467-1470 claims the 30/08 round reached "0 das 32"; the coverage artifact was never
  rerun after 29/08 and still reads 31.2%. The 0% has no artifact.
- `DEVIATIONS-FOR-PAPER.md` §9 (l.249-273) carries the same "does not exist" claim as §6.2 and
  needs an append-only errata (not edited here: task rule).
- The orchestrator's fact list said "17 full + 2 partial"; that count was retracted by
  `DEVIATIONS` §10.31(1) the same day. The memory index (`MEMORY.md`: "P2 ENCERRADO (21/09): 17
  inteiros + 2 parciais") carries the retracted figure too.

## 5. Commands and artifacts

- `A-aging/WARNING-DENSITY-recomputed-2026-10-03.json` —
  `python3 measurement/densidade-de-avisos.py --doc MANUSCRIPT.md --json --out _sprint-2026-10-04/A-aging/WARNING-DENSITY-recomputed-2026-10-03.json`
- `A-aging/p2_verdict_ids-280.txt` — `SELECT episode_id FROM p2_verdict ORDER BY 1` on a
  `/var/tmp` copy of `corpus-preservado-20260908.db` on $NOX_LASTRO_HOST (copy deleted; `ls -d
  /var/tmp/sprint-A-aging-*` → 0 afterwards). No original DB was opened with `sqlite3`.
- Zenodo: `curl https://zenodo.org/api/records/22181415`, `…/22181415/versions/latest`,
  `…/22110203/versions/latest`.
- $NOX_LASTRO_HOST: `ls -la` of `paper2-bancos-ensaio/` and `paper2-corpus/`; `head -c 1048576 | sha256sum`
  of the 4 trial DBs; `sha256sum` of the action archive and its manifest; `wc -l` of the verdict
  files; `tar -tzf … | wc -l` (3,878 entries); `find / -xdev -name 'e20260826*' -o -name 'e20260830*'`.
- Source: `nox-workspace/tools/nox-mem/src` at commit `11296e3c` (2026-09-29) — `grep`s and
  `shasum -a 256` listed in the tables above; `git log -S top_chunk_ids`.
- No git command was run in `memoria-nox`; the only `git` invocations were read-only `log` in
  `nox-workspace`.
