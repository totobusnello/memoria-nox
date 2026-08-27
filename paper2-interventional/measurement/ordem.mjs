// GLM: `churn` e medida de CONJUNTO (diffBriefs faz set-difference). Se o boost
// REORDENA dentro do conjunto selecionado, churn=0 e o efeito e invisivel.
// Testa comparando as SEQUENCIAS, nao os conjuntos.
import Database from "better-sqlite3";
import { buildBriefDiverse } from "../dist/api/brief.js";
import { boostsParaCandidatos } from "../dist/paper2/brief-outcome.js";
import { DIVERSITY_DEFAULTS } from "../dist/api/brief-diversity.js";
const corpus = new Database("/var/lib/nox-mem/epochs/current.db", { readonly: true });
const live   = new Database("/var/tmp/p2-ord-ro.db", { readonly: true });
const cfg = { mode: "active", ...DIVERSITY_DEFAULTS };
const env = {
  NOX_P2_DESIGNATION: "/root/.openclaw/paper2/DESIGNATION-2026-08-26.json",
  NOX_P2_DESIGNATION_SHA256: "0a04d2d41c4e3f1c86088223ea834b79a39eaedfec4954595436d1632eda0a76",
  NOX_P2_DESIGNATION_SKIP_DRIFT: "1",
};
const AG = ["nox","lex","atlas","boris","cipher","forge",null];
const agora = Date.now();
const out = [];
for (const w of [2.0, 4.0, 7.5, 100000]) {
  for (const agent of AG) {
    const params = { scope:"global", n:10, format:"json", ...(agent?{agent}:{}) };
    const prov = (c) => boostsParaCandidatos(live, c, w, undefined, env);
    const r = buildBriefDiverse(corpus, params, cfg, agora, live, prov);
    if (!r.altBoosted || !r.alt) { out.push({w,agent,erro:"sem altBoosted"}); continue; }
    const a = r.alt.items.map(i=>i.id), b = r.altBoosted.items.map(i=>i.id);
    const mesmoConjunto = JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
    const mesmaOrdem = JSON.stringify(a) === JSON.stringify(b);
    // quantas posicoes diferem
    const posDif = a.reduce((n,x,i)=> n + (x !== b[i] ? 1 : 0), 0);
    out.push({ w, agent, churn: r.diffP2?.churn ?? null,
               mesmoConjunto, mesmaOrdem, posicoes_diferentes: posDif,
               ...(mesmaOrdem ? {} : { alt: a, boosted: b }) });
  }
}
console.log(JSON.stringify({ resultados: out }));
