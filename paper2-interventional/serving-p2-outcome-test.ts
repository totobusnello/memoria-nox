// Paper 2, componente 2 — dual-compute do boost de desfecho.
// Run: cd tools/nox-mem && npx tsc && node --test dist/__tests__/p2-outcome.test.js

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createHash } from "node:crypto";
import Database from "better-sqlite3";
import {
  buildBriefDiverse,
  ensureBriefLog,
  _resetBriefLogMemo,
  type BriefDb,
} from "../api/brief.js";
import { DIVERSITY_DEFAULTS, type DiversityConfig } from "../api/brief-diversity.js";
import {
  boostsParaCandidatos,
  carregarDesignados,
  chaveDeDesignacao,
  designadosGlobais,
  impressaoDoConjunto,
  doseDeShadow,
  epochInicioISO,
  parseP2Mode,
  resolverBraco,
  logarDecisaoDeServing,
  epochInicioMs,
  _resetAvisoDeLog,
  _resetAvisoDeDesignacao,
  P2_DELTA_CUT,
} from "../paper2/brief-outcome.js";

const CFG: DiversityConfig = { mode: "active", ...DIVERSITY_DEFAULTS, freshSlots: 1 };

function makeDb(): BriefDb & InstanceType<typeof Database> {
  const db = new Database(":memory:");
  db.exec(`
    CREATE TABLE chunks (
      id INTEGER PRIMARY KEY,
      source_file TEXT NOT NULL,
      chunk_text TEXT NOT NULL,
      chunk_type TEXT NOT NULL DEFAULT 'other',
      source_type TEXT,
      tier TEXT DEFAULT 'peripheral',
      pain REAL DEFAULT 0.2,
      importance REAL DEFAULT 0.5,
      retention_days INTEGER,
      source_date TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now')),
      last_accessed_at TEXT,
      access_count INTEGER DEFAULT 0
    );
  `);
  _resetBriefLogMemo();
  ensureBriefLog(db as unknown as BriefDb);
  return db as unknown as BriefDb & InstanceType<typeof Database>;
}

function comP2Verdict(db: InstanceType<typeof Database>): void {
  db.exec(`
    CREATE TABLE p2_verdict (
      episode_id  TEXT PRIMARY KEY,
      severity    TEXT NOT NULL,
      sig_primary TEXT NOT NULL,
      chunk_id    INTEGER
    );
  `);
}

/**
 * Incumbente e chunk do estudo (S1), ambos nunca-servidos e elegiveis ao pool de
 * cobertura, mais preenchimento para que os slots PRINCIPAIS estejam ocupados.
 *
 * Dois cuidados que a primeira versao deste cenario errou:
 *  - sem preenchimento e com `n` folgado os dois cabem no brief e nao ha disputa;
 *  - `pain >= painFloor` (0.9) torna o item PINNED, imune a despejo — logo o
 *    incumbente usa pain 0.5 e entra no pool via `importance`.
 */
function cenario(db: InstanceType<typeof Database>): { incumbente: number; estudo: number } {
  const ins = db.prepare(
    `INSERT INTO chunks (source_file, chunk_text, chunk_type, pain, importance, created_at, updated_at, source_date)
     VALUES (?, ?, 'lesson', ?, ?, '2026-08-20 00:00:00', '2026-08-20 00:00:00', '2026-08-20')`,
  );
  // Preenchimento: salience alta, e FORA dos padroes do pool de cobertura.
  for (let i = 0; i < 4; i++) {
    ins.run(`memory/outros/filler-${i}.md`, `filler ${i}`, 0.5, 1.0);
  }
  const a = ins.run("memory/entities/lessons/incumbente.md", "incumbente", 0.5, 0.9)
    .lastInsertRowid as number;
  const b = ins.run("memory/entities/lessons/ep-estudo.md", "estudo", 0.25, 0.9)
    .lastInsertRowid as number;
  return { incumbente: a, estudo: b };
}

const ids = (r: { items: { id: number }[] }) => r.items.map((i) => i.id);

const SEED_ZERO = "0".repeat(64);

/**
 * Escreve um DESIGNATION.json congelado e devolve o env que o prende.
 *
 * Sem isto, `boostsParaCandidatos` devolve mapa vazio — e é deliberado: não há
 * caminho default para o conjunto designado, pela mesma razão que não há para o
 * ASSIGNMENT (servir tratamento a partir de conjunto não verificado é pior que não
 * servir).
 */
