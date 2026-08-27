import Database from "better-sqlite3";
import { designadosGlobais, impressaoDoConjunto } from "../dist/paper2/brief-outcome.js";
const seed = process.argv[2];
const db = new Database("/root/.openclaw/workspace/tools/nox-mem/nox-mem.db", { readonly: true });
const d = designadosGlobais(db, seed);
const ordenado = {};
for (const k of [...d.keys()].sort()) ordenado[k] = d.get(k);
console.log(JSON.stringify({
  grupos: d.size,
  designados: ordenado,
  designados_ids: [...d.values()].sort((a, b) => a - b),
  sha256_do_conjunto: impressaoDoConjunto(d),
}, null, 2));
