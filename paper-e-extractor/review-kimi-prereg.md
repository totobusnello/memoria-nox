kimi version 2.3.1
• I need respond in Portuguese likely. Should act skeptical independent verifier. Should read entire specified files (~48.5k chars) no cuts. Also cited files within repo allowed. Should verify hand arithmetic code semantics. Should inspect whole files via Read max enough. Should likely no edits, pure research no plan mode needed. I need be thorough. Should have citations line exact. I have tools. First perhaps TodoList multi-step because complex. I should read files full parallel. Should check sizes perhaps Read max_chars 500000 each enough. Five parallel calls. Could give short note. Then read.

• Vou ler os cinco artefatos integralmente e, depois, conferir separadamente a aritmética, o estimador, a execução e os casos de borda, usando apenas arquivos citados quando necessário.

• I have entire. Should inspect cited files relevant: paper3-construction/lme-run.py at current perhaps compare tag paper3-prereg-v1.3, lme-analyze.py, v13-manifest, e_batch, e-test, perhaps smoke data and README. User says no other files except cited within repo. All these cited yes. Should check code matches tag. User asks specifically same IC Paper3, blocks etc. Should read lme-run full perhaps huge. User said "Não há outros arquivos a considerar além destes, salvo os que eles citarem dentro do repo." So cited allowed. Should examine needed portions/full? User demands read entire specified only; other can portions as needed. Should likely read e_batch full, e-test full, lme-analyze, lme-run relevant sections, manifest counts perhaps use Python calculations. SMOKE calculations verify using data files? It cites runs/smoke..., e-smoke.py. Should have "Números ... batem entre si e com aritmética" Should recalc per call from token means prices. Power formulas exact using normal quantiles perhaps paired two-sided formula. Should identify issues.

  Initial observations:
  - PREREG line 4 says tag three files match (FROZEN e-run,e_prompts,e_batch) but PREREG itself not checked by runner, e-analyze not frozen checked. Text says tag on all files; runner refuses paid phases until tag and its three files match, accurate three files but pre-reg itself not byte-match. Perhaps out of scope question perhaps edge? Could mention low perhaps Q3 "teto" not freeze.
  - Power numbers: Standard approximate n = ((z.975+z.8)^2 * Var(I)) / δ², Var(I)=2σ²(1-ρ) = .456(1-ρ). z sum 2.8016 squared 7.8489. ρ0 var .456; factor 3.579? n = 3.579/δ² => δ .1 n357.9 yes; n for .15 159.1; .2 89.5. ρ.2 n286.3,127.2,71.6; ρ.4 n214.7,95.4,53.7. n242 detectable δ sqrt(3.579*(1-ρ)/242): rho0 .1216, .2 .1088, .4 .0940. Good. 10pp at rho about .35 or more: solve rho=1-.01*242/3.579=0.3238, not .35? I'll compute. For n242 detectable 10pp if 2σ²(1-rho)*(zsum)^2/n <= .01. 3.578? /242=.014785, so 1-rho <= .6763 => rho>=.3237. "about 0.35 or more" perhaps approximate conservative but inconsistent table? At rho 1/3 n238.6, so yes .324. They say about .35 perhaps coarse. Could be low arithmetic mismatch. Should calculate exact using possibly t distribution/cluster correction yields .326. Should examine original power script if cited? Smoke perhaps no script for power? e-smoke perhaps. Search files names. But can compute manually Python.

  - Cost per call:
  Pro default C0 535*1.25e-6 + (129+942)*10e-6 = .00066875+.01071=.01137875 ~.0114 yes
  C2 .001075+(186+1009)*.00001=.001075+.01195=.013025 ~.0130 yes
  P .00063125+(274+1034)*.00001=.00063125+.01308=.01371125 ~.0137.
  Pro budget128 C0 .00066875+(100+71)*1e-5=.00237875 .0024 yes
  C2 .001075+.00243=.003505 .0035
  P .00063125+.00331=.00394125 ~.0039
  flash lite P .0000505+202*.4e-6=.0000505+.0000808=.0001313 ~.00013
  flash C0 .0001605+137*2.5e-6=.0001605+.0003425=.000503 .00050
  C2 .000258+139*.0000025=.000258+.0003475=.0006055 .00061
  P .0001515+258*.0000025=.0001515+.000645=.0007965 .00080
  EST values match except F_C0 5.02e-4 vs .000503, C2 .000605 vs .0006055, P .000796 vs .0007965 yes. L_C0 .0001 and C2 .00013 from unknown token means (probably smoke set not table except P). Could be approximate.
  Projection pro default batch:
  per-call means across criteria sum .01137875+.013025+.01371125=.038115. *70067*.5 = 1335.25 yes. Budget sum .00237875+.003505+.00394125=.009825 *70067*.5=344.32 yes. For 100: .038115*31241*.5=595.30; 160 .038115*48399*.5=922.0. Budget 153.45,237.7. Flash three sum .000503+.0006055+.0007965=.001905 *70067=133.4776 standard, batch66.7388. P flash-lite .0001313*70067=9.1998. Reading smoke says about29 based 6 cells? PREREG 42 reading both judges all 1492 rows vs smoke 29 likely smoke projection originally 100/160/242 with three strong + perhaps 3 lite? Should examine. 242*6+40=1492. 29/1492=.01944 per row not .028 used e-run plan, which yields 41.776 =42. Smoke says 29 perhaps based 6? 242*? 104? Should find source e-smoke and read cost perhaps based prior Paper3 actual. PREREG explicitly estimate 42, code plan .028. Smoke second says 29 for reader/judges likely older estimate using only 1034? 6*242=1452 +40. At .02 ~29.84. Original table says 100 reader 12,160 19,242 29; roughly .12 per instance not per row. 100*6=600 rows*.02=12, 160*6=960*.02=19.2,242*6=1452*.02=29.04; positive control adds 40 perhaps omitted and .02 old. Code changed to .028 to 42. User asks numbers between pre-reg and smoke. This is likely discrepancy: Smoke says $29 vs pre-reg $42. Perhaps pre-reg includes positive control or updated estimate? It says reading and both judges $42. Smoke says $29 for reader and judges. Same all 242 context, though pre-reg all 7 cells incl L vs smoke? Original pro design perhaps three strong + P lite etc? Smoke is cost smoke before final design. Should flag medium or low? User asks include projections. Also total pre-reg $72 batch distillation vs smoke flash strong $67 + lite P $9 = $76. Pre-reg says about72, difference because seed L_C0,C2 and distinct counts actual vs smoke median. Should calculate plan actual distinct per counts 140134 needed includes all ext/crit combos. Strong 3*70067=210201, L P 70067 plus L C0+C2 140134? Wait total needed? Seed 140052 of 140134 needed (L C0/C2). Overall distinct distillations total perhaps 350? I'll understand needs set unique across cells ext/crit. For each 242 all blocks, six ext-crit combos (L C0,C2,P,F C0,C2,P). F_C2_pos uses same dkey blocks all sessions, no extra. If 70067 distinct blocks per all? Each ext crit count 70067, total 420402. Seed L C0/C2 140052 successes, 82 fail; remaining distill 280350? F three 210201 + L P 70067 +82 =280350. Batch cost F 133.48/2=66.74 + LP 9.20/2=4.60 + L failed small .005 =>71.34 ~72. Smoke second says strong batch67 + flash-lite P9 + reader29. It reports flash-lite P standard 9, but procedure batch would 4.6. Pre-reg distillation 72 =66.7+4.6+ retry .01 =71.3. So consistent if different pricing (smoke says flash-lite P standard, pre-reg all batch). Perhaps say pre-reg total estimate $114 vs smoke $105 if reading same? Approx 115 given user. 72+42=114. Code standard est before seed ~? L C0 70067*.0001=7.0067; L C2=9.10871; LP=9.178777; F C0=35.173? C2=42.39; P=55.77 => standard158.6 ~159, batch79.3 before seed. After seed standard cost remaining 142.7, batch71.35. reading 42. Good.

  - 140052 of 140134 = 2*70067 exactly. 82 missing. Percentage 82/140134 =0.058514%; rounded 0.06 yes. Smoke 87/155506 =0.055946% yes. Difference five nonconfirm or other. 140052+82=140134. 1492 =242*6+40 yes.
  - Cell needs: F_C2_pos only control read yes, but distillation all blocks full F_C2 reused so positive doesn't trigger extra distills. It removes evidence sessions via lme.evidence(r), likely answer sessions. Should verify lme.evidence exact. "sem as sessões de resposta" yes.
  - `needs` iterates set(CELLS.values()) so all six combos full blocks for all 242. Good.
  - Parser issues:
    - bool is subclass of int in Python. `isinstance(True,(int,float))` true, `(True or 0)>=.5` true. So boolean importance accepted as 1/0 though text says units whose importance is not a number dropped. JSON booleans not numbers semantically. Paper3 may same behavior. Differential between extractors possible if one outputs true. Should severity low/medium.
    - NaN/Infinity accepted by Python json.loads (non-standard JSON) and float numeric; NaN >=.5 false dropped, Infinity accepted. responseMimeType JSON likely standard. Text says parsed as JSON, Python accepts NaN Infinity extension. Could note low edge.
    - Dict `mem = j.get("memories") or []`: if memories is 0, "", None, False gets converted to [] and returns ok True rather than failed; text says object its memories list used, anything else failed. Also missing memories key returns [], True. Empty object valid success; wrong types falsy success, truthy wrong type failure. Paper 3 likely same? Should inspect. This affects failure counts and missing served empty anyway. Material not different between extractors? Empty same material; only failure accounting differs.
    - List entries non-dict are silently dropped and parse ok. "Anything else is a failed block" could imply mixed list should fail? It says units nonnumber dropped, perhaps non-dict not specified. Doesn't cause differential unless models shape differs.
    - Importance numeric strings dropped as stated.
    - text missing/non-string accepted (m.get("text","") could dict/None) then lme.serve may fail or produce odd. Should inspect lme.serve expects dict text etc. Could be important.
    - Max 10 items not enforced parser; prompt only. Text says output contract at most 10, not parser enforcement. Paper3 likely same.
    - Response text extraction joins all parts. If candidate absent or blocked, txt empty parse fails. okay.
    - top-level list accepted new parser for all models. Reused Paper3 cached values for successes only; new L P and F all parser same. Failed L C0/C2 redistilled. But potential differential material: seed copies Paper3 values with units already filtered, parser now top-level accepted only on 82. Same block content and prompts. Cache keys model/gen/prompt/block. Good.
    - Critical: cache key does not include parser version. Seed uses new dkey but copies values. If rerun with parser changes after tag? e_prompts frozen. fine.
    - Critical batch resume: `ingest` processes arbitrary `lines`, duplicates keys possible. `got` increments per line, cache overwritten. missing = len(meta)-got-bad could negative. Batch API output one per request presumably unique. More serious: `ch` state done after ingest even if errors/missing; todo on restart recomputed from cache so missing no cache get retried. If errors no response not cached => retry. Parse failures cached, not retried by sync. Procedure says sync "for whatever batches did not return (errors, missing lines, expired chunks)" parse response did return so okay.

    - Batch chunks manifest written once from current todo. If seed occurs after make_chunks? Procedure seed first. On restart after partial sync? Suppose initial batch chunks created from todo. Sync later fills some. Restart distill batch loads old chunks, only submitted/new states; chunks done not reingest. Fine.
    - Crash consistency serious: batch state submitted is saved only after create. If process dies after `create` before save, on restart `make_chunks` loads batches.json with ch new, list display names adopts existing. Good. But if process dies after upload before create, stray uploaded file but new create okay.
    - More serious: if process dies during `ingest` after caching some and spending before `ch["state"]="done"` save, restart sees submitted, downloads and ingests all lines again, double-counts spend but same response deterministic cached. No material difference between extractors? Double cost only. Cap perhaps.
    - If process dies after state done save but cache puts committed? lme Cache.put commit behavior need inspect. Probably commits each.
    - `make_chunks` writes chunks files and state once. If process dies partway writing initial batches.json? write_text non-atomic. Could corrupt resume, but general.
    - Display name adoption doesn't verify model, request count/content. If same out dir and same prefix fixed design frozen; potential stale chunks from different data? manifest hash same, prompts frozen. Not cross extractors unless collision existing display name externally. Could be edge low.
    - `distill_batch`: `existing=e_batch.list_display_names()` inside each chunk; adopts by display name regardless of actual state. Then poll get. okay.
    - Batch terminal bad chunks marked bad and never open; sync todo picks cache missing. okay.
    - Cap: `Spend` Ledger likely stops at cap? Should inspect lme.Ledger. `distill_sync` launches ThreadPoolExecutor.map all todo; ledger add raises when cost > cap after calls, but cannot prevent overshoot from concurrent in-flight; text says stops a process at cap not guarantee never exceeds? "teto cumulative ... stops a process at cap". Pre-check only batch estimates; sync no pre-call estimate so actual may overshoot by concurrent calls and the raising call. Read similar. Could be high if hard cap US$160 claimed. Should inspect Ledger implementation. If `lme.Ledger.add` raises before adding? I'll read. Also Spend prior summing process files could double count due filename collisions? PID/time unique enough. Spend.save rounds per process to 6 decimals. Fine.
    - Batch cost cap estimate: check `sp.led.usd + est_inflight + ch.est_usd > cap`; sp.led.usd includes actual costs ingested, estimates for all submitted even done? inflight computed at start while, appended. Done chunks remain in local inflight until next while; when submitting new in same for before poll, okay all submitted. Next loop fresh. Actual batch spend incurred when ingest; held estimate reserved. Good.
    - But if adopted already completed batch, est_inflight counts until ingest. okay.
    - `batch-test` cap $1 but est chunks perhaps >$1 and held; okay.
    - read cap no per-job estimate, Ledger raises in thread, `ex.map` may continue scheduling all jobs (ThreadPoolExecutor map eagerly collects all iterables, submits all jobs before outputs). Other threads may continue calls even after one raises, since context manager waits for all. If Ledger.add raises on each after cap, but API calls already made before add, could overshoot significantly. Text "stops a process at cap" questionable. Could mention high cap not strict. User Q3 asks teto correspond text. Should be exact.

    - Freeze check: paid `distill` and `read` only, but batch-test spends pre-tag allowed. Cap across processes per out directory. A new out dir resets cumulative, so not global across design. Text "US$160 cumulative across processes" likely per run out implied. If use different out no. not issue.
    - Batch chunks cap estimates based EST and standard means. If actual > estimates, can exceed cap before Ledger catches; same concerns.

  - Critical row completeness/analysis:
    - Read fails if any missing cache references. Parse failures are cached with units empty so all rows exist. 1492 yes.
    - No outcome read until all 1492 rows exist: Code read builds jobs and runs all then writes at end. If process fails mid-read, cache answers/judges exist but no rows. Restart uses cached outcomes, no new row outcome-based selection. Fine. Text says analysis does not run until all rows exist; e-analyze itself does not enforce 1492, it happily analyzes partial rows. Procedure external not code. If user runs analysis prematurely it can. Pre-reg procedure says not to. Perhaps low.
    - `e-analyze` secondary docstring omits F_C2-F_C0 but code includes matches pre-reg. fine.
    - controls positive `pos = sorted(Y["j1"]["F_C2_pos"])` not restricted to prim nor exactly manifest control; rows determines. read exactly40. If incomplete main instances, positive can include 40 even excluded main, as pre-reg says 40 controls independent. Fine.
    - cell describe abstention/chars uses all rows not `ids`, so if missing main cells, acc computed prim but abstain/median includes incomplete qids; slight internal denominator inconsistency. Not asked main.
    - Cluster CI same Paper3? Should inspect exact `clusters`, `cluster_mean_ci`. It imports current working tree file, not tag byte-for-byte, and runner frozen check excludes lme files/e-analyze. Text says imported at tag but e_prompts import current lme. `frozen_check` doesn't verify paper3 files against `paper3-prereg-v1.3`, just manifest hash. If current lme changed, paid run not blocked. However repository may currently at tag? Should git status/log/tags and compare. This could be significant: artifact claims unchanged imported from tag but actually imports mutable current file. The question focus code does what text says. Should flag perhaps high for reproducibility/freeze. But user asks four questions specific; can include in Q2 IC same? Should compare actual tag. I can use git show no modifications. I should read cited lme-analyze and lme-run. Could compare to tag. Should check existence. Also pre-reg tag not yet exists draft. Paper3 tag likely exists. I can run git status, tag etc read-only. No need external web prices? User says only repo files; don't web. Use stated prices arithmetic.

  - Primary exact sign correct: F strong minus L weak, C2-C0. Negative shrink. Yes. IC uses same functions current. Should examine whether Paper3 primary criterion contrast used `contrast_paired` etc same cluster_mean_ci. Read lme-analyze relevant. Use Grep to locate definitions and primary contrast. Also lme-run definitions. Parallel.