function comDesignacao(
  designados: Record<string, number>,
  seed = SEED_ZERO,
): NodeJS.ProcessEnv {
  const dir = mkdtempSync(join(tmpdir(), "p2-desig-"));
  const caminho = join(dir, "DESIGNATION.json");
  const corpo = JSON.stringify({ seed, designados }, null, 2);
  writeFileSync(caminho, corpo);
  return {
    NOX_P2_DESIGNATION: caminho,
    NOX_P2_DESIGNATION_SHA256: createHash("sha256").update(corpo).digest("hex"),
    // A guarda de drift compara com `p2_verdict` ao vivo; nos testes que montam
    // um DESIGNATION sintético isso divergiria por construção e só faria ruído.
    NOX_P2_DESIGNATION_SKIP_DRIFT: "1",
  } as NodeJS.ProcessEnv;
}

// ─── Invariância do caminho de controle ──────────────────────────────────────

test("invariância: sem provedor, altBoosted e diffP2 ausentes", () => {
  const db = makeDb();
  cenario(db);
  const r = buildBriefDiverse(db as unknown as BriefDb, { scope: "global", n: 3, format: "json" }, CFG);
  assert.equal(r.altBoosted, undefined);
  assert.equal(r.diffP2, undefined);
});

test("invariância: provedor com w=0 ⇒ mapa vazio ⇒ alt idêntico a altBoosted", () => {
  const db = makeDb();
  comP2Verdict(db);
  const { estudo } = cenario(db);
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S1','sig-a',?)").run(estudo);
  const env = comDesignacao({ "sig-a": estudo });
  const prov = (c: { id: number }[]) =>
    boostsParaCandidatos(db as never, c, 0, undefined, env);
  const r = buildBriefDiverse(db as unknown as BriefDb, { scope: "global", n: 3, format: "json" }, CFG, Date.now(), undefined, prov);
  assert.deepEqual(ids(r.altBoosted!), ids(r.alt));
  assert.equal(r.diffP2!.churn, 0);
});

test("invariância: p2_verdict ausente ⇒ fail-open ⇒ alt idêntico", () => {
  const db = makeDb();
  cenario(db); // sem comP2Verdict
  const env = comDesignacao({ "sig-a": 999 });
  const prov = (c: { id: number }[]) =>
    boostsParaCandidatos(db as never, c, 7.5, undefined, env);
  const r = buildBriefDiverse(db as unknown as BriefDb, { scope: "global", n: 3, format: "json" }, CFG, Date.now(), undefined, prov);
  assert.deepEqual(ids(r.altBoosted!), ids(r.alt));
  assert.equal(r.diffP2!.churn, 0);
});

// ─── Controle positivo: o boost DESLOCA ──────────────────────────────────────

test("controle positivo: a w=0 o incumbente ocupa o slot; a w=7.5 o chunk do estudo o toma", () => {
  const db = makeDb();
  comP2Verdict(db);
  const { incumbente, estudo } = cenario(db);
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S1','sig-a',?)").run(estudo);

  const semBoost = buildBriefDiverse(db as unknown as BriefDb, { scope: "global", n: 3, format: "json" }, CFG);
  const frescoSem = semBoost.alt.items.map((i) => i.id);
  assert.ok(frescoSem.includes(incumbente), "sem boost, o incumbente entra");

  const env = comDesignacao({ "sig-a": estudo });
  const prov = (c: { id: number }[]) =>
    boostsParaCandidatos(db as never, c, 7.5, undefined, env);
  const comBoost = buildBriefDiverse(db as unknown as BriefDb, { scope: "global", n: 3, format: "json" }, CFG, Date.now(), undefined, prov);
  assert.ok(comBoost.diffP2!.churn > 0, "o boost tem de deslocar algo");
  assert.ok(comBoost.diffP2!.would_enter.includes(estudo), "o chunk do estudo entra");
});

test("designação: dois chunks no mesmo grupo ⇒ só o designado é impulsionado", () => {
  const db = makeDb();
  comP2Verdict(db);
  const { incumbente, estudo } = cenario(db);
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S1','sig-a',?)").run(estudo);
  db.prepare("INSERT INTO p2_verdict VALUES ('ep2','S1','sig-a',?)").run(incumbente);
  // O designado vem do conjunto congelado, NÃO de comparação de salience: o teste
  // anterior asseverava "o de menor w_min = maior base", e essa era exatamente a
  // regra retratada (derivava de `access_count`, mutável por busca exógena).
  const boosts = boostsParaCandidatos(
    db as never,
    [{ id: estudo }, { id: incumbente }],
    7.5,
    undefined,
    comDesignacao({ "sig-a": estudo }),
  );
  assert.equal(boosts.size, 1, "um por grupo de assinatura");
  assert.equal([...boosts.keys()][0], estudo, "o designado, e só ele");
});

