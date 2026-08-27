#!/usr/bin/env node
/**
 * replay-oportunidade.mjs — item 1 do PROTOCOL-CALIBRATION-2026-08-27.
 *
 * Replay do canal de boost do Paper 2 exercitando o CÓDIGO REAL de serving
 * (`buildBriefDiverse` importada do `dist`), não uma reconstrução. Existe porque
 * toda medição de "oportunidade" feita até 27/08 mediu ORDENAÇÃO sobre um pool
 * reimplementado, e o §4 de DEVIATIONS-FOR-PAPER.md declara isso como defeito
 * aberto: nada fazia replay de `interleaveFresh`, `pickDedup`, `pinned`,
 * near-dup nem do corte do `LIMIT 400`.
 *
 * Três modos, e o terceiro é condição de no-go:
 *
 *   ancora  reproduz a âncora publicada (pool 108, 55 do estudo, 44 grupos,
 *           0 nunca-servidos, posição 0) usando `fetchFreshCandidates` REAL.
 *           Divergência aqui é achado, não erro do script.
 *   campo   replay dos briefs do log da janela fechada, comparando
 *           churn/would_enter/would_leave com o que a PRODUÇÃO registrou.
 *           É a âncora mais forte disponível: valida o pipeline inteiro.
 *   dose    varredura de `w` sobre estados reais. Se `w = 100.000` não move
 *           NADA em NENHUM estado, o canal não existe e o estudo morre aqui —
 *           o que é um resultado.
 *
 * ─── O defeito de relógio que este script tem de contornar ─────────────────
 *
 * `src/api/brief.ts:645` filtra a população elegível com
 * `julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?`.
 * O corte de idade usa o relógio do SQLite, NÃO o `nowMs` passado por
 * argumento. Consequência: o brief não é função pura de
 * (corpus, serve-state, nowMs) — a população elegível anda sozinha com o tempo
 * de parede. É a MESMA classe de defeito já documentada em três scripts de
 * medição, agora encontrada no código de PRODUÇÃO.
 *
 * O contorno é aritmético e exato, não é fake-clock: como o predicado é
 * `agora − data <= K`, o instante de corte é `agora − K`. Para reproduzir o
 * corte de `T_REF − K₀` basta usar `K = K₀ + (agora − T_REF)`. Mesmo predicado,
 * mesmo instante de corte. Aplicado aos DOIS knobs (`freshMaxAgeDays` e
 * `freshGlobalMaxAgeDays`), porque :809 e :845 sobrescrevem o primeiro pelo
 * segundo no sub-pool global.
 *
 * ─── Nada tem default ──────────────────────────────────────────────────────
 *
 * Corpus e serve-state são obrigatórios por caminho explícito. A lição é de
 * 27/08: a primeira remediação usou o DB vivo como corpus quando a produção
 * serve o snapshot de epoch, e o número saiu plausível e errado.
 *
 * Uso:
 *   node replay-oportunidade.mjs --modo ancora \
 *     --raiz /root/.openclaw/workspace/tools/nox-mem \
 *     --corpus /var/lib/nox-mem/epochs/e20260826T060003Z.db \
 *     --vivo   /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
 *     --t-ref  '2026-08-26T20:35:00Z' \
 *     --excluir-briefs sondas.txt
 */

import Database from "better-sqlite3";
import { createHash } from "node:crypto";
import { readFileSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { randomUUID } from "node:crypto";

// ─── args, todos explícitos ────────────────────────────────────────────────

function args(argv) {
  const o = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) throw new Error(`argumento solto: ${a}`);
    const k = a.slice(2);
    if (["sem-assert","manter-tmp","so-churn"].includes(k)) { o[k] = true; continue; }
    const v = argv[++i];
    if (v === undefined || v.startsWith("--")) throw new Error(`--${k} sem valor`);
    if (k === "w") (o.w ??= []).push(Number(v));
    else o[k] = v;
  }
  return o;
}

const A = args(process.argv);
const exigir = (k) => {
  const v = A[k];
  if (v === undefined || v === "") {
    console.error(`FALTA --${k} (este script não tem default para nada)`);
    process.exit(2);
  }
  return v;
};