• A primeira leitura confirma o contraste com o sinal pré-registrado. Agora vou checar as funções importadas do Paper 3 e os arquivos de lote/teste citados, porque é neles que estão o IC exato, o filtro de evidências e o comportamento real do teto.

?? paper-e-extractor/review-codex-prereg.md
paper3-prereg-v1.3
• No diff stat means current matches tag for those. There is untracked review-codex-prereg.md not cited? Do not read, independent family etc. Avoid. Should inspect full relevant lme functions and Paper3 analysis usage. Grep more targeted primary criterion cluster_mean_ci call.I can read smoke result JSON and perhaps compute exact averages/cost totals, 280 calls, etc. Should dataset exists. I can run e-run plan (no spend) to get actual counts. It may import and assert, reads data. Standard. Also run tests offline standard, allowed. Should user wants verifier, testing useful. But first calculations. Use Python script in Bash inline to calculate costs power and perhaps parse NDJSON summaries. Dedicated tools for file reads but computations via Python okay. Avoid shell cat/grep. I can read smoke JSON in parallel plus batch test and manifest perhaps full manageable. v13 manifest likely small. Read.242 instances, 1492 rows; distinct distillations:
  gemini-2.5-flash       C0   70,067
  gemini-2.5-flash       C2   70,067
  gemini-2.5-flash       P    70,067
  gemini-2.5-flash-lite  C0   70,067
  gemini-2.5-flash-lite  C2   70,067
  gemini-2.5-flash-lite  P    70,067
  ~US$ 159 standard, ~US$ 79 batch, before the Paper 3 seed; reading ~US$ 42
z sum 2.801585218112968 squared 7.848879734349086
rho 0 n(.10) 357.90891588631825 n(.15) 159.07062928280814 n(.20) 89.47722897157956 MDE n242 0.12161260059468174
rho 0.2 n(.10) 286.32713270905464 n(.15) 127.25650342624652 n(.20) 71.58178317726366 MDE n242 0.10877361674009589
rho 0.4 n(.10) 214.74534953179094 n(.15) 95.44237756968488 n(.20) 53.686337382947734 MDE n242 0.09420071535843531
rho needed for 10pp at n=242 0.3238503170542254
pro C0 0.01137875
pro C2 0.013025
pro P 0.013711250000000001
pro C0b 0.0023787500000000002
pro C2b 0.0035050000000000003
pro Pb 0.00394125
lite P 0.0001313
flash C0 0.000503
flash C2 0.0006055
flash P 0.0007965000000000001
projection 100 31241 595.3753575 153.4714125
projection 160 48399 922.3639424999999 237.7600875
projection 242 70067 1335.3018524999998 344.2041375
flash std,batch 133.477635 66.7388175 liteP std,batch 9.1997971 4.59989855 batch dist total 71.33871605
rows 1492 seed total 140134 failure pct 0.05851542095422953 smoke failure pct 0.055946394351343354
reader at .028 41.776
Good. Should note exact smoke mean cost from JSON differs table rounding due rounded token means. E.g pro C0 exact .011376 vs rounded mean formula .01137875 table .0114 same. Pro C2 .013023 vs .013025. All okay. Flash C0 .000502 vs formula .000503 table .00050, EST .000502 exact. Flash C2 .000605, P .000796. Good.

  Power n table rounded nearest integer not ceiling? n .15 rho0 159.07 ->159 but required n ceiling should 160. .2 rho0 89.477 ->90 ceiling yes. .1 rho0 357.909 ->358 ceiling yes. rho.2 286.327 ->287 ceiling, .15 127.256 ->128 ceiling, .2 71.582 ->72. rho.4 214.745 ->215,95.442 ->96,53.686 ->54. Only 159.07 listed159 instead of160. User used normal approximation round nearest not strict "needs" ceiling. Detectable n242 okay. "10 pp only if rho about .35 or more" actual .324, .35 approximate maybe not serious. Could flag low combined power threshold rounding. User specifically includes n necessary and MDE. I'll articulate. User may expect detection of mismatch. Perhaps pre-reg author intentionally rounded .35 to be conservative. Skeptical should note exact .324. Severity low.

  Should verify variance .228 from Paper3 actual rows. The user explicitly asks "cálculo de poder (variância 0,228, n necessário..." User wants verify variance 0.228 perhaps compute from cited Paper3 confirm results. Should locate confirm cache/rows paths. Pre-reg cites 242 rows known. `CONFIRM-RESULT.md` cited e-analyze. Read it perhaps stats. User allows cited. Could read. Also Paper3 rows external path P3_CACHE points home logs. I may read file not secret. Should find `paper3-construction/CONFIRM-RESULT.md` likely. Read full.prompts and parser
  ok   C2 is byte-identical to Paper 3's
  ok   P keeps C0's output contract
  ok   P drops C0's category list
  ok   object form: kept >= 0.5 only
  ok   top-level list accepted
  ok   bare [] is a parsed empty block
  ok   invalid JSON is a failed block
  ok   empty text is a failed block
  ok   non-numeric importance dropped, block parsed