// ─── A regra nova: contrato de bytes e propriedades ──────────────────────────

test("chave: vetor de bytes CONGELADO, idêntico ao designation_verify.py", () => {
  // Gerado por `designation_verify.py` em 2026-08-26. Se estes valores mudarem, a
  // derivação mudou e todo conjunto designado já emitido é suspeito. Duas
  // implementações da mesma regra em linguagens diferentes só são a mesma regra se
  // concordarem byte a byte — o repo já tem o contraexemplo
  // (`extract_episodes.py:226` omite o separador e reproduziu 293 de 1.576).
  assert.equal(chaveDeDesignacao(SEED_ZERO, 10),
    "c5135da1044e3e823bfa94d61ea0986129d54688683691ed11024f535f020faa");
  assert.equal(chaveDeDesignacao(SEED_ZERO, 11),
    "3bf1f31ad408d7ecac870c2ac2129aee13662d8443e850dd015c0f56ae70f972");
  assert.equal(chaveDeDesignacao(SEED_ZERO, 30),
    "011b80e08a7c7f4dc4020689c12d77529e02ee349b4216704380b8ba3df921f6");
});

test("chave: o separador MORDE — sem ele a chave é outra", () => {
  // Teste negativo, e é o mais importante do arquivo: uma asserção que passaria
  // com e sem o `|` não estaria travando nada.
  const semSeparador = createHash("sha256").update(`${SEED_ZERO}10`, "ascii").digest("hex");
  assert.notEqual(chaveDeDesignacao(SEED_ZERO, 10), semSeparador);
  // E a seed é a STRING hex, não os 32 bytes decodificados.
  const comoBytes = createHash("sha256")
    .update(Buffer.concat([Buffer.from(SEED_ZERO, "hex"), Buffer.from("|10", "ascii")]))
    .digest("hex");
  assert.notEqual(chaveDeDesignacao(SEED_ZERO, 10), comoBytes);
});

test("designadosGlobais: vetor cruzado com o Python, grupos contendo `|`", () => {
  const db = makeDb();
  comP2Verdict(db);
  const ins = db.prepare("INSERT INTO p2_verdict VALUES (?,?,?,?)");
  // Nomes de grupo com `|` de propósito: é o dado REAL (`Bash|shell:outro`) e a
  // razão de `sig_primary` ter saído da chave.
  ins.run("e1", "S1", "grupo|um", 10);
  ins.run("e2", "S1", "grupo|um", 11);
  ins.run("e3", "S2", "grupo|um", 12);
  ins.run("e4", "S2", "grupo|dois", 20);
  ins.run("e5", "S1", "grupo|tres", 30);
  ins.run("e6", "S1", "grupo|tres", 31);
  const d = designadosGlobais(db as never, SEED_ZERO);
  assert.equal(d.size, 3, "um designado por grupo");
  assert.equal(d.get("grupo|um"), 11);
  assert.equal(d.get("grupo|dois"), 20);
  assert.equal(d.get("grupo|tres"), 30);
  // O designado de `grupo|um` é S1 (11) havendo um S2 (12) disponível: a regra
  // sorteia e NÃO olha severidade. É o ponto da opção B — a designação deixa de
  // herdar a calibração de severidade de uma família do painel.
  assert.equal(
    impressaoDoConjunto(d),
    "a599d19de17400a870f474828aba6bdc263550fd843412a17e591fda1305b4f8",
    "sha256 do conjunto tem de bater com o do Python",
  );
});

test("designadosGlobais: S0 e chunk_id NULL ficam fora do sorteio", () => {
  const db = makeDb();
  comP2Verdict(db);
  const ins = db.prepare("INSERT INTO p2_verdict VALUES (?,?,?,?)");
  ins.run("e1", "S1", "sig-a", 10);
  ins.run("e2", "S0", "sig-a", 11); // S0 com chunk: nao deve concorrer
  ins.run("e3", "S0", "sig-so-s0", null); // o caso real: 225 linhas assim
  const d = designadosGlobais(db as never, SEED_ZERO);
  assert.equal(d.size, 1, "grupo que so tem S0 nao existe para a designacao");
  assert.equal(d.get("sig-a"), 10);
});

