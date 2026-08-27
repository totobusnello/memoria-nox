/**
 * rebuild-vec0-index.mjs — reempacota o índice vec0, in-place, com rede.
 *
 * ─── Por que existe ────────────────────────────────────────────────────────────
 * O vec0 aloca a shadow table em chunks fixos de 1024 vetores (12.582.912 B). Um
 * chunk que esvazia por completo É devolvido, mas o vazio DENTRO de chunks parciais
 * não é recuperado por nada — `VACUUM` não toca no conteúdo do blob. Medido em
 * 2026-08-28: 103 chunks para 69.261 vetores, onde 68 bastam, e a fragmentação
 * custa **33,1% da latência** de busca semântica (668,2 → 446,8 ms).
 * Ver `paper2-interventional/VEC0-REEMPACOTAMENTO-2026-08-28.md` e D77.
 *
 * ─── ⚠️ RENAME NÃO SERVE, e isso foi medido, não lido ─────────────────────────
 * `ALTER TABLE vec_x RENAME TO vec_y` **retorna sucesso** e renomeia apenas a
 * entrada da tabela virtual: as shadow tables continuam `vec_x_chunks`,
 * `vec_x_rowids`, `vec_x_vector_chunks00`. Resultado: a tabela nova é ilegível
 * (`Error preparing rowid scan: no such table`) — ou seja, RENAME **destrói** o
 * índice em silêncio. Por isso o caminho aqui é duplo-copy: copia para uma tabela
 * nova, dropa a original, recria com o nome original e copia de volta.
 *
 * ─── O que ele deliberadamente NÃO carrega ────────────────────────────────────
 * Só vetores com linha em `vec_chunk_map`. A busca semântica resolve o chunk por
 * `JOIN vec_chunk_map m ON m.vec_rowid = vc.rowid` (`src/embed.ts:339-341`), logo
 * vetor sem linha de map é **inalcançável por construção** — e ainda assim é
 * varrido pelo `MATCH` antes de o JOIN descartá-lo, custando I/O e distância para
 * nunca retornar nada. Medido: 2.074 nessa condição.
 *
 * A evidência deles NÃO é perdida: o snapshot pré-op contém o índice íntegro. É a
 * razão de `--op-audit` ser obrigatório para mutar produção.
 *
 * Uso:
 *   # ensaio (não muta):
 *   node rebuild-vec0-index.mjs --db <copia.db>
 *   # executa:
 *   node rebuild-vec0-index.mjs --db <copia.db> --executar
 *   # produção: exige o wrapper de auditoria (snapshot atômico + ops_audit)
 *   node rebuild-vec0-index.mjs --db <prod.db> --executar --op-audit --raiz <nox-mem>
 */
import D from "better-sqlite3";
import * as vec from "sqlite-vec";
import { resolve } from "node:path";

const A = {};
for (let i = 2; i < process.argv.length; i++) {
  const t = process.argv[i];
  if (!t.startsWith("--")) continue;
  const k = t.replace(/^--/, "");
  const v = process.argv[i + 1];
  if (v && !v.startsWith("--")) { A[k] = v; i++; } else A[k] = true;
}
if (!A.db) { console.error("--db obrigatório"); process.exit(2); }
const EXEC = A.executar === true;
const DIM = Number(A.dim ?? 3072);

const ms = (t0) => Number(process.hrtime.bigint() - t0) / 1e6;

function ocupacao(db, tabela) {
  const rows = db.prepare(`SELECT validity FROM ${tabela}_chunks`).all();
  let bits = 0;
  for (const r of rows) for (const b of r.validity) bits += (b.toString(2).match(/1/g) || []).length;
  return { chunks: rows.length, ocupados: bits, mb: +(rows.length * 12582912 / 1048576).toFixed(1) };
}