request bodies and cache keys
  ok   L body equals Paper 3's distill body
  ok   F body differs only by thinkingBudget 0
  ok   six distinct keys per block
seed from Paper 3
seeded 1 flash-lite C0/C2 distillations from Paper 3; 1 left to distill
  ok   copies a good flash-lite distillation
  ok   leaves a Paper 3 failure to distill again
  ok   never seeds P or the flash extractor
batch path
  ok   20 requests to do
  t-F-000: submitted as batches/b1 (4 requests)
  t-F-001: submitted as batches/b2 (4 requests)
  ok   chunks by extractor, 4 per chunk
  ok   at most max_inflight submitted on the first pass
  ok   nothing ingested while running
  t-F-000: done, 2 ingested, 1 errors, 1 missing · US$ 0.00
  t-F-001: done, 4 ingested, 0 errors, 0 missing · US$ 0.00
  t-F-002: submitted as batches/b3 (2 requests)
  t-L-000: submitted as batches/b4 (4 requests)
  t-F-002: done, 2 ingested, 0 errors, 0 missing · US$ 0.00
  t-L-000: done, 3 ingested, 0 errors, 1 missing · US$ 0.00
  t-L-001: submitted as batches/b5 (4 requests)
  t-L-002: submitted as batches/b6 (2 requests)
  t-L-001: done, 3 ingested, 0 errors, 1 missing · US$ 0.00
  t-L-002: done, 2 ingested, 0 errors, 0 missing · US$ 0.00
  ok   every chunk done
  ok   each chunk created exactly once
  ok   error and missing lines stay to do
  ok   list-form answers parsed
  ok   object-form answers parsed, low importance dropped
  ok   batch spend at half the list price
  ok   a rerun submits nothing
  t-F-000: submitted as batches/b1 (4 requests)
  t-F-000: done, 2 ingested, 1 errors, 1 missing · US$ 0.00
  ok   duplicate guard adopts the batch by display name
  sync: 4 ok, 0 errors · US$ 0.00
  ok   sync clears the residue
cap
  c-F-000: held, would pass the cap (spent US$ 0.00, in flight ~US$ 0.00, this ~US$ 0.00)
  nothing in flight and the next chunk would pass the cap; stopping
  ok   a chunk past the cap is held, not submitted
  ok   spend is cumulative across processes
  ok   second process on the same out dir refused
freeze
  ok   distill/read refuse before the tag exists
read phase
  ok   read refuses with distillations missing
  r-F-000: submitted as batches/b1 (27 requests)
  r-L-000: submitted as batches/b2 (27 requests)
  r-F-000: done, 25 ingested, 0 errors, 2 missing · US$ 0.01
  r-L-000: done, 25 ingested, 1 errors, 1 missing · US$ 0.01
  sync: 4 ok, 0 errors · US$ 0.01
  read 19/19 · US$ 0.01 · 0s
{"rows": 19, "distill_by_source": {"paper3": 0, "batch": 50, "sync": 4}, "distill_failed": 0, "spend_usd_cumulative": 0.0102}
  ok   6 cells per instance plus the positive control
  ok   positive control only on control_subsample
  ok   positive control holds no answer session
  ok   every full-window cell answers (fake extractor keeps the code)
  ok   extractor recorded per row
  ok   receipt counts the distillations by source
analysis
  ok   interaction estimate exact
  ok   clusters from shared answer sessions
  ok   controls pass on designed cells
  ok   verdict: shrinks
  ok   failed positive control blocks interpretation
  ok   instance missing a cell is left out and named
  ok   analysis is deterministic

ALL PASS
e568a2d0cd7e79e9ce050b364df96fd3559b63c8
5917661d3b10987df69e44db3a2a5867e4b4f90a
b4b1f0e763cd913a646a8030e67cb5b25bb9d0bb
I accidentally Grep broad 87 yielded huge but truncated okay. Should compute variance from rows. `paper3-construction/runs/confirm-2026-11-04/rows.ndjson` cited via result. I can use Python to compute. Should inspect row schema perhaps Read first 2 lines huge but okay. Or Python counts directly. Data cited. Use computation. I can calculate mean, sample variance ddof1 vs population. Smoke .228 probably sample. Use Python. Also verify L_C0/C2 needed seed counts from actual P3 cache and new needs. I can run seed? That writes cache, not desired perhaps plan enough. Use read-only script imports e-run and computes need, connects P3 cache read-only and count good/fail/missing. Should be cautious P3_CACHE path outside working dir explicitly in artifact and user authorizes cited. Bash can read DB outside working directory? Instructions say avoid using `..`; absolute path from code okay read. Not secret. Could run Python sqlite read-only. No modifications. This verifies 140052. Also check existing cache P3 successful row values shape. Should have no need. Do it.

  Potential major issue: reused cache keys do not include extractor model? Paper3 key h("distill",crit,prompt,block), model default GMODEL flash-lite. New dkey includes model and gen. Seed correct. Reader/judge caches same keys and new out cache empty except distill so all new. If user points out dir to Paper3 cache? out new expected. Could reuse answers if same out had previous Paper E runs; every cell read first run. Resume uses cached answer/judges. okay.

  Important cross-extractor material differential due cache collision: dkey includes model alias (`gemini-2.5-flash`) not actual `modelVersion`. Fine.

  Parser differential: Old Paper3 parser didn't type-check numeric and could throw TypeError for string importance; exceptions catch whole distill and serve empty. New parser drops nonnumeric, so on seed only successful old cached blocks, failed re-run. As claimed max82 changed. For all other blocks same filters except bool. New P etc same. Fine.

  Batch resume serious differential via cache overwritten by duplicate output lines with different responses? Batch API keys unique. Not likely.

  `make_chunks` restart behavior with cache and chunks: If run `distill --via batch` initially without `--wait`, creates chunks for all todo and submits up to max. Later run `distill --via sync` while submitted batches pending (procedure says --wait, so no). Sync fills all including inflight, then later batch ingestion overwrites sync material with batch responses for same requests. Both same model/prompt/block but stochastic temperature .1 so material can change depending resume order. Text allows restart, could serve different material than previous read if reads in between? Procedure read after sync and batch wait. If no wait contrary procedure. Not within prereg.

  More subtle and within procedure: rerun `distill --via batch --wait` after a chunk state `done` but some missing/errors. `todo_of` includes missing but `make_chunks` returns existing batches.json, so it will not create chunks for those residuals. Then `open_` none -> returns left residuals. Procedure then sync handles. okay.
  After sync pass, failures due network are not cached, so `read` refuses due missing. Pre-reg failures says block that fails after sync served empty and reports count. Code `distill_sync` catches exception and returns error without `cache.put`; `read` then `build_jobs` missing -> sys.exit. This is a clear mismatch, likely high. Text §8 Failures: "A block that fails to distill after the sync pass is served empty, and result reports count..." But code only parse failures cached empty; network/sync exceptions left uncached and block read. There is no mechanism to convert residual sync failures to cached failed empty. So a single persistent sync network failure prevents all reading rather than serving empty. That's Q3/Q4 high or medium. It doesn't serve different material between extractors but execution doesn't correspond text. Q3 cells/teto perhaps include failure handling. Q4 resume can serve material different? Another issue parse failure cached and served empty as text. Network failure not.

  Also cap on sync errors: failed calls no cost recorded if HTTP error after retries (API may charge? likely no). okay.

  Another critical mismatch: failure threshold "If more than1% blocks any extractor×criterion fail result says so beside primary." `receipt` only global `distill_failed`, not per extractor/criterion, `e-analyze` only rows no distill failure info. So no count per extractor/criterion in result and no flag beside primary. Code receipt aggregate by source and total failed. The text explicitly says count per extractor and criterion and threshold beside primary; not implemented. Q3 or Q4 high/medium. I'll mention. User didn't explicitly ask failure reporting except parser/resume, but overall code text. Good skeptical finding. Could be medium since no effect on estimate except transparent instrument failure. Distill parse failures served empty but analysis doesn't report. `receipt` has dist list with entries but only total; can compute externally but frozen analysis doesn't. "result reports" could receipt counts global insufficient. Clear.

  `response_value` sync only caches after successful POST even parse failed. Network errors not cached. yes.

  Another serious mismatch: F_C2_pos no answer sessions but uses all cached units including evidence, then serve only non-evidence. Correct.
  `evidence_kept` uses len(ev & set(sess)) always 0 pos, len(ev) full. Good.

  Full window all sessions includes empty session blocks; serve nothing for empties. Fine.

  Cache seed values already units filtered, via paper3. When build jobs v could failed with units empty. good.

  `needs` set uses unique block content. If identical block appears in both evidence and non evidence, same distillation. expected.

  Rows count `len(man["confirm"])*6+len(control_subsample)`. If control not subset confirm could still build only confirm controls and count mismatch, manifest subset verified 40. Good.

  Cost cap actual:
  - `Ledger.add` raises SystemExit inside worker thread. In `concurrent.futures`, SystemExit is captured like BaseException? Future captures BaseException, yes. `ex.map` iteration raises. Context manager exit waits all. Other queued tasks continue; each does API then add raises. Because API call caches only after `led.add`, when add raises no cache. So overspend and no cached results for over cap. Could be high financial guard mismatch. Batch cap estimate prevents submissions but ingest can raise; multiple chunks etc. "stops a process at cap" technically raises after crossing but doesn't guarantee <=160. Cap named cap suggests hard. Pre-reg says "Cap: US$160 cumulative ... runner holds batch chunk whose estimate would pass cap and stops a process at cap." It does stop (eventually) at cap but above. User might accept overshoot minimal, but 8 workers default and read jobs each 3 calls so max 24 calls beyond plus all queued due SystemExit in each but calls still made. Actually after first SystemExit from `ex.map`, main exits with stack, context manager `__exit__` calls shutdown(wait=True), all 1492 jobs already submitted by ex.map, so every job will run and call APIs despite cap, each Ledger.add raises at first over-cap answer, so for each remaining job `lme.answer`: API call, led.add raises before judge, so no judges for remaining. Up to 1492 extra reader calls could happen after cap, not just 8! I'll examine `ThreadPoolExecutor.map`: in Python version, map submits all fs immediately. Yes. When one future result raises, map iteration exits, with executor shutdown wait true; pending futures are not cancelled. All jobs each attempts answer; cache may hit for duplicate material/question? mostly unique. Each over cap API answer then add raises; no judges. Could massively blow cap on read. In `distill_sync`, `res=list(ex.map(one,todo))`: list consumes until SystemExit thrown, exits and shutdown waits all; all todos submitted, each does POST then `sp.led.add` raises. So all residual sync distillation calls could be made, massively over cap. This is high. Note base Ledger raises on any add after cap so all calls made but no cost saved? `Spend.add` finally increments k and perhaps saves. Each led.usd updated before raise, so recorded. Ultimately atexit saves actual estimated spend. Still cap not hard. Batch submission cap safer but actual ingest can raise and abort processing.

  Perhaps test with fakes to verify overshoot, but no need code logic enough. Could write ephemeral Python to simulate small cap and count calls using e-test fakes? Tests existing don't cover sync cap. I can create no files script import e-run and monkeypatch lme.post counts, use temp. But response_value etc. Could verify all tasks called after cap. Useful evidence. Not alter repo. I can run minimal. But the line references in response enough. Perhaps need see Python SystemExit behavior. Test.

  Other potential high issue: Batch response `response_value` assumes `ln["response"]` is GenerateContentResponse. Gemini Batch API JSONL format might response body nested? e_batch fake matches. Real batch test passed 60, so okay.

  Power and sample clustering: Power calculation ignores cluster robust design (G241 ~ n so negligible) and CR1. It uses independent per-instance paired normal formula. With 241 clusters, negligible. But primary interaction variance depends both differences and correlation; assumption stated. Good. However using variance .228 of binary difference d. The variance for difference values -1,0,1, mean .248, sample variance maybe .228. Interaction I = dF-dL variance formula 2σ²(1-ρ) yes. n calculation normal. Fine.
  Power detectable effect at n242 derived normal approximate. Good.
  But actual paired data re-reading same 242 creates outcomes not independent due same reader/judge caching? Cache keys answer material question. Different cells with identical material could hit same answer cache (e.g C0/C2 both no units, same question), inducing correlation naturally. Judge caches same. Fine.
  No new instances, inference E over what? They define expectation over 242 sample, reused. Not asked.

  Should verify variance.

