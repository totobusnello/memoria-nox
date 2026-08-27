/**
 * bench-vec0-reempacotamento.mjs — o reempacotamento do índice vec0 acelera a busca?
 *
 * ─── Por que existe ────────────────────────────────────────────────────────────
 * A shadow table do vec0 aloca em chunks fixos de 1024 vetores (12.582.912 B). No
 * nox-mem, 34% dos slots estão vazios: 103 chunks alocados para 69.261 vetores,
 * quando 68 bastariam. A hipótese — plausível e NÃO medida — é que o full scan do
 * vec0 leia 1.236 MB onde 816 bastariam, ou seja −34% de I/O por busca.
 *
 * "Plausível" não é resultado. Slot vazio tem bit zerado no `validity` e não custa
 * cálculo de distância; a pergunta aberta é se os BYTES ainda são lidos. Isto mede.
 *
 * ─── Desenho, e os confundidores que ele fecha ────────────────────────────────
 * 1. as DUAS tabelas vivem no MESMO arquivo — mesma page cache, mesmo volume,
 *    mesmo processo. Comparar dois arquivos mediria qual deles o SO cacheou;
 * 2. A/B INTERCALADO por sonda: deriva de carga (a VPS é compartilhada) afeta os
 *    dois braços igualmente em vez de premiar quem rodou no minuto calmo;
 * 3. passada de aquecimento DESCARTADA: o primeiro KNN medido custou 1.356 ms
 *    contra ~650 ms nos seguintes;
 * 4. mediana, não média — uma pausa de scheduler contamina média;
 * 5. e roda sobre CÓPIA em /var/tmp. Nunca no banco vivo.
 *
 * ⚠️ Sobre a sonda: o vec0 faz FULL SCAN, então o custo não depende de QUAL vetor
 * se consulta — depende de quantos chunks são varridos. Por isso sondas amostradas
 * do próprio corpus são adequadas aqui, e a ausência de `query_text` recente (a
 * telemetria por chunk morreu em 19/05) não limita ESTA medição. Limitaria uma
 * medição de qualidade de retrieval, que não é esta.
 *
 * Uso:
 *   node bench-vec0-reempacotamento.mjs --db <copia.db> [--sondas 12] [--reps 5]
 */
import D from "better-sqlite3";
import * as vec from "sqlite-vec";

const A = {};
for (let i = 2; i < process.argv.length; i += 2) {
  A[process.argv[i].replace(/^--/, "")] = process.argv[i + 1];
}
if (!A.db) { console.error("--db obrigatório (uma CÓPIA, nunca o vivo)"); process.exit(2); }
if (/\/nox-mem\/nox-mem\.db$/.test(A.db)) {
  console.error("⛔ isso é o caminho do banco VIVO. Este script escreve (cria tabela). Use uma cópia.");
  process.exit(2);
}
const N_SONDAS = Number(A.sondas ?? 12);
const REPS = Number(A.reps ?? 5);
const K = Number(A.k ?? 10);

const db = new D(A.db);
vec.load(db);

const ms = (t0) => Number(process.hrtime.bigint() - t0) / 1e6;
const mediana = (xs) => {
  const s = xs.slice().sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const ocupacao = (tabela) => {
  const rows = db.prepare(`SELECT validity FROM ${tabela}_chunks`).all();
  let bits = 0;
  for (const r of rows) for (const b of r.validity) bits += (b.toString(2).match(/1/g) || []).length;
  return { chunks: rows.length, ocupados: bits, alocados: rows.length * 1024,
           mb: +(rows.length * 12582912 / 1048576).toFixed(1) };
};

console.log("ANTES  vec_chunks :", JSON.stringify(ocupacao("vec_chunks")));

// ─── reempacota: INSERT sequencial preenche cada chunk antes de abrir o próximo ──
db.exec("DROP TABLE IF EXISTS vec_packed");
db.exec("CREATE VIRTUAL TABLE vec_packed USING vec0(embedding FLOAT[3072])");
const t0 = process.hrtime.bigint();
const ins = db.prepare("INSERT INTO vec_packed(rowid, embedding) VALUES (?, ?)");
/**
 * ⚠️ `BigInt`, e não o `number` cru: o better-sqlite3 liga `number` como REAL, e o
 * vec0 recusa com "Only integers are allows for primary key values". Testado: cru,
 * `Number()` e `Math.trunc()` todos falham; só `BigInt` passa. Mesma família da
 * lição "SQLite TEXT affinity coage INTEGER — usar CAST(? AS INTEGER)".
 */
const lote = db.transaction((rows) => {
  for (const r of rows) ins.run(BigInt(r.rowid), r.embedding);
});
const todos = db.prepare("SELECT rowid, embedding FROM vec_chunks").all();
for (let i = 0; i < todos.length; i += 2000) lote(todos.slice(i, i + 2000));
console.log(`reempacotado: ${todos.length} vetores em ${(ms(t0) / 1000).toFixed(1)} s`);
console.log("DEPOIS vec_packed:", JSON.stringify(ocupacao("vec_packed")));

// ─── sondas amostradas do próprio corpus ──────────────────────────────────────
const passo = Math.max(1, Math.floor(todos.length / N_SONDAS));
const sondas = [];
for (let i = 0; i < todos.length && sondas.length < N_SONDAS; i += passo) sondas.push(todos[i].embedding);

const qA = db.prepare(`SELECT rowid FROM vec_chunks WHERE embedding MATCH ? ORDER BY distance LIMIT ${K}`);
const qB = db.prepare(`SELECT rowid FROM vec_packed WHERE embedding MATCH ? ORDER BY distance LIMIT ${K}`);

// aquecimento descartado
for (const s of sondas.slice(0, 2)) { qA.all(s); qB.all(s); }

const tA = [], tB = [];
for (let r = 0; r < REPS; r++) {
  for (const s of sondas) {
    // ordem alternada por repetição: nem sempre A primeiro
    if (r % 2 === 0) {
      let t = process.hrtime.bigint(); qA.all(s); tA.push(ms(t));
      t = process.hrtime.bigint(); qB.all(s); tB.push(ms(t));
    } else {
      let t = process.hrtime.bigint(); qB.all(s); tB.push(ms(t));
      t = process.hrtime.bigint(); qA.all(s); tA.push(ms(t));
    }
  }
}

const mA = mediana(tA), mB = mediana(tB);
console.log(`\nfragmentado (vec_chunks): mediana ${mA.toFixed(1)} ms  (n=${tA.length}, min ${Math.min(...tA).toFixed(1)}, max ${Math.max(...tA).toFixed(1)})`);
console.log(`reempacotado (vec_packed): mediana ${mB.toFixed(1)} ms  (n=${tB.length}, min ${Math.min(...tB).toFixed(1)}, max ${Math.max(...tB).toFixed(1)})`);
console.log(`\nganho = ${((1 - mB / mA) * 100).toFixed(1)}%   (hipótese do tamanho previa ~34%)`);

// mesma resposta? ganho que muda o resultado não é ganho.
const iguais = sondas.filter((s) => JSON.stringify(qA.all(s)) === JSON.stringify(qB.all(s))).length;
console.log(`sondas com resposta IDÊNTICA nos dois: ${iguais}/${sondas.length}`);
db.close();
