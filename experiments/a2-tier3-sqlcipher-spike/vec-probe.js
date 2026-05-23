// Real sqlite-vec load + query on SQLCipher-encrypted DB
const Database = require('better-sqlite3-multiple-ciphers');
const sqliteVec = require('sqlite-vec');
const path = require('path');
const fs = require('fs');

const dbPath = path.join(__dirname, 'vec-probe.db');
if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db = new Database(dbPath);
db.pragma("cipher='sqlcipher'");
db.pragma("legacy=4");
db.pragma("key='spike-pass-1'");
db.defaultSafeIntegers(true);  // force BigInt return

console.log('Loading sqlite-vec...');
try {
  sqliteVec.load(db);
  console.log('PROBE_VEC_LOAD=ok');
} catch (e) {
  console.log('PROBE_VEC_LOAD_ERR=' + e.message);
  process.exit(1);
}

const ver = db.prepare("SELECT vec_version() AS v").get();
console.log('PROBE_VEC_VERSION=' + ver.v);

db.exec("CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding float[8])");
console.log('PROBE_VEC_TABLE=ok');

// Use BigInt for rowid (vec0 requires strict INTEGER)
const ins = db.prepare("INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)");
const vectors = [
  [1n, new Float32Array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])],
  [2n, new Float32Array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2])],
  [3n, new Float32Array([0.0, 0.1, 0.0, 0.1, 0.0, 0.1, 0.0, 0.1])],
  [4n, new Float32Array([0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85])],
];
for (const [id, v] of vectors) {
  ins.run(id, Buffer.from(v.buffer));
}
console.log('PROBE_VEC_INSERT=' + vectors.length);

const q = new Float32Array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]);
const rows = db.prepare(`
  SELECT rowid, distance FROM vec_chunks
  WHERE embedding MATCH ?
  ORDER BY distance
  LIMIT 3
`).all(Buffer.from(q.buffer));
console.log('PROBE_VEC_SEARCH=' + rows.length + ' rows');
console.log('PROBE_VEC_TOP1_ROWID=' + rows[0].rowid);
console.log('PROBE_VEC_TOP1_DIST=' + rows[0].distance);

db.close();

const db2 = new Database(dbPath);
db2.pragma("cipher='sqlcipher'");
db2.pragma("legacy=4");
db2.pragma("key='spike-pass-1'");
db2.defaultSafeIntegers(true);
sqliteVec.load(db2);
const reopenCount = db2.prepare("SELECT count(*) AS n FROM vec_chunks").get().n;
console.log('PROBE_VEC_REOPEN_COUNT=' + reopenCount);

// VACUUM INTO snapshot WITH vec0 data
const snapPath = path.join(__dirname, 'vec-snap.db');
if (fs.existsSync(snapPath)) fs.unlinkSync(snapPath);
db2.exec(`VACUUM INTO '${snapPath}'`);
console.log('PROBE_VEC_SNAP_VACUUM=ok');
db2.close();

// Reopen snap, verify vec table came over
const db3 = new Database(snapPath);
db3.pragma("cipher='sqlcipher'");
db3.pragma("legacy=4");
db3.pragma("key='spike-pass-1'");
db3.defaultSafeIntegers(true);
sqliteVec.load(db3);
try {
  const c = db3.prepare("SELECT count(*) AS n FROM vec_chunks").get().n;
  console.log('PROBE_VEC_SNAP_COUNT=' + c);
} catch (e) {
  console.log('PROBE_VEC_SNAP_ERR=' + e.message);
}
db3.close();

console.log('ALL_VEC_PROBES_PASSED');