• As projeções principais fecham: US$ 133,48/66,74 para flash e US$ 71,34 de destilação em lote após incluir P no flash-lite. Há, porém, duas divergências operacionais relevantes no runner — o teto não impede chamadas já enfileiradas e falhas de rede na passagem síncrona impedem a leitura, em vez de virarem bloco vazio. Vou terminar de checar a variância observada e os caminhos de retomada.

Traceback (most recent call last):
  File "<stdin>", line 13, in <module>
KeyError: '10'
need L C0/C2 140134 good 140052 failed 15 absent 67 by {('C0', 'good'): 70025, ('C2', 'good'): 70027, ('C0', 'absent'): 32, ('C2', 'absent'): 35, ('C0', 'failed'): 10, ('C2', 'failed'): 5}
controls 40 controls outside confirm set()
raised SystemExit CAP REACHED: US$ 0.00 > 0.001
API calls with cap .001 and 12 jobs, workers=1: 2 recorded spend 0.0056
{"memories":null} => ([], True)
{"memories":false} => ([], True)
{} => ([], True)
[{"text":"bool true","importance":true}] => ([{'text': 'bool true', 'category': None, 'importance': True}], True)
[{"text":"bool false","importance":false}] => ([], True)
[{"text":"infinite","importance":Infinity}] => ([{'text': 'infinite', 'category': None, 'importance': inf}], True)
• Variance script error due qid variants perhaps rows `variant` vs qid? Should inspect first line. Read n_lines 2.Why KeyError 10? I used ids intersection across d.values() where each q dict keys cells, intersection gives '10','11', not qids. Should simply ids with both. Fix. Cap probe workers1 only 2 calls because list map in main thread? Why not all12? With workers1 map submits all, first call cost .0028 raises in future, then second already runs during? Executor shutdown perhaps pending futures canceled? In Python map list consumes first future immediately after submit all. First future raises, with shutdown wait true, worker had started second; after second raises, remaining futures? SystemExit in worker thread? Future captures SystemExit yes, worker continues. Why 2 only? Spend.add wrapper finally calls self.save every? cap exceeded triggers save; perhaps `SystemExit` from worker? concurrent futures worker catches BaseException. Should process rest all. But main thread might SystemExit not captured? ex.map returns futures; list iter first raises, `with` shutdown calls wait. Pending should continue. Yet only2 perhaps `Spend.save` at atexit? Not. Wait `ThreadPoolExecutor` in Python 3.14? `shutdown` doesn't cancel. Why only2? Could be `SystemExit` in Future is special: Future.set_exception? It captures. Worker work_item.run catches BaseException. Should continue. Perhaps `Spend.add` wrapper base SystemExit finally self.save and after k>cap saves, no effect. Could be interpreter environment Python 3.13 `Executor.map` lazy buffers? In 3.14 map buffersize? Default still submits all. Should inspect Python version. Not necessary. At least 2 calls, spend .0056 > .001 by 5.6x even one worker. Demonstrates overshoot. With 8 perhaps up to9 calls not all due SystemExit in worker triggers? Actually main future result first raises, main SystemExit propagates and atexit perhaps kills? with shutdown wait only running? Python 3.9 perhaps. Fine.

  Should have no claim all enqueued necessarily run; phrase cap is post hoc and can overshoot by in-flight/queued calls, probe one worker two calls. Avoid overstating all 1492. Could still many with 8.

  Power exact variance.j1 n 273 mean 0.23443223443223443 sample variance 0.2316041801335919 population variance 0.23075581317339558 counts {-1: 7, 0: 195, 1: 71}
j2 n 273 mean 0.2600732600732601 sample variance 0.23726028873087696 population variance 0.23639120342417047 counts {-1: 6, 0: 190, 1: 77}
  sync: 0 ok, 1 errors · US$ 0.00