const MODO = exigir("modo");
if (!["ancora", "campo", "dose"].includes(MODO)) {
  console.error(`--modo inválido: ${MODO}`); process.exit(2);
}
const RAIZ = resolve(exigir("raiz"));
const CORPUS = resolve(exigir("corpus"));
const VIVO = resolve(exigir("vivo"));
const CORTE = A.corte ?? "estrito";
if (!["estrito", "inclusivo", "rowid"].includes(CORTE)) {
  console.error(`--corte inválido: ${CORTE} (estrito|inclusivo|rowid)`); process.exit(2);
}

// ─── o que o dist tem de fornecer, e o que ele NÃO exporta ─────────────────

const DIST = join(RAIZ, "dist");
const brief = await import(join(DIST, "api", "brief.js"));
const div = await import(join(DIST, "api", "brief-diversity.js"));
const p2 = await import(join(DIST, "paper2", "brief-outcome.js"));

for (const [nome, v] of Object.entries({
  buildBriefDiverse: brief.buildBriefDiverse,
  fetchFreshCandidates: brief.fetchFreshCandidates,
  scopePatterns: brief.scopePatterns,
  DIVERSITY_DEFAULTS: div.DIVERSITY_DEFAULTS,
  boostsParaCandidatos: p2.boostsParaCandidatos,
  carregarDesignados: p2.carregarDesignados,
  P2_DELTA_CUT: p2.P2_DELTA_CUT,
})) if (v === undefined) { console.error(`dist não exporta ${nome}`); process.exit(2); }

/**
 * `GLOBAL_FRESH_PATTERNS`, `FRESH_CANDIDATE_POOL` e `interleaveFresh` NÃO são
 * exportados. Os dois primeiros são replicados aqui — e é exatamente o ponto
 * onde uma cópia silenciosamente desatualizada mentiria. Então não se confia na
 * cópia: extrai-se o literal do FONTE e compara-se. Guarda que só verifica
 * presença é decoração; esta compara valor e aborta.
 */
const FONTE = readFileSync(join(RAIZ, "src", "api", "brief.ts"), "utf8");

function literalDoFonte(re, rotulo) {
  const m = FONTE.match(re);
  if (!m) { console.error(`não achei ${rotulo} em src/api/brief.ts`); process.exit(2); }
  return m[1];
}
const PAT_FONTE = literalDoFonte(
  /const GLOBAL_FRESH_PATTERNS = (\[[^\]]*\]);/, "GLOBAL_FRESH_PATTERNS");
const GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"];
if (JSON.parse(PAT_FONTE.replace(/'/g, '"')).join("|") !== GLOBAL_FRESH_PATTERNS.join("|")) {
  console.error(`GLOBAL_FRESH_PATTERNS divergiu do fonte: ${PAT_FONTE}`);
  process.exit(2);
}
const POOL_FONTE = Number(literalDoFonte(
  /const FRESH_CANDIDATE_POOL = (\d+);/, "FRESH_CANDIDATE_POOL"));
const FRESH_CANDIDATE_POOL = 400;
if (POOL_FONTE !== FRESH_CANDIDATE_POOL) {
  console.error(`FRESH_CANDIDATE_POOL divergiu: fonte=${POOL_FONTE}`); process.exit(2);
}

/**
 * Auditoria do relógio: os três sítios de `'now'` no caminho do brief. Dois têm
 * de ficar INERTES no replay, e o terceiro é o que o offset corrige. Se o fonte
 * ganhar um quarto, isto acusa em vez de deixar passar.
 */
const SITIOS = FONTE.split("\n")
  .map((l, i) => [i + 1, l])
  .filter(([, l]) => /julianday\('now'\)|datetime\('now'/.test(l));
const ESPERADOS = new Set([293, 372, 571, 645]);
const inesperados = SITIOS.filter(([n]) => !ESPERADOS.has(n));
if (inesperados.length) {
  console.error("sítio de relógio NOVO no caminho do brief — replay não é fiel:");
  for (const [n, l] of inesperados) console.error(`  :${n} ${l.trim()}`);
  process.exit(2);
}

// ─── T_REF e o offset de idade ─────────────────────────────────────────────

function msDe(iso) {
  const t = Date.parse(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  if (Number.isNaN(t)) throw new Error(`instante inválido: ${iso}`);
  return t;
}

/** cfg com o corte de idade transladado para `tRefMs`. Ver cabeçalho. */
function cfgEm(tRefMs) {
  const base = { ...div.DIVERSITY_DEFAULTS, mode: "active" };
  const desloc = (Date.now() - tRefMs) / 86400000;
  if (desloc < 0) throw new Error("T_REF no futuro: o offset de idade só translada para trás");
  return {
    ...base,
    freshMaxAgeDays: base.freshMaxAgeDays + desloc,
    freshGlobalMaxAgeDays: base.freshGlobalMaxAgeDays + desloc,
    _offset_dias: desloc,
  };
}

// ─── sondas: exclusão por brief_id ENUMERADO, nunca por corte de tempo ─────

const SONDAS = (() => {
  const f = A["excluir-briefs"];
  if (!f) {
    console.error("FALTA --excluir-briefs <arquivo com um brief_id por linha>.");
    console.error("Passe um arquivo vazio para declarar 'nenhuma sonda a excluir'.");
    process.exit(2);
  }
  const ids = readFileSync(resolve(f), "utf8").split("\n")
    .map((s) => s.trim()).filter((s) => s && !s.startsWith("#"));
  const ruins = ids.filter((s) => !/^[0-9a-f-]{36}$/.test(s));
  if (ruins.length) { console.error(`brief_id malformado: ${ruins.join(", ")}`); process.exit(2); }
  return ids;
})();

/**
 * Serve-state derivado: só `brief_log`, só `served_at <= T_REF`, sem as sondas.
 * O corpus NUNCA é copiado nem escrito — é aberto readonly. `brief_log` não
 * pode sair do vivo (achado A3), e não há como filtrar dentro da query real,
 * então filtra-se a TABELA. Em /var/tmp, nunca /tmp: cópia descartável em tmpfs
 * come RAM.
 */
function serveStateDerivado(vivoRO, tRefMs, dir, idMax = null) {
  const p = join(dir, "serve-state.db");
  const d = new Database(p);
  d.exec(`CREATE TABLE brief_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            scope TEXT, agent TEXT,
            served_at TEXT NOT NULL DEFAULT (datetime('now')),
            brief_id TEXT);
          CREATE INDEX idx_brief_log_chunk ON brief_log(chunk_id, served_at);
          CREATE INDEX idx_brief_log_brief ON brief_log(brief_id);`);
  const corte = new Date(tRefMs).toISOString().slice(0, 19).replace("T", " ");
  const filtro = SONDAS.length
    ? ` AND (brief_id IS NULL OR brief_id NOT IN (${SONDAS.map(() => "?").join(",")}))`
    : "";
  /**
   * ⚠️ `served_at` tem resolução de SEGUNDO e cada brief insere ~10 linhas
   * DEPOIS de compor. Com `<=`, o serve-state de um brief contém as linhas que
   * ele mesmo acabou de servir (e as dos briefs irmãos do mesmo segundo — o cron
   * dispara 6 agentes em 1-2 s). Isso faz os chunks recém-servidos parecerem "já
   * servidos" e destrói justamente os estratos de `last_served` que o boost
   * desempata. `--corte estrito` (default) usa `<`, excluindo o segundo inteiro;
   * `inclusivo` usa `<=`. O preço do estrito é perder linhas gravadas ANTES no
   * mesmo segundo: com resolução de segundo não há corte exato, e a escolha tem
   * de ser declarada em vez de herdada.
   */
  const op = CORTE === "inclusivo" ? "<=" : "<";
  const linhas = idMax === null
    ? vivoRO.prepare(
        `SELECT id, chunk_id, scope, agent, served_at, brief_id FROM brief_log
          WHERE served_at ${op} ?${filtro}`,
      ).all(corte, ...SONDAS)
    : vivoRO.prepare(
        `SELECT id, chunk_id, scope, agent, served_at, brief_id FROM brief_log
          WHERE id < ?${filtro}`,
      ).all(idMax, ...SONDAS);
  const ins = d.prepare(
    "INSERT INTO brief_log (chunk_id, scope, agent, served_at, brief_id) VALUES (?,?,?,?,?)");
  d.transaction(() => {
    for (const l of linhas) ins.run(l.chunk_id, l.scope, l.agent, l.served_at, l.brief_id);
  })();
  const total = idMax === null
    ? vivoRO.prepare(`SELECT COUNT(*) c FROM brief_log WHERE served_at ${op} ?`).get(corte).c
    : vivoRO.prepare("SELECT COUNT(*) c FROM brief_log WHERE id < ?").get(idMax).c;
  return { db: d, path: p, linhas: linhas.length, descartadas: total - linhas.length, corte, op, idMax };
}

// ─── provedor de boost: replica brief.ts:957 ───────────────────────────────

/**
 * Produção monta o provedor em `src/api/brief.ts:957` com o handle VIVO (não o
 * corpus): `p2_verdict` e o gate de maturidade vivem no vivo. Aqui é igual, e o
 * acumulador da união das ≥2 invocações também — é o que prova o que o código
 * FEZ contra o que a regra DIZ.
 */
function provedorEm(vivoRO, w, tRefMs, env) {
  const inicio = p2.epochInicioMs(p2.epochInicioISO(tRefMs));
  const emitidos = new Map();
  const fn = (cands) => {
    const m = p2.boostsParaCandidatos(vivoRO, cands, w, inicio, env);
    for (const [id, b] of m) emitidos.set(id, b);
    return m;
  };
  return { fn, emitidos, inicioEpochMs: inicio };
}

// ─── execução ──────────────────────────────────────────────────────────────

const TMP = join("/var/tmp", `replay-oportunidade-${randomUUID()}`);
mkdirSync(TMP, { recursive: true });
const limpar = () => { if (!A["manter-tmp"]) try { rmSync(TMP, { recursive: true, force: true }); } catch {} };
process.on("exit", limpar);

const corpus = new Database(CORPUS, { readonly: true, fileMustExist: true });
const vivoRO = new Database(VIVO, { readonly: true, fileMustExist: true });
try {
  const sv = await import("sqlite-vec");
  sv.load(corpus);
} catch { /* FTS responde; o brief não usa o caminho semântico */ }

const ENV = {
  ...process.env,
  NOX_P2_DESIGNATION: A.designacao ? resolve(A.designacao) : process.env.NOX_P2_DESIGNATION,
  NOX_P2_DESIGNATION_SHA256: A["designacao-sha256"] ?? process.env.NOX_P2_DESIGNATION_SHA256,
};
const desig = p2.carregarDesignados(ENV);
if (!desig.ok) {
  console.error(`designação não carregou: ${desig.motivo ?? "?"} — sem ela o boost é vazio e o replay não mede nada`);
  process.exit(2);
}

const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const proc = {
  gerado_em: new Date().toISOString(),
  modo: MODO,
  corte_serve_state: CORTE,
  corpus: CORPUS,
  corpus_sha256_primeiros_1MB: createHash("sha256")
    .update(readFileSync(CORPUS).subarray(0, 1 << 20)).digest("hex"),
  vivo: VIVO,
  designacao: ENV.NOX_P2_DESIGNATION,
  designacao_sha256: ENV.NOX_P2_DESIGNATION && existsSync(ENV.NOX_P2_DESIGNATION)
    ? sha(ENV.NOX_P2_DESIGNATION) : null,
  designados: desig.ids.size,
  sondas_excluidas: SONDAS,
  fonte_brief_ts_sha256: createHash("sha256").update(FONTE).digest("hex"),
};

/** Composição do pool de cobertura GLOBAL pelo caminho real. */
function poolGlobal(tRefMs, serveDb, provedor) {
  const cfg = cfgEm(tRefMs);
  const pool = brief.fetchFreshCandidates(
    corpus, GLOBAL_FRESH_PATTERNS,
    { ...cfg, freshMaxAgeDays: cfg.freshGlobalMaxAgeDays },
    tRefMs, serveDb, provedor,
  );
  return { pool, cfg };
}

const estudo = new Set(vivoRO.prepare(
  `SELECT DISTINCT chunk_id FROM p2_verdict
    WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')`,
).all().map((r) => r.chunk_id));

const saida = { procedencia: proc };
let falhou = false;

if (MODO === "ancora") {
  const tRefMs = msDe(exigir("t-ref"));
  const sv = serveStateDerivado(vivoRO, tRefMs, TMP);
  const { pool, cfg } = poolGlobal(tRefMs, sv.db, undefined);
  /**
   * ⚠️ `ordenarCobertura` DESCARTA `lastServedMs` do objeto devolvido
   * (`({ lastServedMs: _drop, ...c })`), então a chave de estrato NÃO está no
   * pool retornado — agrupar por ela dá um grupo só, silenciosamente. A chave é
   * recuperada do serve-state com a MESMA query que o código usa (`MAX`), que é
   * também a chave que `measurement/gap-defs.mjs` usou na âncora publicada.
   */
  const ls = sv.db.prepare("SELECT MAX(served_at) m FROM brief_log WHERE chunk_id = ?");
  const chaveDe = new Map(pool.map((c) => [c.row.id, ls.get(c.row.id).m ?? null]));
  const grupos = new Set(pool.map((c) => String(chaveDe.get(c.row.id))));
  const obs = {
    t_ref: new Date(tRefMs).toISOString(),
    offset_idade_dias: cfg._offset_dias,
    serve_state: { linhas: sv.linhas, descartadas_por_sonda: sv.descartadas, corte: sv.corte },
    pool: pool.length,
    estudo_no_pool: pool.filter((c) => estudo.has(c.row.id)).length,
    grupos_last_served: grupos.size,
    nunca_servidos: pool.filter((c) => chaveDe.get(c.row.id) === null).length,
    posicao_primeiro_estudo: pool.findIndex((c) => estudo.has(c.row.id)),
  };
  /**
   * ⚠️ A âncora depende da configuração de sondas, e a tupla citada no
   * PROTOCOL-CALIBRATION-2026-08-27 ("pool 108, 55/55, 44 grupos,
   * nunca-servidos 0" + "sondas excluídas por brief_id") é INTERNAMENTE
   * INCONSISTENTE: `44 grupos` é a figura CONTAMINADA, que vem junto com
   * `posicao 3`. Descontaminada, a tabela de REMEDIATION-2026-08-27 §1 dá
   * `43 / 0`. Nenhuma configuração produz `44 / 0`.
   *
   * As duas colunas ficam aqui declaradas e a seleção é pela lista de exclusão,
   * não por escolha. Rodar os dois modos é o teste de que a harness é SENSÍVEL à
   * exclusão — se as duas configurações dessem o mesmo número, a exclusão seria
   * decoração.
   */
  const ANCORAS = {
    com_sondas: { pool: 108, estudo_no_pool: 55, grupos_last_served: 44, nunca_servidos: 0, posicao_primeiro_estudo: 3 },
    sem_sondas: { pool: 108, estudo_no_pool: 55, grupos_last_served: 43, nunca_servidos: 0, posicao_primeiro_estudo: 0 },
  };
  const ancora = SONDAS.length ? ANCORAS.sem_sondas : ANCORAS.com_sondas;
  obs.configuracao = SONDAS.length ? "sem_sondas" : "com_sondas";
  const diverge = Object.entries(ancora).filter(([k, v]) => obs[k] !== v);
  saida.ancora = { publicada: ancora, observada: obs, divergencias: Object.fromEntries(diverge) };
  if (diverge.length) {
    falhou = true;
    console.error("⚠️ ÂNCORA NÃO REPRODUZIDA pelo caminho real:");
    for (const [k, v] of diverge) console.error(`   ${k}: publicada=${v} observada=${obs[k]}`);
    console.error("   Isto é achado, não bug do script: a âncora foi medida sobre um pool");
    console.error("   REIMPLEMENTADO (measurement/gap-defs.mjs). Divergir é a diferença entre");
    console.error("   ordenação e seleção — exatamente o defeito que o item 1 existe para medir.");
  }
}

if (MODO === "campo" || MODO === "dose") {
  const LOG = resolve(exigir("log-campo"));
  const briefs = readFileSync(LOG, "utf8").split("\n").filter((l) => l.trim())
    .map((l) => JSON.parse(l))
    .filter((r) => r.tag === "p2_outcome" && r.ids_controle?.length === 10);
  const limite = A.limite ? Number(A.limite) : briefs.length;
  let alvo = A["so-churn"] ? briefs.filter((r) => r.churn > 0) : briefs;
  if (A["so-ts"]) {
    alvo = alvo.filter((r) => r.ts === A["so-ts"]);
    if (alvo.length === 0) { console.error(`nenhum brief com ts=${A["so-ts"]}`); process.exit(2); }
  }
  const doses = MODO === "dose" ? (A.w ?? [2, 100000]) : [null];

  /**
   * Um serve-state só, no T_REF MÁXIMO, e poda monótona descendo pelos briefs:
   * copiar 573 mil linhas por brief seria o custo dominante e não compraria nada.
   * A ordem decrescente torna cada poda um DELETE do que já não pode ser visto.
   */
  const ordenados = alvo.slice(0, limite).slice()
    .sort((a, b) => (a.ts < b.ts ? 1 : a.ts > b.ts ? -1 : 0));
  if (ordenados.length === 0) { console.error("nenhum brief selecionado"); process.exit(2); }
  /**
   * ⚠️ Corte `rowid`: a única regra EXATA disponível, e a razão de existir.
   * `served_at` tem resolução de segundo e o cron dispara 6 agentes dentro de
   * 1-2 s, então há estados verdadeiros — "depois do cipher, antes do forge, no
   * mesmo segundo" — que NENHUM corte temporal expressa. `brief_log.id` é
   * `AUTOINCREMENT`: é a ordem de inserção que o timestamp perdeu. O brief é
   * localizado no log por (agent, segundo, os 10 chunk_id que ele serviu) e o
   * corte passa a ser `id < min(id das próprias linhas)`.
   *
   * Se a identificação falhar (brief não achado, ou ambígua), cai para o corte
   * temporal declarado e MARCA a linha — nunca finge exatidão que não tem.
   */
  /**
   * Localização do brief no `brief_log` por GRUPO de `brief_id`, não por
   * contagem. A primeira versão exigia exatamente 10 linhas em
   * (agent, segundo) — e falhava em 31 de 350 porque o `nox` dispara DUAS vezes
   * no mesmo segundo (ex. 08:52:04.242 e .948): as 20 linhas das duas casavam e
   * a contagem rejeitava. Aqui agrupa-se por `brief_id` e escolhe-se o grupo
   * cujo conjunto de `chunk_id` é IGUAL a `ids_controle` — que é a assinatura do
   * brief, e é única.
   */
  const gruposNoSegundo = vivoRO.prepare(
    `SELECT brief_id, MIN(id) mi, GROUP_CONCAT(chunk_id) ids FROM brief_log
      WHERE served_at IN (?,?,?) AND COALESCE(agent,'') = ? AND brief_id IS NOT NULL
      GROUP BY brief_id`,
  );
  const idDoBrief = (r) => {
    if (r.ids_controle.length !== 10) return null;
    const seg = (dt) => new Date(dt).toISOString().slice(0, 19).replace("T", " ");
    const t = msDe(r.ts);
    const alvo = r.ids_controle.slice().sort((a, b) => a - b).join(",");
    const cands = gruposNoSegundo.all(seg(t), seg(t + 1000), seg(t + 2000), r.agent ?? "")
      .filter((g) => String(g.ids).split(",").map(Number).sort((a, b) => a - b).join(",") === alvo);
    return cands.length === 1 ? cands[0].mi : null;
  };

  const idMaxTopo = CORTE === "rowid" ? idDoBrief(ordenados[0]) : null;
  const sv = serveStateDerivado(vivoRO, msDe(ordenados[0].ts), TMP, idMaxTopo);
  const podar = sv.db.prepare(CORTE === "inclusivo"
    ? "DELETE FROM brief_log WHERE served_at > ?"
    : CORTE === "rowid"
      ? "DELETE FROM brief_log WHERE id >= ?"
      : "DELETE FROM brief_log WHERE served_at >= ?");

  const res = [];
  for (const r of ordenados) {
    const tRefMs = msDe(r.ts);
    let idProprio = null;
    if (CORTE === "rowid") {
      idProprio = idDoBrief(r);
      if (idProprio === null) {
        res.push({ ts: r.ts, agent: r.agent, erro: "brief não localizado no brief_log por (agent, segundo, 10 ids) — corte rowid impossível" });
        continue;
      }
      podar.run(idProprio);
    } else {
      podar.run(new Date(tRefMs).toISOString().slice(0, 19).replace("T", " "));
    }
    const params = { scope: r.scope, agent: r.agent ?? undefined, n: r.ids_controle.length, format: "json" };
    for (const w of doses) {
      const dose = w ?? r.w;
      const pv = provedorEm(vivoRO, dose, tRefMs, ENV);
      let out;
      try {
        out = brief.buildBriefDiverse(corpus, params, cfgEm(tRefMs), tRefMs, sv.db, pv.fn);
      } catch (e) {
        res.push({ ts: r.ts, w: dose, erro: String(e && e.message || e) });
        continue;
      }
      const d = out.diffP2;
      const item = {
        ts: r.ts, agent: r.agent, w: dose,
        boosts_emitidos: pv.emitidos.size,
        rowid_corte: idProprio,
        churn: d ? d.churn : null,
        would_enter: d ? d.would_enter : null,
        would_leave: d ? d.would_leave : null,
      };
      if (w === null) {
        item.producao = { churn: r.churn, would_enter: r.would_enter, would_leave: r.would_leave, boosts: Object.keys(r.boost_by_id).length };
        /**
         * Fidelidade do CONTROLE é pergunta ANTERIOR à do boost: se `alt` já
         * divergir de `ids_controle`, a divergência de churn é a jusante de um
         * defeito de replay, não evidência sobre o canal. Sem esta coluna, um
         * churn que bate por coincidência (controle errado + tratado errado)
         * passaria por fidelidade.
         */
        item.ids_controle_replay = out.alt.items.map((i) => i.id);
        item.bate_controle =
          JSON.stringify(item.ids_controle_replay) === JSON.stringify(r.ids_controle);
        item.controle_producao = r.ids_controle;
        item.bate_churn = item.churn === r.churn;
        item.bate_entra = JSON.stringify((item.would_enter ?? []).slice().sort()) === JSON.stringify(r.would_enter.slice().sort());
      }
      res.push(item);
    }
  }
  sv.db.close();

  if (MODO === "campo") {
    const n = res.filter((x) => !x.erro).length;
    const okC = res.filter((x) => x.bate_churn).length;
    const okE = res.filter((x) => x.bate_entra).length;
    saida.campo = {
      log: LOG, briefs_no_log: briefs.length, replayados: n,
      erros: res.filter((x) => x.erro).length,
      bate_churn: okC, bate_entra: okE,
      bate_controle: res.filter((x) => x.bate_controle).length,
      fidelidade_churn: n ? okC / n : null,
      detalhe: res,
    };
    if (n === 0 || okC !== n) {
      falhou = true;
      console.error(`⚠️ FIDELIDADE PARCIAL: ${okC}/${n} briefs reproduzem o churn da produção.`);
      console.error("   Sem 100% aqui, nenhum número derivado deste replay sustenta N, poder ou estimando.");
    }
  } else {
    const porW = new Map();
    for (const x of res) {
      if (x.erro) continue;
      const a = porW.get(x.w) ?? { w: x.w, estados: 0, mexeu: 0, churn_total: 0, boosts: 0 };
      a.estados++; a.churn_total += x.churn ?? 0; a.boosts = Math.max(a.boosts, x.boosts_emitidos);
      if ((x.churn ?? 0) > 0) a.mexeu++;
      porW.set(x.w, a);
    }
    const tab = [...porW.values()].sort((a, b) => a.w - b.w);
    saida.dose = { log: LOG, estados: alvo.slice(0, limite).length, tabela: tab, detalhe: res };
    const absurda = tab.filter((t) => t.w >= 100000);
    const moveu = absurda.some((t) => t.mexeu > 0);
    saida.dose.controle_positivo = {
      doses_absurdas: absurda.map((t) => t.w),
      mexeu_em_algum_estado: moveu,
      veredito: absurda.length === 0 ? "NÃO EXECUTADO — passe --w 100000"
        : moveu ? "PASSA — o canal existe e responde à dose"
        : "NO-GO — dose absurda não move nada; o canal não existe",
    };
    if (absurda.length && !moveu) {
      falhou = true;
      console.error("⛔ NO-GO: w >= 100.000 não movimentou nenhum estado.");
      console.error("   O comparador de cobertura é lexicográfico e `salience` é a coordenada");
      console.error("   subordinada: dose absurda sem efeito não é ruído, é prova de que o");
      console.error("   parâmetro não está na coordenada que decide. Isto é um RESULTADO.");
    }
  }
}

console.log(JSON.stringify(saida, null, 2));
if (A.out) {
  const fs = await import("node:fs");
  fs.writeFileSync(resolve(A.out), JSON.stringify(saida, null, 2) + "\n");
}
process.exit(falhou && !A["sem-assert"] ? 1 : 0);
