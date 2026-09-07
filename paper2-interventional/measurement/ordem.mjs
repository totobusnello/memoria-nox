// GLM: `churn` e medida de CONJUNTO (diffBriefs faz set-difference). Se o boost
// REORDENA dentro do conjunto selecionado, churn=0 e o efeito e invisivel.
// Testa comparando as SEQUENCIAS, nao os conjuntos.
import Database from "better-sqlite3";
import { buildBriefDiverse } from "../dist/api/brief.js";
import { boostsParaCandidatos } from "../dist/paper2/brief-outcome.js";
import { DIVERSITY_DEFAULTS } from "../dist/api/brief-diversity.js";
/**
 * ⚠️ NÃO ler `epochs/current.db` num script que produz artefato pinado. `current.db`
 * é **symlink reapontado às 06:01** e `epochs/` retém 3 dias (`nox-epoch.log`
 * registra `"podados":1` por dia), então:
 *
 *   - pinar `current.db` é pino **vazio** — o caminho sobrevive, o conteúdo muda;
 *   - pinar o alvo datado é pino que **pendura** em 3 dias.
 *
 * Medido em 2026-09-07: **30** arquivos deste repositório pinam corpora de epoch que
 * **já não existem** (27 no `e20260826T060003Z.db`, 1 no `e20260827`, 2 no
 * `e20260830`), e a busca pelo de 26/08 foi esgotada — por tamanho exato sem
 * `-xdev`, por nome nos três mounts, e por censo de todo `.db` acima de 1 GB.
 * É a mesma frase que o texto do depósito já confessa sobre corpus perdido por
 * identificador, recorrendo em escala. Ver `DEVIATIONS-FOR-PAPER.md` §10.6.
 */
const CORPUS = process.env.NOX_P2_ORD_CORPUS
  ?? "/var/lib/nox-mem/p2/corpus/e20260907T060001Z.db";
const corpus = new Database(CORPUS, { readonly: true });
/**
 * ⚠️ Este script é o item 115 do `deposit/paperA/MANIFEST.json` — é publicado, e
 * um terceiro deveria conseguir rodá-lo. Até 2026-09-07 ele lia um insumo de 1,6G
 * em `/var/tmp`: fora do depósito (o MANIFEST não contém nenhum `.db`) e num
 * diretório sujeito a faxina de disco. O arquivo quase foi apagado num varrimento
 * de espaço em 2026-09-07.
 *
 * E nesse mesmo dia ele deixou de ser recriável: o watcher foi consertado às
 * 14:06:13Z e o corpus do `main` descongelou (67187 → 67224 chunks), então
 * "recriar a partir do main" já não reproduz o snapshot de 2026-08-26 que sustenta
 * a alegação de `README.md:69` — 28 casos, 0 com ordem diferente, que é o que
 * refuta o canal de reordenação.
 *
 * Movido para `/var/lib/nox-mem/p2/corpus/`, que não é varrido, e o caminho ficou
 * parametrizável para um terceiro apontar para a própria cópia.
 * Ver `DEVIATIONS-FOR-PAPER.md` §10.6.
 */
const LIVE = process.env.NOX_P2_ORD_LIVE
  ?? "/var/lib/nox-mem/p2/corpus/p2-ord-ro-2026-08-26.db";
const live   = new Database(LIVE, { readonly: true });
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