cache after sync exception: None todo remaining: 1
pro smoke records 280 errors 0 sum usd 1.9226940000000001
flash smoke records 120 errors 0 sum usd 0.0761319 object form 120
Oops n273 includes 31 counterfactual variants same qid overwritten? Rows 1654 includes 242*6=1452 +40pos+40neg+242lenmatch=1774? Wait actual 1654: primary 4*242=968, dose 120, controls 80, lenmatch 242, counterfactual 31*6? 186 -> total159? I'll compute: 968+120+80+242=1410, plus 244? Hmm. Counterfactual variants qid same original but variant altered; rows cell 10/11 duplicated per qid causing dict overwrite arbitrary order, n242 unique but my `ids` shows273? That implies qid perhaps variants unique? First variant same. Why 273? Manifest confirm242 + counterfactual31 =273, some counterfactual qids not in confirm? Actually counterfactual variants from spent stage1 not confirm and run extra. Should restrict manifest confirm. I need load manifest set. Do.j1 n 242 mean 0.24793388429752067 sample variance 0.2287301532869243 population variance 0.22778498736425107 counts {-1: 5, 0: 172, 1: 65}
j2 n 242 mean 0.2727272727272727 sample variance 0.24066390041493776 population variance 0.2396694214876033 counts {-1: 5, 0: 166, 1: 71}
Variance .228: population .227785 rounds .228, sample .228730 rounds .229. They used population variance np.var default. Mean .248. Good. Power formula uses .228 exactly. If sample variance, MDE slightly different negligible. Should state population variance matches. Important to mention variance is population (ddof=0), not sample. No issue.

  Should examine same IC exact formula. Done. Could mark Q2 no serious findings except freeze imported current? Current matches tag verified. Primary correct. Potential issue: `P3_CRITERION` unused. Pre-reg says L_C2-L_C0 beside +24.8; code label uses hardcoded +24.8 in name, okay constant unused no impact.
  Alpha .05 z normal same.
  Complete-case prim based j1 only; Y j2 same rows so fine.
  Rows duplicate qid/cell overwritten silently. read produces unique. Fine.
  CI CR1 correction only G/(G-1), no n/(n-1) typical CR1? They call CR1 but Stata CR1 often G/(G-1)*(n-1)/(n-k). Paper3 same. They explicitly same Paper3. No issue.
  Sign hi/lo correct.
  G computed set(cl.values) can differ `G` returned from cluster mean if some clusters sums zero? g defaultdict only adds each q so all cluster keys created even zeros. same.
  No major Q2. Could mention low: e-analyze imports mutable lme-analyze rather than verifies tag, but current matches. The pre-reg freeze procedure tag all files at commit, but future modifications after tag to lme-analyze not caught by e-analyze. User asks artifact pre-freeze, this is relevant. `e-analyze.py` frozen by tag but external code not. Same for e-run's frozen_check. Could classify medium in Q2/Q3: claim "unchanged imported at tag" isn't enforced, although at review time matches. However `git` tag `paper-e-prereg-v1.0` on commit holding current Paper3 files ensures at freeze they match whatever; subsequent working tree changes could alter. Runner only checks three E files, so paid phases can run with modified Paper3 instrument. e-analyze no frozen_check at all, so post-tag modifications to E analysis itself can run and write analysis; `--check` reproduces current modified code, not tag. Pre-reg says e-analyze as frozen at tag no other confirmatory, procedural honor not enforcement. Text only explicitly runner refuses until its three files match, so not claiming e-analyze guard. §3.1 says imported from lme-run at tag, which fact at current review yes. It doesn't promise ongoing guard. I can put in limits or low, not central.

  Should scrutinize e_prompts exact P sha etc. I can run __main__ prints. Already smoke JSON hashes. C0 assert? Only C2 assert. Pre-reg C0 byte for byte and hash matches current smoke. Could compute actual. Done smoke result. C0 no assert but current. No issue.

  Parser differences potentially serious due response shapes:
  - The new parser accepts a top-level JSON list of *anything*, filters non-dict. Fine.
  - New parser considers dict with `"memories": "not a list"` false, but with null true. Text says anything else failed. Low reporting.
  - Numeric bool accepted. Could serve `"true"` units if model emits importance true. Gemini responseMimeType only MIME no schema, so possible. Difference between extractors? Same parser across newly distilled F/L, so no asymmetric code path by model. Only model output shapes differ naturally. Question specifically "Algum caso de borda do parser ou da retomada do lote pode servir material diferente entre os extratores sem o texto declarar?" User wants find perhaps yes: seed uses old parser, new parser on 82 declared. Parser booleans etc applies same across extractors, doesn't itself cause different material between extractors unless output differs. Not a hidden asymmetric path. But perhaps there is a real batch resume issue that does:
  `make_chunks` groups todo by extractor. `cid=f"{prefix}-{e}-{i//CHUNK:03d}"`. On initial run after seed, L todo has L_P all70,067 +82 failed C0/C2. Sorted todo tuples `(dkey,e,c,b)` then groups preserves sorted by hash key, random criteria interleaved. chunks L size20k. F all210201. Fine.
  If process dies before recording created chunk, adoption by display name. On restart `make_chunks` returns batches state new. Good.
  But crash after `make_chunks` initial writes `batches.json`, before any submission, then seed? Not procedure.
  When chunk terminal bad marked "bad"; on future batch call, `make_chunks` loads existing, ignores bad. Sync picks. good.
  When errors/missing lines in done chunk, sync picks. good.
  When batch returns response line with `response` empty dict `{}` treated error, no cache. okay.
  When response candidate contains multiple parts, join. same sync.
  Cost batch `usageMetadata` may absent => cost0 but material same.
  The batch and sync paths use same request_body and response_value, so parser same. Key mapping metadata maps key->ext/crit. Good.
  Potential key issue with batch API: Keys are dkey hash; meta maps to ext/crit, so even if response line key from another chunk but same key in current meta no. fine.
  The batch API may return `response` as string? Real test works.
  No serious resume material difference within prescribed procedure. Could respond no serious Q4, but note low parser contract deviations and sync failure mismatch Q3. User specifically says if nothing serious say. I can say no hidden model-dependent resume path found; only low parser edges. Should ensure no unexpected serious.
  One subtle difference: seed reuses Paper3 distillations where `failed` false. Paper3 `failed` is `not txt`, so JSON parse failures raised except -> `failed` true and not cached! Wait Paper3 distill:
  ```
  try:
   d=post
   txt=...
   mem=(json.loads(txt).get("memories") or []) if txt else []
   units=...
   v={"units":..., "failed":not txt}
  except Exception as e:
   v={"units":[],"failed":True,...}
  led.add...
  if not v.get("error"): cache.put
  ```
  If top-level list, `.get` AttributeError -> except failed error, not cached. If invalid JSON same. If object memories wrong type maybe TypeError -> not cached. Failed network not cached. Receipt `failed_blocks` counts need v None or failed? 87 includes absent67+failed15+? total82 in E subset. Seed skips both absent/failed. Re-distill 82. Good.

  Paper3 successful cache with bool importance uses comparison true>=.5 works same. String numeric old raises, absent then rerun new drops. declared under82.
  Old parser accepts dict `"memories": null` as[] success failed false, cached. New would true also. same material.
  Old parser accepts NaN? comparison nan>=.5 false. same. Infinity same. bool same. So not differential seed except82.

  But new parser filters nonnumeric whereas old successful cached values could include odd custom numeric? JSON only int/float/bool. Same.
  New parser top-level list accepted all F/L fresh. Good.

  Batch resume adoption by display name can adopt batch-test? Prefix differs. Existing chunk names same out. No cross.
  Potential API list pagination duplicate names returns last arbitrary; if duplicates from prior double-create due crash window? Guard designed prevent duplicates but two processes prevented lock; if process dies after create before recording, only one. External same name could duplicate. Not serious.
  Cache dkey includes JSON gen sorted with separators default including spaces; deterministic. Prompt/block unicode. Same in request. good.
  Serving units importance descending recency. sort tuple includes b,pos but not i after pos? tuple (-imp,rank,b,pos,i,u). rank unique session order, so no compare dict. If same importance nan? nan filtered. infinity okay. text dict converted f-string not error. So malformed text served as Python repr, could differ model outputs but same parser.
  Numeric importance bool is accepted and serve -(True or0) -1. okay.

  Cells "F_C2_pos only40 without response sessions": needs distills F_C2 full all242 as main F_C2, no extra positive blocks. build jobs positive uses same cache. Good.
  Teto CAP_MAX160 enforced `a.cap_usd` required at most160, but a lower cap allowed. Cumulative per out. Batch est uses standard means half. Good except hard overshoot.
  Estimate $72 vs code EST plan after seed $71.34. Sync fallback standard could raise distillation above72; pre-reg says estimate about72 batch and cap160. If all residuals small82, standard difference negligible. Batch missing lines maybe more, could be higher, but estimate.
  Reading both judges $42 at .028 per row. Actual lme costs maybe .028 from Paper3 measured. Good.
  Smoke $29 difference: Need decide finding. It is explicitly historical cost smoke with second flash says "plus US$9 for flash-lite on P and about US$29 for reader and judges." Pre-reg uses $42. No explanation of updated per-row estimate. User asks numbers batem entre si: response no, reader/judges projection differs by13 and lite P standard vs batch. Could be medium/low. Not mathematical error, but inconsistent documents. Mention low or medium? Cost estimate under cap: pre-reg 72+42=114 (~115) vs smoke 67+9+29=105. User context approximate115 uses pre-reg. Since smoke was earlier and pre-reg final can update, but no stated reason. Severity low (transparency) not high. Also pro projected cost range pre-reg $380 to1370 vs smoke pro lowest344+9+29=382, highest1335+9+29=1373. matches. Good.
  Smoke reader projections at10012,16019,24229, consistent .02 per six main rows. Pre-reg adds positive control and uses .028. Could infer updated estimate. State arithmetic internally consistent with different unit assumptions, but not reconciled in text.
  - US$1.92 280 calls, shape .09, flash .08, batch .01 total2.10. exact1.9227+.0761+.01436=2.01316 plus shape.09=2.103 ->2.10. yes.
  - Pro 380 to1370 uses standard? batch default/b128 and plus. 344+9+29=382; 1335+9+29=1373. Good.
  - Distinct block counts median5 random subsets: 70067 actual all242 not median random? all242 no random. Table says distinct blocks per criterion median5 random subsets of242, for242 always same. okay.
  - Smoke says no outcome; unit counts could be seen but no questions. Fine.

  140052 actual verified read-only P3 cache. 15 failed+67 absent =82. Good.
  87 of155506 from confirm result, exact .05595. New seed subset82. Good.
  1492 rows actual plan.
  242 confirm + controls40 subset.
  No untouched instances arithmetic 500−30−8−200−262=0 yes 500-500=0. Confirm manifest242 +20 exposed? 262 confirm allocation perhaps 242+20 exposed. arithmetic okay.
  Accuracy .818 and .570: C0 full cell10 actual perhaps .5702479. C2 .81818. difference .24793. Could verify counts already d mean with C2? I didn't calculate levels but known. Fine.
  Power .228 population variance. Judge2 .240 population. Good.

  Should check n necessary table with population variance exact .227785 vs using .228 negligible. MDE12.2 etc. 10pp rho threshold .324. If using two-sided exact power with alternative normal includes lower tail negligible. Formula standard. n required uses ceiling except159. Should report low.

  Could there be high numbers mismatch pre-reg says "10 pp detectable only if rho about0.35 or more" actual .324 so at rho1/3 enough. About .35 perhaps rounding to nearest.05. I can mark low. Table 15pp n159 should ceil160. Could include one finding with both. No serious arithmetic errors.
  Power assumes equal variance/correlation, no cluster adjustment. stated. Fine.

  Should have question (2) "O IC é o mesmo do Paper3?" yes exact function current identical tag. Could state no findings serious. I can include low external import not pinned? Should I add? User expects findings numbered each question severity. I can give Q2 "Nenhum achado sério" plus perhaps low freeze guard. If finding not directly contrast perhaps Q3. Better keep Q2 concise and no issue. I can cite e-analyze:54-55,67-69,88-98; Paper3 lme analyze lines43-72,208. Verified files identical to tag. Perhaps mention code e-analyze:29-32 imports working tree; at current hash matches tag. In limits, didn't execute real analysis on actual future data.

  Q3 findings:
  1 High cap not hard. Cite PREREG:127-129; e-run:320-335 and lme-run:271-281; read ex.map e-run:388-394. Explain Ledger adds after API and only raises after crossing, executor may have in-flight/queued calls. Batch precheck at280 only estimates. Could cite e-run:280 and response costs after. Severity high due financial guard US$160. User asks teto yes.
  2 High/medium sync failures not served empty. Cite PREREG131-133; e-run:320-335,354-358,371-373. A persistent POST exception leaves cache absent; read exits. Severity high because stated failure policy not implemented and can block entire $115 run, but does not bias outcomes. Could be high operational. I can choose alta.
  3 Medium failure counts per extractor criterion and >1% flag missing. Cite PREREG131-133, e-run398-417 (global only), e-analyze99-104 (no failures). This is explicit. Medium.
  4 Low frozen check does not include PREREG/e-analyze/Paper3 imports. Perhaps not necessary to avoid noise. But could be medium pre-reg integrity. Text line3-4 says three files match precisely, so not mismatch. Procedure tag all. e-analyze as frozen at tag but no guard, honor system okay. Not a direct violation. Don't include unless important.
  Positive controls/bodies/cache all match. State no findings in those.
  Cost cap batch resume record as soon created: `ch["batch"]=create`, then state submitted, save chunks. yes. Adoption by display. Good.

  Q4 findings:
  - Parser contract low: null/missing/false memories returns parsed success rather than failed; bool importance accepted as numeric; Infinity. Which ones materially serve different between extractors? `true` accepted yields memory, text says non-number dropped, so could serve material different from declared (for any extractor output bool). Since models could differ in emitting it, yes. Severity low or medium? Importance bool unusual under JSON no schema. Low.
  - `dict` missing memories returns empty success same served material empty; only failure count/threshold impacted. Combine with missing failure reporting perhaps low.
  - Nonfinite Infinity accepted by Python non-standard JSON and served. Low perhaps too pedantic. Could mention bool only, not Infinity unless thorough.
  - Batch resume no serious differential found. Same dkey/request/response parser in both paths. Errors/missing remain todo and sync. Duplicate response lines could overwrite but API expected unique; no evidence.
  - Critical resume: Parse failures are cached with failed true. `todo_of` only missing cache, so sync pass doesn't retry parse failures. Text sync for "errors, missing lines, expired chunks" not parse failures. Failures served empty. okay.
  - Ingest marks `bad` for no response but `missing=len(meta)-got-bad`; errors no cache. good.
  - `got` counts failed parse as got and caches. okay.
  - If batch output contains duplicate key lines, `cache.put` last wins and spend double; not expected. Could note not serious.
  - Crash mid-ingest can double spend but same cached last response identical. no material difference.
  - Adopted batch uses metadata local original; same key ext/crit. no difference.
  Q4 no serious hidden asymmetry. Low parser edges and sync issue already Q3. Could say no serious case beyond declared82 old/new parser. Good.

  Perhaps test resume paths are all passing. e-test all46? Output says 46 but actual count perhaps 46. I ran all pass. Include verification.
  Should verify no actual pre-reg tag exists (test freeze pass because absent). Good.
  Should perhaps check total char full reading satisfied. yes.

  Perhaps inspect exact lme-run hashes vs tag via `git diff` no output. I can state verified byte identity using git diff. e-smoke hash SMOKE says e51637fc (sha256 not git hash) current e-smoke file perhaps matches? Smoke JSON runner sha e516; current file sha? Could compute sha256 current e-smoke to verify SMOKE run script unchanged. `e-smoke.py` current likely differs flash added so hash current 0cb9 matches flash, original pro e516. okay. Not necessary.

  Question 1 exact per call from raw mean vs rounded. Should present table perhaps concise. I can list per-call values:
  Pro default C0 .01137875 ->.0114; C2 .013025 ->.0130; P .01371125 ->.0137
  Pro b128 .00237875->.0024, .003505->.0035, .00394125->.0039
  lite P .0001313->.00013
  flash .000503->.00050, .0006055->.00061, .0007965->.00080.
  Raw smoke exact means C0 flash .000502 etc table rounding consistent.
  Projection flash standard133.4776, batch66.7388; lite P standard9.1998, batch4.5999; total batch71.3387 ->72 including82. Reading41.776 ->42; total113.115? 71.3387+41.776=113.1147, plus82 costs <.01 -> about114, context115. Pre-reg says72+42=114. Smoke flash67+9+29=105. Pro range382-1373 ->380-1370.
  Power formula include \(n \approx (z_.975+z_.80)^2 2(0.228)(1-\rho)/\delta^2\). Show n table matches. MDE at242 values exact .1216126 etc. Variance population .227784987 ->.228. Note sample .228730 ->.229 but they evidently use population, not error if descriptive variance. n for15pp rho0 exact159.07 -> ceiling160 but table159; low. 10pp rho threshold .32385. Mention no high arithmetic issues.
  140052/140134 verified cache: 140052 good,15 failed,67 absent=82. 82/140134 .058515% ->.06%. 1492. 87/155506 .055946 ->.056%. Good.

  Should check smoke reader29 vs pre-reg42. Explain smoke appears 6*242*.02=29.04, while runner/pre-reg uses1492*.028=41.776. Does smoke explicitly say six rows? Not in text. I can say numerically consistent with that, but not documented. Avoid asserting. "US$29 não bate com o pre-reg; equivale aproximadamente a 1.452 chamadas a US$.02, enquanto..." Could say origins not stated. This is low.
  Also pre-reg distillation72 vs smoke76 batch? Smoke's 67+9 are mixed pricing: flash batch and lite P standard. If apply Batch API to all as procedure, total71.34. This reconciles. Mention not discrepancy once price tier accounted.

  Severity classification: User wants each finding numbered, severity high/medium/low and file:line. I should format each Q with findings. For no issues, state verified calculations not necessarily numbered? They request each with numbered findings. I can structure:
  ##1
  1. **Baixa — projeção de leitura...** refs.
  2. **Baixa — dois arredondamentos de poder...** refs.
  Then "Conferências sem achado" bullets with arithmetic. This satisfies include all.
  Could classify power threshold as low. Cost difference perhaps medium? Budget estimates not confirmatory outcome, low.
  No high inQ1.

  Q2:
  "Nenhum achado sério." Could include 1. **Baixa — congelamento não é auto-verificado**? If I add, then not no serious still low. But is it useful? The task pre-reg verifier should catch analysis code could be modified after tag and --check still passes. Pre-reg line99 "e-analyze.py as frozen at tag" and procedure tag, no runner check needed if discipline. `--check` only reproducibility current not authenticity. Could be medium because confirmatory integrity relies on external tag check. But not asked "guard freeze" except artifact. Perhaps reviewer should flag. Yet avoid scope creep. User asks exact contrast and same CI, both correct. I can respond no findings and perhaps note at end low operational "o IC é mesmo; a identidade ao tag hoje verificada, embora importação seja working tree". If I mention as limit not finding, okay.
  Potential real issue same CI but not same data cluster selection? Paper3 `prim` built all four main cells, e-analyze six; expected. clusters same. z same. Correct.

  Q3 high cap, high sync failure, medium fail reporting. Should line refs all artifact and cited. Could number.
  Q4 low parser booleans and null. No serious resume. Perhaps identify an actual parser issue with nonnumeric "NaN" handling not necessary.
  No other files beyond cited used. Good.

  I'll run `e-analyze --check` on existing? No PaperE rows only smokes. Offline tests done.
  Should verify prompt sha C0/P actual. Smoke raw matches. Could run Python e_prompts output no network. Already e-test. Fine.
  Should perhaps calculate cache keys all six distinct test pass.
  Should perhaps run no writes? e-test writes temp only. okay.
  Should perhaps check current working tree untracked review file not touch. Fine.

  I'll update todos as I finish Q2, Q3, Q4. I can mark Q2 done Q3 in progress then perhaps immediate work already done but should not batch completions? Instructions say mark as soon finished before next. I have done all essentially, but updates can now sequential tool calls? I should avoid unchanged list. I can one update Q2 done Q3 in progress then perhaps perform final targeted check for failure report or read lines. I already read. Could do Grep for distill_failed usage to substantiate only receipt. Also cap lines. Then update.