test("designação é GLOBAL: fatias diferentes do pool ⇒ mesmo designado", () => {
  // A propriedade que a regra anterior NAO tinha. `boostsParaCandidatos` e chamada
  // >=2 vezes por brief com fatias diferentes (`brief.ts:714`, `:753`, `:843-851`)
  // e nao havia ponto onde os mapas fossem unificados; cada fatia recomputava o
  // argmin LOCAL, e o designado dependia de quem tinha aparecido.
  const db = makeDb();
  comP2Verdict(db);
  const ins = db.prepare("INSERT INTO p2_verdict VALUES (?,?,?,?)");
  ins.run("e1", "S1", "sig-a", 10);
  ins.run("e2", "S1", "sig-a", 11);
  const env = comDesignacao({ "sig-a": 11 });
  const soODesignado = boostsParaCandidatos(db as never, [{ id: 11 }], 7.5, undefined, env);
  const ambos = boostsParaCandidatos(db as never, [{ id: 10 }, { id: 11 }], 7.5, undefined, env);
  const soOOutro = boostsParaCandidatos(db as never, [{ id: 10 }], 7.5, undefined, env);
  assert.deepEqual([...soODesignado.keys()], [11]);
  assert.deepEqual([...ambos.keys()], [11], "a presenca do 10 nao promove o 10");
  assert.equal(soOOutro.size, 0, "designado fora do pool ⇒ grupo sem boost, ninguem promovido");
});

test("carregarDesignados: ausência, sha divergente e conjunto vazio recusam", () => {
  assert.equal(carregarDesignados({} as NodeJS.ProcessEnv).ok, false);
  const env = comDesignacao({ "sig-a": 10 });
  assert.equal(carregarDesignados(env).ok, true);
  const adulterado = { ...env, NOX_P2_DESIGNATION_SHA256: "0".repeat(64) };
  const r = carregarDesignados(adulterado as NodeJS.ProcessEnv);
  assert.equal(r.ok, false, "sha divergente NAO serve tratamento");
  assert.match(r.motivo ?? "", /sha256 divergente/);
  assert.equal(carregarDesignados(comDesignacao({})).ok, false, "conjunto vazio recusa");
});

test("sem seed: mapa vazio, grita UMA vez, e não lança", () => {
  _resetAvisoDeDesignacao();
  const db = makeDb();
  comP2Verdict(db);
  const { estudo } = cenario(db);
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S1','sig-a',?)").run(estudo);
  const vistos: string[] = [];
  const orig = console.error;
  console.error = (...a: unknown[]) => vistos.push(String(a[0]));
  try {
    for (let i = 0; i < 3; i++) {
      const b = boostsParaCandidatos(db as never, [{ id: estudo }], 7.5, undefined,
                                     {} as NodeJS.ProcessEnv);
      assert.equal(b.size, 0);
    }
  } finally {
    console.error = orig;
  }
  const avisos = vistos.filter((l) => l.includes("p2_designation_seed_ausente"));
  assert.equal(avisos.length, 1, "avisa uma vez por processo, nao a cada brief");
});

// ─── Modo, dose e resolução de braço ─────────────────────────────────────────

test("parseP2Mode: valor não reconhecido não cai em off silenciosamente", () => {
  assert.deepEqual(parseP2Mode(undefined), { mode: "off", bruto: null, reconhecido: true });
  assert.deepEqual(parseP2Mode("shadow"), { mode: "shadow", bruto: "shadow", reconhecido: true });
  const ruim = parseP2Mode("Active");
  assert.equal(ruim.mode, "off");
  assert.equal(ruim.reconhecido, false, "tem de sinalizar, não engolir");
  assert.equal(ruim.bruto, "Active");
});

test("doseDeShadow: defaults e leitura de env", () => {
  assert.equal(doseDeShadow({} as NodeJS.ProcessEnv), 0);
  assert.equal(doseDeShadow({ NOX_P2_SHADOW_W: "4" } as never), 4);
  assert.equal(doseDeShadow({ NOX_P2_SHADOW_W: "-1" } as never), 0);
  // `cDesignacao()` foi removida em 2026-08-26 junto com NOX_P2_C_DESIGNACAO.
  // Devolvia CUT_FRESH = 0.7342, um limiar que o `pick` nunca aplica e cujo
  // referente a emenda v1.12 retrata (retratacoes 3, 4, 13).
});

