/**
 * teto-pool-principal.mjs — o boost teria alcance no POOL PRINCIPAL?
 *
 * Medição de viabilidade da opção B da revisão de desenho (2026-08-30). O teto do
 * canal de cobertura é 4,86% dos briefs sob dose infinita; a pergunta é se o outro
 * ordenador — os 8 slots do pool principal — é mais permeável.
 *
 * ⚠️ ISTO É UM CONTRAFACTUAL SOBRE CÓDIGO QUE NÃO EXISTE. A produção aplica o boost
 * apenas no ranking de cobertura; não há pipeline real para replicar. O que se faz
 * aqui é usar o pool e a salience REAIS (query do código + `calculateSalience` do
 * dist) e perguntar quanto de boost seria preciso para um designado entrar no top-N.
 * É modelo do ORDENADOR, não reimplementação do pipeline — a distinção importa, e a
 * conclusão só é válida na direção "se nem assim alcança, não alcança".
 */
import Database from "better-sqlite3";
import { join } from "node:path";
import { readFileSync } from "node:fs";

const A = {};
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i].startsWith("--")) A[process.argv[i].slice(2)] = process.argv[++i];
}
const DIST = A.dist || "/root/.openclaw/workspace/tools/nox-mem/dist";
const sal = await import(join(DIST, "salience.js"));
const calc = sal.calculateSalience;
if (typeof calc !== "function") { console.error("calculateSalience ausente do dist"); process.exit(2); }

const db = new Database(A.corpus, { readonly: true });
const designados = JSON.parse(readFileSync(A.designacao, "utf8"));
const ids = new Set((designados.designados || designados.ids || Object.values(designados).flat())
  .filter((x) => typeof x === "number"));
if (!ids.size) { console.error("nenhum id designado lido de --designacao"); process.exit(2); }

const CANDIDATE_POOL = 500, MAIN_SLOTS = 8;
const estados = JSON.parse(readFileSync(A.estados, "utf8"));

const linhas = [];
for (const ts of estados) {
  const nowMs = Date.parse(ts);
  const rows = db.prepare(
    `SELECT id, source_file, chunk_text, chunk_type, source_type, tier,
            pain, importance, retention_days, source_date, created_at,
            updated_at, last_accessed_at, access_count
       FROM chunks
      ORDER BY (0.55 * COALESCE(importance, 0.5)
              + 0.10 * COALESCE(pain, 0.2)
              + CASE WHEN COALESCE(access_count, 0) > 0 THEN 0.1 ELSE 0 END) DESC,
               updated_at DESC
      LIMIT ${CANDIDATE_POOL}`).all();
  const scored = rows.map((r) => ({ id: r.id, s: calc(r, nowMs) }))
                     .sort((a, b) => b.s - a.s);
  if (scored.length < MAIN_SLOTS) continue;
  const corte = scored[MAIN_SLOTS - 1].s;          // salience do 8º
  // designados presentes no pool de candidatos
  const des = scored.map((x, i) => ({ ...x, pos: i })).filter((x) => ids.has(x.id));
  const melhor = des.length ? des[0] : null;       // o mais bem posicionado
  linhas.push({
    ts, corte,
    designados_no_pool: des.length,
    melhor_pos: melhor ? melhor.pos : null,
    melhor_salience: melhor ? melhor.s : null,
    boost_necessario: melhor ? Math.max(0, corte - melhor.s) : null,
    ja_no_top: melhor ? melhor.pos < MAIN_SLOTS : false,
  });
}
console.log(JSON.stringify({
  gerado_por: "teto-pool-principal.mjs",
  contrafactual: "o codigo NAO aplica boost no pool principal; isto modela o ORDENADOR",
  corpus: A.corpus, estados: linhas.length, slots_principais: MAIN_SLOTS,
  detalhe: linhas,
}, null, 2));
