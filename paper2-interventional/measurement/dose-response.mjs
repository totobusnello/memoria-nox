// Dual-compute OFFLINE da banda registrada. Read-only: buildBriefDiverse nao
// escreve em brief_log (quem escreve e handleBrief), logo isto NAO contamina
// last_served — a licao de 20:28Z.
import Database from "better-sqlite3";
import { buildBriefDiverse } from "../dist/api/brief.js";
import { boostsParaCandidatos } from "../dist/paper2/brief-outcome.js";
import { DIVERSITY_DEFAULTS } from "../dist/api/brief-diversity.js";

const DB = "/var/tmp/p2-dose-ro.db";           // copia, para nao tocar o vivo
const db = new Database(DB, { readonly: true });
const cfg = { mode: "active", ...DIVERSITY_DEFAULTS };
const AGENTES = ["nox", "lex", "atlas", "boris", "cipher", "forge", null];
const BANDA = [2.0, 4.0, 7.5];
const N = Number(process.argv[2] ?? 10);
const env = {
  NOX_P2_DESIGNATION: "/root/.openclaw/paper2/DESIGNATION-2026-08-26.json",
  NOX_P2_DESIGNATION_SHA256: "0a04d2d41c4e3f1c86088223ea834b79a39eaedfec4954595436d1632eda0a76",
  NOX_P2_DESIGNATION_SKIP_DRIFT: "1",
};
const agora = Date.now();
const out = [];
for (const w of BANDA) {
  for (const agent of AGENTES) {
    const params = { scope: "global", n: N, format: "json", ...(agent ? { agent } : {}) };
    const prov = (cands) => boostsParaCandidatos(db, cands, w, undefined, env);
    const r = buildBriefDiverse(db, params, cfg, agora, db, prov);
    out.push({
      w, agent, n: N,
      churn: r.diffP2 ? r.diffP2.churn : null,
      would_enter: r.diffP2 ? r.diffP2.would_enter : null,
      would_leave: r.diffP2 ? r.diffP2.would_leave : null,
    });
  }
}
console.log(JSON.stringify({ n: N, resultados: out }));