test("epochInicioISO: fronteira 09:00 UTC", () => {
  assert.equal(epochInicioISO(Date.parse("2026-08-21T08:59:59Z")), "2026-08-20");
  assert.equal(epochInicioISO(Date.parse("2026-08-21T09:00:00Z")), "2026-08-21");
  assert.equal(epochInicioISO(Date.parse("2026-08-21T23:30:00Z")), "2026-08-21");
});

test("resolverBraco: toda falha devolve CONTROLE com ok=false", () => {
  assert.equal(resolverBraco("2026-08-21", {} as NodeJS.ProcessEnv).ok, false);
  const dir = mkdtempSync(join(tmpdir(), "p2-assign-"));
  const f = join(dir, "ASSIGNMENT.json");
  const corpo = JSON.stringify({
    epochs: [
      { epoch_inicio: "2026-08-21", arm: "treatment", w: 4 },
      { epoch_inicio: "2026-08-22", arm: "control", w: 0 },
    ],
  });
  writeFileSync(f, corpo);
  const sha = createHash("sha256").update(corpo).digest("hex");

  const errado = resolverBraco("2026-08-21", {
    NOX_P2_ASSIGNMENT: f,
    NOX_P2_ASSIGNMENT_SHA256: "0".repeat(64),
  } as never);
  assert.equal(errado.ok, false);
  assert.equal(errado.arm, "control");
  assert.match(errado.motivo!, /sha256 divergente/);

  const env = { NOX_P2_ASSIGNMENT: f, NOX_P2_ASSIGNMENT_SHA256: sha } as never;
  const t = resolverBraco("2026-08-21", env);
  assert.deepEqual({ ok: t.ok, arm: t.arm, w: t.w }, { ok: true, arm: "treatment", w: 4 });
  const c = resolverBraco("2026-08-22", env);
  assert.deepEqual({ ok: c.ok, arm: c.arm, w: c.w }, { ok: true, arm: "control", w: 0 });
  const ausente = resolverBraco("2026-09-01", env);
  assert.equal(ausente.ok, false);
  assert.match(ausente.motivo!, /ausente da sequência/);
});

test("W_OUTCOME escala com severity e Δ_cut está congelado", () => {
  assert.equal(P2_DELTA_CUT, 0.043);
  const db = makeDb();
  comP2Verdict(db);
  const { estudo } = cenario(db);
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S2','sig-a',?)").run(estudo);
  const b = boostsParaCandidatos(db as never, [{ id: estudo }], 4, undefined,
                                 comDesignacao({ "sig-a": estudo }));
  assert.equal(b.get(estudo), 4 * 0.043 * 0.5);
});

// ─── Log durável de decisão ──────────────────────────────────────────────────

test("log: sem NOX_P2_SERVING_LOG não escreve, e avisa UMA vez", () => {
  _resetAvisoDeLog();
  const originais: string[] = [];
  const orig = console.error;
  console.error = (...a: unknown[]) => originais.push(String(a[0]));
  try {
    logarDecisaoDeServing({ tag: "x" }, {} as NodeJS.ProcessEnv);
    logarDecisaoDeServing({ tag: "y" }, {} as NodeJS.ProcessEnv);
    logarDecisaoDeServing({ tag: "z" }, {} as NodeJS.ProcessEnv);
  } finally {
    console.error = orig;
  }
  const avisos = originais.filter((l) => l.includes("p2_serving_log_ausente"));
  assert.equal(avisos.length, 1, "avisa uma vez, não a cada brief");
  assert.match(avisos[0], /replay impossivel/);
});

test("log: com caminho explícito grava NDJSON com as DUAS listas de ids", () => {
  const dir = mkdtempSync(join(tmpdir(), "p2-log-"));
  const f = join(dir, "sub", "p2-serving.ndjson"); // subdir inexistente de propósito
  const env = { NOX_P2_SERVING_LOG: f } as never;
  logarDecisaoDeServing({ tag: "p2_outcome", ids_controle: [1, 2], ids_tratado: [1, 3], churn: 2 }, env);
  logarDecisaoDeServing({ tag: "p2_outcome", ids_controle: [4], ids_tratado: [4], churn: 0 }, env);
  assert.ok(existsSync(f), "cria o diretório");
  const linhas = readFileSync(f, "utf8").trim().split("\n");
  assert.equal(linhas.length, 2, "append-only, uma linha por decisão");
  const primeira = JSON.parse(linhas[0]);
  assert.deepEqual(primeira.ids_controle, [1, 2]);
  assert.deepEqual(primeira.ids_tratado, [1, 3]);
  assert.ok(primeira.ts, "carrega timestamp");
});