• O contraste e o IC estão corretos e usam exatamente as funções do Paper 3; a variância de 0,228 também se reproduz como variância populacional das 242 diferenças. A retomada normal do lote mantém as mesmas chaves, corpos e parser entre batch e sync; os casos de borda adicionais que encontrei no parser são de baixa severidade.

C0 72208f90119405c6a83b28a8506e2c6d50ba3112492fc6fb11de3539a223cd27
C2 325342a36e742f1e844b7c3792dae3eb47a76879c501678b576cd6df2cc8089d
P 9e7668b2a12a1b0c5c122e62fc35520318e9c2b8bfdfa3d932a94e442d1000db
P exact construction: True
• Perhaps "receipt dist list v None could error if missing" read ensures no missing. fine.

  Should consider smoke shape probe statement "first24 failed calls >1 output token": raw calls only counts no response text retained, shape probe external not output file? SMOKE only table. I cannot verify shape counts because shape probe output perhaps not in repo. Limits mention shape-probe 11/11/2 and actual voice authorization cannot independently verify beyond user-provided. User included authorization perhaps wants acknowledge P before tag voices? I don't need question about voices, but context authorization indicates permitted. Could mention not verify external conversation. Limits include no external price/current API. Good.

  Potential pre-registration violation: P was written before any call used it. e-smoke runner current code comment flash added after pro priced out. Pre-reg P fixed before calls yes. Authorization Toto date. No issue.

  Question "Modo: challenge" User expects skeptical independent and probably verdict whether freeze. High issues mean do not freeze until fixed. Raw verdict line "NÃO CONGELARIA: ..." likely. Should raw verdict in response after Q4 and before limits. User asks "Termine com uma linha de veredito cru e uma seção de limites" means final section limits after verdict. Could verdict "NÃO APROVARIA O CONGELAMENTO como está: hipótese/IC e aritmética essencial estão certos, mas o teto e a política de falhas não são os pré-registrados." Good. Then limits. Or if high only operational not science, still don't freeze. User likely wants go/no-go. Use raw.

  Make sure all explicit questions addressed and severity each finding. Yes.
  Could include counts of no serious Q4. "Nenhum achado sério na retomada" and low parser. Good.

  Should classify cap high. Sync failure high. Failure reporting medium. Cost mismatch low. Power rounding low. Parser booleans low. Perhaps parser null low separate? Could combine one finding but file line same. Each numbered.
  Could mention `F_C2_pos` only control verified exactly. Good.
  Could mention all tests pass but don't cover high issues. Existing t_cap tests only held batch and cumulative, not sync overshoot; t_read no persistent failure. Good to explain why ALL PASS doesn't clear. Cite e-test lines248-267 perhaps optional. I can note in verification footer.

  Perhaps question 1 "n necessário" all table values not just358. Include table small 3x? Could list:
  - δ10pp:358,287,215
  -15:159(160 ceiling),128,96
  -20:90,72,54.
  MDE. Use table in response perhaps two tables (cost per call 10 rows could be heavy). Keep concise but enough. Could combine cost per call in code block or inline. User asked detailed audit, ~1500-2500 words perhaps. I should aim 1800 words? Portuguese concise 1300. Should have all calculations. Tables okay shallow. I can do per call table 3 columns model/criterion calculated. 10 rows fine. Another power table 3 rows. Response could be ~2000 tokens. I have ample.

  Line references exact:
  Q1 finding reading:
  `SMOKE-RESULT.md:101-103`, `PREREGISTRATION.md:127-129`, `e-run.py:477-482`.
  Power:
  `SMOKE-RESULT.md:77-85`, `PREREGISTRATION.md:108-113`.
  Cost per call refs `SMOKE-RESULT.md:24-36`,95-103.
  Seed refs `PREREGISTRATION.md:70-73`, cache actual not line. e-run seed182-205. 1492 lines prereg32 and e-run477.
  Q2 `e-analyze.py:67-69`,88-98,54-55, Paper3 lme-analyze62-72 and208-213. `PREREGISTRATION.md:77-82`.
  Q3 cap `e-run.py:280-284`,320-335,375-394; lme-run276-281; pre-reg127-129. High.
  Sync `e-run.py:320-335`, build jobs354-358/read371-373; pre-reg131-133.
  Failure report `e-run.py:398-420`, `e-analyze.py:99-104`; pre-reg131-133.
  Normal matches refs e-run62-86,78-80 dkey,339-367 cells.
  Q4 parser `e_prompts.py:55-67`; text pre-reg63-68. Bool lines65. Null line56. Resume e-run213-239,248-268,271-317,320-335. No serious.
  Could include nonnumeric booleans technically Python bool subclass int. "importance:true vira1 e é mantida" verified. Text says "not a number dropped"; JSON bool isn't number. Good.
  `{}` returns [] true because mem=j.get or[]; wrong null same. This affects only failed count, not material (still empty), except if boolean true gives actual unit. I can split low:
  1 Baixa boolean non-number can serve undeclared memory.
  2 Baixa malformed object counted success, distorts failure threshold. But failure reporting already missing entirely, still parser contract mismatch. Combine as one low with two subpoints? User asked numbered findings; okay one finding with both.

  No serious batch resume. However cap issue can interrupt batch and sync and then different paths serve stochastic outputs across resumed runs, but any temperature0.1 run repeated missing requests yields new outputs. Text doesn't promise deterministic across resume. Same extractor could differ between resumes, not between extractors systematically. Not hidden unfairness. Mention no evidence of cross-extractor differential beyond model outputs and declared82.
  What if a batch process dies after recording submitted but before actual API create response? create either succeeded or not; if failed no record. adoption handles. fine.
  Cache dkey model names separate L/F, criterion and block; parser version frozen. Good.

  Limites:
  - Did not spend or call real APIs; no new reader/judge/extractor outputs. Ran offline tests and plan/read-only cache.
  - Did not independently verify external model prices, actual Batch API semantics beyond60 request receipt, Toto authorization, DOI/tag external; current repo Paper3 files match tag.
  - Did not re-derive token counts from raw API responses? I have smoke-calls records with counts and costs; verified aggregates, but cannot prove authenticity against provider. State "verifiquei agregados a partir dos NDJSON, não autenticidade das respostas".
  - Power uses assumed normal approximation, equal var/correlation, not simulation with actual future F or clustered finite sample; cannot verify ρ or detectability realized.
  - Parser edges tested synthetic, frequency in real outputs unknown.
  - Real run not exists, so no end-to-end paid read/analysis.
  Perhaps limits should not be too long. 4 bullets.
  Verdict raw before limits as requested.

  Should update todos properly. I can mark Q3 done Q4 in progress then perhaps no more tool needed? I should use Todo update, then immediately mark Q4 done consolidation in progress in another call after perhaps think. Could call now.

