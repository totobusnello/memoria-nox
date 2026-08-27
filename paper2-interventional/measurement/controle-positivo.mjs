import Database from "better-sqlite3";
import { buildBriefDiverse } from "../dist/api/brief.js";
import { boostsParaCandidatos } from "../dist/paper2/brief-outcome.js";
import { DIVERSITY_DEFAULTS } from "../dist/api/brief-diversity.js";
const db = new Database("/var/tmp/p2-dose-ro.db", { readonly: true });
const cfg = { mode: "active", ...DIVERSITY_DEFAULTS };
const env = {
  NOX_P2_DESIGNATION: "/root/.openclaw/paper2/DESIGNATION-2026-08-26.json",
  NOX_P2_DESIGNATION_SHA256: "0a04d2d41c4e3f1c86088223ea834b79a39eaedfec4954595436d1632eda0a76",
  NOX_P2_DESIGNATION_SKIP_DRIFT: "1",
};
// 1. O provedor devolve mapa NAO-vazio neste harness?
const amostra = db.prepare(
  "SELECT DISTINCT chunk_id AS id FROM p2_verdict WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')"
).all();
const m = boostsParaCandidatos(db, amostra, 2.0, undefined, env);
console.log("boosts_com_w2:", m.size, "primeiros:", [...m.entries()].slice(0,3));
// 2. O provedor e CHAMADO durante o buildBriefDiverse?
let chamadas = 0, totalCands = 0, boostsVistos = 0;
const espiao = (w) => (cands) => {
  chamadas++; totalCands += cands.length;
  const r = boostsParaCandidatos(db, cands, w, undefined, env);
  boostsVistos += r.size;
  return r;
};
// 3. Doses absurdas — se nem 1000 desloca, o harness esta quebrado
for (const w of [2.0, 100, 1000, 100000]) {
  chamadas = 0; totalCands = 0; boostsVistos = 0;
  const r = buildBriefDiverse(db, { scope: "global", n: 10, format: "json" },
                              cfg, Date.now(), db, espiao(w));
  console.log(`w=${w}: chamadas=${chamadas} cands_vistos=${totalCands} boosts_emitidos=${boostsVistos} churn=${r.diffP2?.churn} enter=${JSON.stringify(r.diffP2?.would_enter)}`);
}