test("log: falha de escrita não lança — serving não degrada por causa de log", () => {
  const env = { NOX_P2_SERVING_LOG: "/dev/null/escrever.ndjson" } as never;
  const orig = console.error;
  console.error = () => {};
  try {
    assert.doesNotThrow(() => logarDecisaoDeServing({ tag: "x" }, env));
  } finally {
    console.error = orig;
  }
});

// ─── Gate de maturidade: o chunk nao pode agir no epoch em que foi escrito ───

function comVerdictDatado(): { db: InstanceType<typeof Database>; estudo: number } {
  const db = makeDb();
  db.exec(`CREATE TABLE p2_verdict (
    episode_id TEXT PRIMARY KEY, severity TEXT NOT NULL,
    sig_primary TEXT NOT NULL, chunk_id INTEGER, written_at TEXT NOT NULL)`);
  const { estudo } = cenario(db);
  return { db, estudo };
}

test("epochInicioMs: fronteira registrada 09:00 UTC", () => {
  assert.equal(epochInicioMs("2026-08-22"), Date.parse("2026-08-22T09:00:00Z"));
});

test("gate: chunk escrito NO epoch corrente NAO e impulsionado", () => {
  const { db, estudo } = comVerdictDatado();
  // epoch corrente comeca 2026-08-22T09:00Z; escrito 6h DEPOIS do inicio
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S2','sig-a',?,?)")
    .run(estudo, "2026-08-22 15:00:00");
  const inicio = epochInicioMs("2026-08-22");
  const b = boostsParaCandidatos(db as never, [{ id: estudo }], 7.5, inicio,
                                 comDesignacao({ "sig-a": estudo }));
  assert.equal(b.size, 0, "escrito dentro do epoch: fora da populacao tratada");
});

test("gate: escrito MENOS de 24 h antes do inicio tambem fica fora", () => {
  const { db, estudo } = comVerdictDatado();
  // inicio 2026-08-22T09:00Z; escrito 10 h antes => 2026-08-21T23:00Z
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S2','sig-a',?,?)")
    .run(estudo, "2026-08-21 23:00:00");
  const b = boostsParaCandidatos(db as never, [{ id: estudo }], 7.5,
                                 epochInicioMs("2026-08-22"),
                                 comDesignacao({ "sig-a": estudo }));
  assert.equal(b.size, 0, "10 h < 1 epoch: fora");
});

test("gate: escrito >= 24 h antes do inicio ENTRA", () => {
  const { db, estudo } = comVerdictDatado();
  // inicio 2026-08-22T09:00Z; corte = 2026-08-21T09:00Z; escrito 2026-08-20
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S2','sig-a',?,?)")
    .run(estudo, "2026-08-20 12:00:00");
  const b = boostsParaCandidatos(db as never, [{ id: estudo }], 7.5,
                                 epochInicioMs("2026-08-22"),
                                 comDesignacao({ "sig-a": estudo }));
  assert.equal(b.size, 1, "maduro: entra");
  assert.equal(b.get(estudo), 7.5 * 0.043 * 0.5);
});

test("gate: exatamente no corte (24 h) entra — a regra e '>=' 1 epoch", () => {
  const { db, estudo } = comVerdictDatado();
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S1','sig-a',?,?)")
    .run(estudo, "2026-08-21 09:00:00");
  const b = boostsParaCandidatos(db as never, [{ id: estudo }], 7.5,
                                 epochInicioMs("2026-08-22"),
                                 comDesignacao({ "sig-a": estudo }));
  assert.equal(b.size, 1, "no corte exato: dentro");
});

test("sem epochInicioMs o gate NAO se aplica — compatibilidade explicita", () => {
  const { db, estudo } = comVerdictDatado();
  db.prepare("INSERT INTO p2_verdict VALUES ('ep1','S2','sig-a',?,?)")
    .run(estudo, "2026-08-22 15:00:00");
  const b = boostsParaCandidatos(db as never, [{ id: estudo }], 7.5, undefined,
                                 comDesignacao({ "sig-a": estudo }));
  assert.equal(b.size, 1, "omitir o parametro desliga o gate, e isso e declarado");
});