• Os blocos, as seis chaves por bloco, as 1.492 células e o controle positivo estão de acordo com o texto. As falhas de execução não são cobertas pelos testes atuais: os 46 testes passam, mas o teste de teto só exercita a retenção de um chunk em batch, não o estouro na passagem síncrona.

• Perhaps run a resume equivalence synthetic test beyond existing? Existing tests cover list parsing, duplicate guard, sync residue. I can rely. No need tools. But to satisfy as soon done, update Q4 done and consolidation in progress. Then prepare response and mark done before response. Could do one update now then final check mentally then another.I need response polished. Before response mark done. But need formulate response fully in mind. I'll decide exact severity and wording.

  Opening "Li os cinco arquivos inteiros. Rodei plan e e-test (ALL PASS), conferi cache e rows." Good.

  Q1:
  Findings numbered first:
  1 Baixa cost reading mismatch.
  2 Baixa power threshold and ceiling.
  Then checks no findings with arithmetic.

  Cost table could be under "Conferi e fechei". If findings numbered, verified items not findings perhaps bullets. User asks each question findings numbered, okay.
  Q1 finding power: "A tabela usa arredondamento, não 'n necessário' estrito: 15pp,rho0=159.0706, deveria ceiling160, table159. E rho mínimo10pp=0.32385, not0.35. MDE values correct. Severity low." Note if n159 exact power slightly below80, so valid.
  Q1 cost mismatch: "SMOKE says29 vs pre-reg42. They don't batem. Runner formula42 exact. No rationale in docs. Other projections match after pricing." Good.
  Costs table perhaps avoid all pro formulas by listing "na ordem da tabela" values. But user specifically include cost per call. A table with all10 good.
  Raw exact smoke JSON exact means differ from rounded token formula, table rounding correct. I can say "usando tokens arredondados do relatório". Values.
  Projections:
  Pro batch default and b128 at242:1335.30/344.20; plus lite9.2 and reader29 yields1373.5/382.4 -> pre-reg380-1370. At100/160 table match, perhaps mention 595/153,922/238. Should include all projections? "100/160/242 pro default:595.38/922.36/1335.30; budget128:153.47/237.76/344.20." Good.
  Flash:133.48 std,66.74 batch. LiteP9.20std,4.60batch. total batch71.34. Reader41.776. Pre-reg114. User context115 approximate. Good.
  Smoke pro "US$380 to1370" includes all design reader etc. Fine.
  Seed and rows.
  Power formula and table. Could be long but necessary.
  Variance .228 from rows population. Show mean65-5 /242=.2479339. Variance counts can verify: d counts -1=5,0=172,+1=65. Population variance formula E[d²]=70/242=.289256; mean²=.061471 ->.227785. Good. Sample .22873. Smoke uses population. Judge2 counts mean66/242=.272727, variance .239669->.240. Nice.
  n table formula. Good.

  Q2 no findings. Show formula exact per q and judge1. Negative hi correct. Same CI formula:
  m mean; cluster sums residuals; var=sum S_g²/n² *G/(G-1); CI=m±1.96se. Same as Paper3. Complete-case6. Fine. Could state current imported files byte-identical tag. This is enough.

  Q3:
  1 Alta cap.
  Precise "Ledger increments then raises after call; no preflight in sync/read. With one worker synthetic cap.001 two API calls and .0056 recorded. So cap160 can be exceeded; batch precheck estimate only." This synthetic probe details strong evidence. Do I include exact .0056 depends fake F1000in1000out: each .0028,2 calls. Yes.
  2 Alta sync failure.
  3 Media report.
  Then "Sem achado nos demais itens" list.
  Perhaps severity high for sync failure "operacional" to clarify not bias. Use **Alta (operacional)**.
  Cap high financial.
  Failure reporting medium.

  Q4:
  1 Baixa parser boolean.
  2 Baixa null object success. Could combine but separate numbered.
  Then no serious resume. Should user says if nothing serious say: "Não encontrei caso sério de retomada que sirva material diferente entre L e F." Explanation same request body/dkey and response_value, errors missing left for sync; duplicates guard. "A assimetria de no máximo82 blocos L is declared." Good.
  Parser boolean affects any model only if emits malformed importance; not systematic. Null affects counts not served material. Note this.
  Could mention `Infinity` too? Not needed. Perhaps add in same low parser finding "Python também aceita Infinity" but overly pedantic. Skip.

  Verdict no freeze due high operational.
  Limits 4 bullets.

  Do I need cite every arithmetic verified item file lines? I can include refs at paragraph ends. Good.

  Response ~2500 words perhaps too much but user asked detailed. Could trim cost table and power table. Target 1800 tokens? I'll estimate:
  Opening50, Q1 700, Q2 150,Q3 400,Q4 250, verdict/limits200 =1750. Fine.

  Should mark todo done before responding.

• A consolidação está fechada: não há erro no estimador nem nas contas centrais, mas há dois bloqueadores operacionais para o congelamento — o teto pode ser ultrapassado e a política pré-registrada para falhas após sync não está implementada.

• Now respond in Portuguese. Ensure "custo por chamada" table values exactly and raw JSON notes. Use $ formatting US$. Avoid heavy deep nesting. Headings 4. Each findings numbered perhaps numbering resets.
  Q1 arithmetic formula use LaTex terminal renders markdown okay.
  "n=159.07 -> table159, strict ceiling160". MDE with n242 using .228 exact.
  "10 pp detectable only if rho about .35 or more" actual .324. At .35 indeed detectable, word "only if about" approximate. Low.
  Reading projection difference low.
  All other numbers match. Good.

  Q3 cap statement "stops a process at cap" code technically stops after crossing; user might not interpret as hard guarantee. But cap explicit US$160, high valid. Explain.
  Sync failure text says after sync served empty, code exits read. high.
  Failure report "receipt total only" code per criterion can infer from cache externally but not report. correct.
  "1,492 cells" rows. Positive sessions removed exact `evidence`.
  Q4 "material different between extractors" booleans could serve if one outputs true, same parser though. Phrase "não é viés assimétrico de código, mas é material fora do contrato declarado". Good.
  Resume no serious.
  Limit "Não verifiquei autenticidade do cache Paper3?" I read DB and rows counts. Could state values recomputed from cited local artifacts, not provider. Good.
  "Paper3 tag byte identity" verified current two files. No need limitation.
  "Não executei tag real" absent expected.
  "46 tests pass" include opening or limits. Good.

  I'll compose.

