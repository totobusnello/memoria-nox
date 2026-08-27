// Dual-compute OFFLINE, agora no caminho que prod REALMENTE usa:
// corpus = snapshot de epoch (P2S1 active), serve-state = DB vivo.
// A primeira versao usou o vivo como os dois e o controle positivo (w=100000)
// deu churn 0 — foi o harness, nao o mecanismo.
import Database from "better-sqlite3";
import { buildBriefDiverse } from "../dist/api/brief.js";
import { boostsParaCandidatos } from "../dist/paper2/brief-outcome.js";
import { DIVERSITY_DEFAULTS } from "../dist/api/brief-diversity.js";
const corpus = new Database("/var/lib/nox-mem/epochs/current.db", { readonly: true });
const live   = new Database("/var/tmp/p2-dose-ro.db", { readonly: true });
const cfg = { mode: "active", ...DIVERSITY_DEFAULTS };
const env = {
  NOX_P2_DESIGNATION: "/root/.openclaw/paper2/DESIGNATION-2026-08-26.json",
  NOX_P2_DESIGNATION_SHA256: "0a04d2d41c4e3f1c86088223ea834b79a39eaedfec4954595436d1632eda0a76",
  NOX_P2_DESIGNATION_SKIP_DRIFT: "1",
};
const AGENTES = ["nox", "lex", "atlas", "boris", "cipher", "forge", null];
const DOSES = JSON.parse(process.argv[2] ?? "[2.0,4.0,7.5]");
const agora = Date.now();
const out = [];
for (const w of DOSES) {
  for (const agent of AGENTES) {
    let chamadas = 0, boostsEmitidos = 0;
    const prov = (cands) => {
      chamadas++;
      const m = boostsParaCandidatos(live, cands, w, undefined, env);
      boostsEmitidos += m.size;
      return m;
    };
    const params = { scope: "global", n: 10, format: "json", ...(agent ? { agent } : {}) };
    const r = buildBriefDiverse(corpus, params, cfg, agora, live, prov);
    out.push({ w, agent, chamadas, boostsEmitidos,
               churn: r.diffP2?.churn ?? null,
               enter: r.diffP2?.would_enter ?? null,
               leave: r.diffP2?.would_leave ?? null });
  }
}
console.log(JSON.stringify({ resultados: out }));
