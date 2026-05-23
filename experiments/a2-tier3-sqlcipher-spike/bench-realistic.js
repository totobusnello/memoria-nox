// More realistic bench: amortize KDF, measure steady-state read p50/p95
const Database = require('better-sqlite3-multiple-ciphers');
const path = require('path');
const fs = require('fs');

function bench(label, dbFactory) {
  const N_WRITE = 5000;
  const N_READ = 5000;
  const dbPath = path.join(__dirname, `bench-${label}.db`);
  if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

  const db = dbFactory(dbPath);
  db.exec("CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT, embedding BLOB)");
  db.exec("CREATE VIRTUAL TABLE chunks_fts USING fts5(content, content='chunks', content_rowid='id')");

  // bulk insert with transaction
  const ins = db.prepare("INSERT INTO chunks (content, embedding) VALUES (?, ?)");
  const buf = Buffer.alloc(3072 * 4); // simulate 3072d float32 embedding
  buf.writeFloatLE(0.123, 0);

  const txWrite = db.transaction((n) => {
    for (let i = 0; i < n; i++) {
      ins.run('chunk content number ' + i + ' with realistic length text for tokens', buf);
    }
  });
  const tW0 = process.hrtime.bigint();
  txWrite(N_WRITE);
  const tW1 = process.hrtime.bigint();
  db.exec("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')");
  const tW2 = process.hrtime.bigint();

  // read benchmark — point lookups
  const sel = db.prepare("SELECT content FROM chunks WHERE id = ?");
  const samples = [];
  for (let i = 0; i < N_READ; i++) {
    const id = 1 + Math.floor(Math.random() * N_WRITE);
    const t0 = process.hrtime.bigint();
    sel.get(id);
    const t1 = process.hrtime.bigint();
    samples.push(Number(t1 - t0));
  }

  // FTS5 query benchmark
  const ftsQ = db.prepare("SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ?");
  const ftsSamples = [];
  for (let i = 0; i < 500; i++) {
    const t0 = process.hrtime.bigint();
    ftsQ.all('content number ' + (i % 50));
    const t1 = process.hrtime.bigint();
    ftsSamples.push(Number(t1 - t0));
  }

  samples.sort((a, b) => a - b);
  ftsSamples.sort((a, b) => a - b);
  const pct = (arr, p) => arr[Math.floor(arr.length * p)];

  const result = {
    label,
    write_total_ms: Number(tW1 - tW0) / 1e6,
    fts_rebuild_ms: Number(tW2 - tW1) / 1e6,
    read_p50_us: pct(samples, 0.5) / 1000,
    read_p95_us: pct(samples, 0.95) / 1000,
    read_p99_us: pct(samples, 0.99) / 1000,
    fts_p50_ms: pct(ftsSamples, 0.5) / 1e6,
    fts_p95_ms: pct(ftsSamples, 0.95) / 1e6,
  };
  db.close();
  return result;
}

const vanilla = bench('vanilla', (p) => new Database(p));
const cipher = bench('cipher', (p) => {
  const d = new Database(p);
  d.pragma("cipher='sqlcipher'");
  d.pragma("legacy=4");
  d.pragma("key='spike-pass-1'");
  return d;
});

const overhead = {
  write: ((cipher.write_total_ms / vanilla.write_total_ms - 1) * 100).toFixed(1) + '%',
  fts_rebuild: ((cipher.fts_rebuild_ms / vanilla.fts_rebuild_ms - 1) * 100).toFixed(1) + '%',
  read_p50: ((cipher.read_p50_us / vanilla.read_p50_us - 1) * 100).toFixed(1) + '%',
  read_p95: ((cipher.read_p95_us / vanilla.read_p95_us - 1) * 100).toFixed(1) + '%',
  fts_p50: ((cipher.fts_p50_ms / vanilla.fts_p50_ms - 1) * 100).toFixed(1) + '%',
};

console.log(JSON.stringify({ vanilla, cipher, overhead }, null, 2));