• Li os cinco arquivos integralmente. Também executei `plan` e os 46 testes offline (`ALL PASS`), recalculei as estatísticas das linhas do Paper 3 e consultei o cache confirmatório em modo somente leitura.

  ## 1. Números, custos e poder

  **1.1 — Baixa: a projeção de leitura e julgamento mudou de US$ 29 para US$ 42 sem reconciliação documentada.**  
  `SMOKE-RESULT.md:101-103` estima “about US$ 29 for reader and judges”; `PREREGISTRATION.md:127-129` estima US$ 42. O runner confirma a segunda: `1.492 × US$ 0,028 = US$ 41,776` (`e-run.py:477-482`). Não é erro aritmético do pré-registro, mas os dois documentos não batem entre si.

  **1.2 — Baixa: dois arredondamentos de poder são imprecisos.**  
  Em `SMOKE-RESULT.md:77-85` e `PREREGISTRATION.md:108-113`:

  - Para efeito de 15 pp e ρ=0, a conta dá **n=159,0706**. A tabela mostra 159; se “needs” significa o menor inteiro com pelo menos 80% de poder, deveria ser **160**.
  - Para detectar 10 pp com n=242, o limiar calculado é **ρ≥0,32385**, não aproximadamente 0,35. “Cerca de 0,35” é conservador, mas pouco exato.

  Fora esses pontos, as contas fecham.

  **Custos por chamada.** Usando os tokens arredondados das tabelas e os preços declarados (`SMOKE-RESULT.md:24-36`, `SMOKE-RESULT.md:95-103`):

  | Extrator | Critério | Cálculo, US$ | Arredondamento correto |
  |---|---|---:|---:|
  | pro default | C0 | 0,01137875 | 0,0114 |
  | pro default | C2 | 0,01302500 | 0,0130 |
  | pro default | P | 0,01371125 | 0,0137 |
  | pro budget 128 | C0 | 0,00237875 | 0,0024 |
  | pro budget 128 | C2 | 0,00350500 | 0,0035 |
  | pro budget 128 | P | 0,00394125 | 0,0039 |
  | flash-lite | P | 0,00013130 | 0,00013 |
  | flash | C0 | 0,00050300 | 0,00050 |
  | flash | C2 | 0,00060550 | 0,00061 |
  | flash | P | 0,00079650 | 0,00080 |

  Os valores exatos dos NDJSON — por exemplo, flash C0 US$ 0,000502 e C2 US$ 0,000605 — são compatíveis; as pequenas diferenças vêm de usar médias de tokens já arredondadas.

  **Projeções.**

  - Pro default, batch, para 100/160/242 instâncias: **US$ 595,38 / 922,36 / 1.335,30**.
  - Pro budget 128, batch: **US$ 153,47 / 237,76 / 344,20**.
  - Flash, três critérios, 70.067 blocos: **US$ 133,4776 standard; US$ 66,7388 batch**.
  - Flash-lite P: **US$ 9,1998 standard; US$ 4,5999 batch**.
  - Destilação total no procedimento em batch: **66,7388 + 4,5999 = US$ 71,3387**, coerente com “about US$ 72”, incluindo as 82 repetições.
  - Com leitura a US$ 41,776, o total estimado é aproximadamente **US$ 113–114**, compatível com a aproximação de US$ 115.
  - A faixa pro de aproximadamente US$ 380–1.370 também fecha ao somar P no flash-lite e leitura.

  Assim, a diferença entre os US$ 67 + US$ 9 do smoke e os US$ 72 do pré-registro é principalmente **batch versus standard para flash-lite P**, não uma conta errada.

  **Poder.** Recalculei das 242 linhas confirmatórias:

  - d tem contagens −1: 5, 0: 172, +1: 65.
  - Média: **0,2479339**, ou +24,8 pp.
  - Variância populacional: **0,22778499 → 0,228**. A variância amostral seria 0,228730; o relatório claramente usa a populacional.
  - Judge 2: média 0,272727 e variância populacional 0,239669 → 0,240.

  Com a aproximação normal declarada:

  \[
  n \approx \frac{(z_{0,975}+z_{0,80})^2\,2(0,228)(1-\rho)}{\delta^2},
  \qquad (z_{0,975}+z_{0,80})^2=7,8488797.
  \]

  Isso reproduz:

  - 10 pp: **358 / 287 / 215** para ρ=0 / 0,2 / 0,4;
  - 15 pp: **159,07 / 127,26 / 95,44**;
  - 20 pp: **89,48 / 71,58 / 53,69**;
  - efeito detectável com n=242: **12,161 / 10,877 / 9,420 pp**, corretamente arredondado para **12,2 / 10,9 / 9,4 pp**.

  **140.052, 140.134 e 1.492.** Conferi diretamente o cache citado:

  - 70.067 blocos distintos × C0/C2 = **140.134**;
  - **140.052** reutilizáveis;
  - 15 marcados como falhos + 67 ausentes = **82** a repetir;
  - 82/140.134 = **0,058515% → 0,06%**;
  - 87/155.506 = **0,055946% → 0,056%**;
  - linhas: `242 × 6 + 40 = **1.492**`.

  Esses números estão corretos (`PREREGISTRATION.md:32-33`, `PREREGISTRATION.md:70-73`; `e-run.py:182-205`).

  ## 2. Contraste principal e IC

  **Nenhum achado sério.**

  O contraste implementado é exatamente, por instância:

  ```python
  (F_C2 - F_C0) - (L_C2 - L_C0)
  ```

  em `e-analyze.py:88-92`. Portanto, um valor negativo significa encolhimento da vantagem de C2 no extrator forte. As decisões `hi < 0` e `lo > 0` estão no sentido correto (`e-analyze.py:93-101`), usando judge 1 como primário e judge 2 como bracket.

  O IC também é o mesmo do Paper 3:

  - média dos contrastes por instância;
  - clusters pelos componentes que compartilham sessões de resposta;
  - somas dos resíduos por cluster;
  - `SE² = Σ S_g² / n² × G/(G−1)`;
  - IC normal bilateral de 95%.

  Compare `e-analyze.py:54-55`, `e-analyze.py:67-69` com `paper3-construction/lme-analyze.py:43-72`. É também a função usada nos contrastes do Paper 3 (`paper3-construction/lme-analyze.py:208-213`). Os dois arquivos importados do Paper 3 estão atualmente byte-idênticos aos da tag `paper3-prereg-v1.3`.

  ## 3. Blocos, cache, células e teto

  **3.1 — Alta: o teto de US$ 160 não é um teto rígido.**  
  O pré-registro diz “Cap: US$ 160 cumulative” e que o processo para no teto (`PREREGISTRATION.md:127-129`). Entretanto:

  - batch usa apenas uma **estimativa** para reter chunks (`e-run.py:280-284`);
  - sync e read fazem a chamada à API antes de contabilizar o custo (`e-run.py:320-335`, `e-run.py:375-394`);
  - `Ledger.add` soma o custo e só então lança `SystemExit` se já tiver passado do teto (`paper3-construction/lme-run.py:276-281`);
  - chamadas em execução ou já enfileiradas podem continuar.

  Numa sonda sintética com um único worker e teto de US$ 0,001, foram feitas **duas chamadas** e registrados **US$ 0,0056**. O teste existente só verifica retenção de chunk em batch e acumulação entre processos (`e-test.py:248-267`), não esse estouro.

  **3.2 — Alta: falha persistente após sync não é servida vazia; ela bloqueia toda a leitura.**  
  O texto promete que um bloco que falhar após a passagem síncrona será servido vazio (`PREREGISTRATION.md:131-133`). Mas `distill_sync` captura a exceção e não grava nada no cache (`e-run.py:320-335`). Depois, `build_jobs` conta aquela referência como ausente e `read` encerra com “run distill first” (`e-run.py:354-358`, `e-run.py:370-373`).

  Reproduzi isso com uma falha persistente simulada: cache `None`, um item ainda pendente. Apenas respostas recebidas e depois reprovadas no parser viram blocos vazios cacheados. A política pré-registrada para falhas de rede/API não está implementada.

  **3.3 — Média: o relatório por extrator × critério e o aviso de falhas >1% não existem.**  
  O texto exige contagem por extrator e critério e aviso ao lado do primário quando alguma célula superar 1% (`PREREGISTRATION.md:131-133`). O receipt grava somente um **`distill_failed` global** (`e-run.py:398-420`), e `e-analyze.py` não lê falhas nem imprime esse aviso junto ao primário (`e-analyze.py:99-104`).

  **Nos demais pontos pedidos, o código corresponde ao texto:**

  - corpos L/F e `thinkingBudget: 0`: `e-run.py:61-86`;
  - chaves separadas por modelo, configuração, critério e bloco: `e-run.py:78-80`;
  - seis chaves distintas por bloco, confirmadas pelos testes;
  - seed somente de L_C0/L_C2, sem respostas ou notas: `e-run.py:182-205`;
  - seis células principais nas 242 e `F_C2_pos` somente nas 40 de `control_subsample`: `e-run.py:339-350`;
  - remoção exata das sessões cujos IDs estão em `answer_session_ids`: `e-run.py:349` e `paper3-construction/lme-run.py:232-233`;
  - chunks de no máximo 20.000, registro e adoção por display name: `e-run.py:213-239`, `e-run.py:271-317`.

  ## 4. Parser e retomada: material diferente entre extratores

  **4.1 — Baixa: `importance: true` é aceito como número e pode servir memória fora do contrato declarado.**  
  Em Python, `bool` é subclasse de `int`. Assim, a condição de `e_prompts.py:63-66` aceita `true`, que passa no corte como 1; `false` é descartado como 0. Reproduzi ambos. O texto diz que importância que não é número é descartada (`PREREGISTRATION.md:63-65`). Não há um caminho assimétrico deliberado entre L e F, mas, se apenas um deles emitir esse JSON, o material servido pode divergir do comportamento declarado.

  **4.2 — Baixa: objetos malformados podem ser contados como sucesso.**  
  `{}`, `{"memories": null}` e `{"memories": false}` retornam `([], True)` por causa de `j.get("memories") or []` (`e_prompts.py:55-62`). Pela regra “anything else is a failed block”, deveriam ser falhas. O material continua vazio, mas a contagem de falhas — e portanto o controle de 1% — pode ser subestimada.

  **Não encontrei caso sério na retomada normal do lote que sirva material diferente entre os extratores sem declaração.** Batch e sync usam o mesmo `request_body`, as mesmas chaves e o mesmo `response_value`; erros e linhas ausentes permanecem pendentes para sync (`e-run.py:248-268`, `e-run.py:320-335`). A adoção por display name não recria o chunk. A única assimetria parser antigo/novo é a dos **82 blocos flash-lite**, explicitamente declarada no pré-registro.

  **Veredito cru:** **NÃO CONGELARIA assim.** Hipótese, sinal, IC e aritmética central estão corretos, mas o teto não garante US$ 160 e a política de falhas após sync não faz o que o pré-registro promete.

  ## Limites desta verificação

  - Não fiz chamadas pagas nem executei o estudo real com extratores, leitor e juízes; os testes end-to-end foram os fakes offline do repositório.
  - Verifiquei os agregados dos smokes a partir dos NDJSON locais, não sua autenticidade contra históricos dos provedores nem os preços externos vigentes.
  - Não verifiquei independentemente a autorização externa do Toto; usei a autorização fornecida no pedido.
  - O cálculo de poder verifica a aproximação normal e suas premissas, não o ρ nem o poder que serão efetivamente observados com os resultados do flash e os clusters finais.
  - Os casos de borda do parser foram demonstrados sinteticamente; sua frequência em respostas reais dos modelos permanece desconhecida.

To resume this session: kimi -r session_7b209a96-f296-4678-ac7a-b5dd6b363fcf
