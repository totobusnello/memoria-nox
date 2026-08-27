#!/usr/bin/env node
/**
 * gatilho-composicao.mjs — item 7(b) do PROTOCOL-CALIBRATION-2026-08-27.
 *
 * Vigia a COMPOSIÇÃO DO CANAL de tratamento. Este gatilho não existia em nenhum
 * documento antes de 27/08, e é a ameaça mais urgente identificada até aqui:
 * é a única que muda a escala de dose **durante** o estudo, em silêncio.
 *
 * ─── O que ele vigia, e por que isso importa ────────────────────────────────
 *
 * O pool de cobertura é `interleaveFresh(agentFresh, globalFresh)`. Em
 * `2026-08-26 20:35Z` medimos `agentFresh` **vazio** para os 6 agentes — não por
 * os patterns não casarem, mas por IDADE: 265 (nox), 6.001 (cipher) e 3.011
 * (atlas) chunks de `sessions/<agente>/%` passavam o piso de `importance`, e
 * ZERO passavam a janela de `freshMaxAgeDays = 7`.
 *
 * Logo `interleaveFresh([], global) === global`, e todo o canal é o sub-pool
 * global (108 candidatos de `memory/entities/%` + `memory/lessons.md`). Toda a
 * calibração de dose de 27/08 — a distribuição de `w_min`, o teto de 17/350 —
 * vale NESSE regime.
 *
 * Uma rajada de sessões faz `agentFresh` reaparecer, `interleaveFresh` deixa de
 * ser função-zero, e a escala muda sob os pés do estudo. Sem este gatilho, isso
 * é invisível: nenhum log, nenhum alarme, nenhuma linha no morning report.
 *
 * ─── Duas regras de construção, herdadas de erro já cometido ────────────────
 *
 * 1. **NÃO sonda `/api/brief`.** Item 2 do protocolo, e a razão é dura: o
 *    endpoint ESCREVE em `brief_log` o estado que mede. Este gatilho é `SELECT`
 *    sobre o corpus, ponto.
 * 2. **Os limiares vêm de `DIVERSITY_DEFAULTS` no `dist`, não digitados aqui.**
 *    Um gatilho com 0,7 e 7 hardcoded fica silenciosamente errado no dia em que
 *    alguém mexer no `cfg` — e "gatilho que vigia a grandeza errada" é
 *    exatamente o defeito que o item 7 original tinha.
 *
 * Saída: uma linha `GREEN|YELLOW|RED …` em stdout e, com `--status <arquivo>`,
 * a mesma linha no arquivo que o `morning-report.sh` lê. Exit 0 sempre — o
 * status vive na linha, não no código de saída, para o cron não virar alarme.
 */

import Database from "better-sqlite3";
import { readFileSync, writeFileSync, appendFileSync } from "node:fs";
import { join, resolve } from "node:path";

function args(argv) {
  const o = {};
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i].replace(/^--/, "");
    o[k] = argv[++i];
  }
  return o;
}
const A = args(process.argv);
const exigir = (k) => {
  if (!A[k]) { console.error(`FALTA --${k}`); process.exit(2); }
  return A[k];
};

const RAIZ = resolve(exigir("raiz"));
const CORPUS = resolve(exigir("corpus"));
const AGENTES = exigir("agentes").split(",").map((x) => x.trim()).filter(Boolean);

const brief = await import(join(RAIZ, "dist", "api", "brief.js"));
const div = await import(join(RAIZ, "dist", "api", "brief-diversity.js"));
const cfg = div.DIVERSITY_DEFAULTS;

/**
 * O predicado tem de ser o MESMO de `src/api/brief.ts:641-647`. Ele é replicado
 * aqui (não há como chamar só o `WHERE`), e por isso o fonte é conferido: se as
 * cláusulas mudarem, este gatilho aborta em vez de vigiar o predicado velho.
 */
const FONTE = readFileSync(join(RAIZ, "src", "api", "brief.ts"), "utf8");
const CLAUSULAS = [
  "(COALESCE(importance, 0) >= ? OR COALESCE(pain, 0) >= ?)",
  "julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?",
];
for (const c of CLAUSULAS) {
  if (!FONTE.includes(c)) {
    console.error(`RED predicado-do-fresh-mudou clausula_ausente=${JSON.stringify(c)}`);
    process.exit(2);
  }
}

const corpus = new Database(CORPUS, { readonly: true, fileMustExist: true });
const q = corpus.prepare(
  `SELECT COUNT(*) n FROM chunks
    WHERE source_file LIKE ? ESCAPE '\\'
      AND (COALESCE(importance, 0) >= ? OR COALESCE(pain, 0) >= ?)
      AND julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?`,
);
const qSemIdade = corpus.prepare(
  `SELECT COUNT(*) n FROM chunks
    WHERE source_file LIKE ? ESCAPE '\\'
      AND (COALESCE(importance, 0) >= ? OR COALESCE(pain, 0) >= ?)`,
);

const porAgente = {};
let elegiveis = 0;
for (const ag of AGENTES) {
  const pats = brief.scopePatterns("global", ag);
  let n = 0, semIdade = 0;
  for (const p of pats) {
    n += q.get(p, cfg.freshMinImp, cfg.freshMinPain, cfg.freshMaxAgeDays).n;
    semIdade += qSemIdade.get(p, cfg.freshMinImp, cfg.freshMinPain).n;
  }
  porAgente[ag] = { patterns: pats, elegiveis: n, passam_piso_sem_idade: semIdade };
  elegiveis += n;
}

/**
 * `RED` no primeiro chunk elegível, sem faixa amarela. A escala de dose de
 * 27/08 foi calibrada com `agentFresh` vazio; um único candidato entrando já
 * muda `interleaveFresh` de função-zero para intercalação real, e o `w_min` de
 * qualquer estado afetado deixa de valer. Isto não é ruído a tolerar — é a
 * premissa da calibração caindo.
 */
const estado = elegiveis > 0 ? "RED" : "GREEN";
const ts = new Date().toISOString();
const linha =
  `${estado} p2-composicao-do-canal agent_fresh_elegiveis=${elegiveis} ` +
  `piso_imp=${cfg.freshMinImp} piso_pain=${cfg.freshMinPain} janela_dias=${cfg.freshMaxAgeDays} ` +
  `por_agente=${AGENTES.map((a) => `${a}:${porAgente[a].elegiveis}`).join(",")} ts=${ts}` +
  (estado === "RED"
    ? " ACAO=a escala de dose de 27/08 pressupoe agentFresh vazio; remedir w_min antes de qualquer inferencia"
    : "");

console.log(linha);
if (A.status) writeFileSync(resolve(A.status), linha + "\n");
if (A.ndjson) {
  appendFileSync(resolve(A.ndjson), JSON.stringify({
    ts, tag: "p2_gatilho_composicao", estado, elegiveis,
    cfg: { freshMinImp: cfg.freshMinImp, freshMinPain: cfg.freshMinPain, freshMaxAgeDays: cfg.freshMaxAgeDays },
    corpus: CORPUS, por_agente: porAgente,
  }) + "\n");
}