/** O trabalho. Fica numa função para poder rodar dentro do withOpAudit sem duplicar. */
function reempacotar(db) {
  const t0 = process.hrtime.bigint();
  const antes = ocupacao(db, "vec_chunks");
  const noIndice = db.prepare("SELECT COUNT(*) c FROM vec_chunks_rowids").get().c;
  const noMap = db.prepare("SELECT COUNT(*) c FROM vec_chunk_map").get().c;
  const semMap = Math.max(0, noIndice - noMap);

  // Só os alcançáveis. `BigInt` no rowid: better-sqlite3 liga `number` como REAL e
  // o vec0 recusa ("Only integers are allows for primary key values").
  const alcancaveis = db.prepare(
    `SELECT vc.rowid AS rid, vc.embedding AS emb
       FROM vec_chunks vc JOIN vec_chunk_map m ON m.vec_rowid = vc.rowid`,
  ).all();
  if (alcancaveis.length !== noMap) {
    throw new Error(
      `abortando: ${alcancaveis.length} vetores alcançáveis mas ${noMap} linhas de map. ` +
      `Divergência aqui significa map apontando para rowid que não existe no índice — ` +
      `estado que este script não sabe reparar.`,
    );
  }

  const copiar = (destino, linhas) => {
    const ins = db.prepare(`INSERT INTO ${destino}(rowid, embedding) VALUES (?, ?)`);
    const lote = db.transaction((xs) => { for (const x of xs) ins.run(BigInt(x.rid), x.emb); });
    for (let i = 0; i < linhas.length; i += 2000) lote(linhas.slice(i, i + 2000));
  };

  db.exec("DROP TABLE IF EXISTS vec_chunks_reb");
  db.exec(`CREATE VIRTUAL TABLE vec_chunks_reb USING vec0(embedding FLOAT[${DIM}])`);
  copiar("vec_chunks_reb", alcancaveis);
  const intermed = db.prepare("SELECT COUNT(*) c FROM vec_chunks_reb_rowids").get().c;
  if (intermed !== alcancaveis.length) {
    db.exec("DROP TABLE vec_chunks_reb");
    throw new Error(`abortando ANTES do drop: intermediária tem ${intermed} de ${alcancaveis.length}`);
  }

  // Ponto de não-retorno. A rede é o snapshot pré-op, não o rollback do SQLite:
  // DDL de tabela virtual não volta atrás de forma confiável.
  const volta = db.prepare("SELECT rowid AS rid, embedding AS emb FROM vec_chunks_reb").all();
  db.exec("DROP TABLE vec_chunks");
  db.exec(`CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding FLOAT[${DIM}])`);
  copiar("vec_chunks", volta);
  db.exec("DROP TABLE vec_chunks_reb");

  const depois = ocupacao(db, "vec_chunks");
  const finalIdx = db.prepare("SELECT COUNT(*) c FROM vec_chunks_rowids").get().c;
  if (finalIdx !== noMap) {
    throw new Error(`PÓS-OP INCONSISTENTE: índice tem ${finalIdx}, map tem ${noMap}. RESTAURAR SNAPSHOT.`);
  }
  return {
    affected_rows: finalIdx,
    notes: `vec0 repack: ${antes.chunks}->${depois.chunks} chunks, ` +
           `${antes.mb}->${depois.mb} MB, ${semMap} sem-map descartados`,
    antes, depois, no_indice_antes: noIndice, no_map: noMap,
    descartados_sem_map: semMap, duracao_s: +(ms(t0) / 1000).toFixed(1),
  };
}

const db = new D(A.db, { readonly: !EXEC });
vec.load(db);

if (!EXEC) {
  const o = ocupacao(db, "vec_chunks");
  const idx = db.prepare("SELECT COUNT(*) c FROM vec_chunks_rowids").get().c;
  const map = db.prepare("SELECT COUNT(*) c FROM vec_chunk_map").get().c;
  const nec = Math.ceil(map / 1024);
  console.log(JSON.stringify({
    ensaio: true, db: A.db, atual: o, no_indice: idx, no_map: map,
    descartaria_sem_map: idx - map, chunks_necessarios: nec,
    mb_previstos: +(nec * 12582912 / 1048576).toFixed(1),
    aviso: "nada foi mutado; passe --executar (e --op-audit em produção)",
  }, null, 2));
  db.close();
  process.exit(0);
}

let r;
if (A["op-audit"]) {
  if (!A.raiz) { console.error("--op-audit exige --raiz <nox-mem> para importar o wrapper"); process.exit(2); }
  const { withOpAudit } = await import(resolve(A.raiz, "dist", "lib", "op-audit.js"));
  // O wrapper tira o snapshot atômico em /var/backups/nox-mem/pre-op/ e registra
  // started/success/failed em `ops_audit` (append-only). É a regra 6 do CLAUDE.md,
  // e reimplementá-la aqui seria exatamente o defeito que ela existe para impedir.
  r = await withOpAudit("rebuild-vec0-index", async () => reempacotar(db));
} else {
  r = reempacotar(db);
}
console.log(JSON.stringify(r, null, 2));
db.close();
