#!/usr/bin/env node
/**
 * pilot_window_stats.mjs — emite os números da série de piloto do Paper 2 sobre
 * uma JANELA FECHADA, para que a prosa da emenda não envelheça.
 *
 * Motivo (achado 2026-08-25): a emenda v1.12 citava `n = 2.256` medido às
 * 10:22Z. Uma hora e meia depois o log tinha 2.263 linhas — o cron produz 28
 * registros/hora. Número de série viva citado como fotografia fica falso num
 * depósito imutável. A correção é declarar a janela, não o instante.
 *
 * Lição aplicada: derivação vai em script que EMITE ou ASSERTA, não em prosa
 * que afirma (retratação de 2026-08-17).
 *
 * Uso:
 *   node pilot_window_stats.mjs <log.ndjson> [--from ISO] [--to ISO] [--assert-json f]
 *
 * Janela congelada da emenda v1.12:
 *   --from 2026-08-21T22:57:00Z --to 2026-08-25T10:22:00Z
 *
 * Com --assert-json, compara com um snapshot e sai != 0 se divergir — o guarda
 * que impede a prosa de derivar do dado sem recomputo.
 */

import { readFileSync } from "node:fs";

const argv = process.argv.slice(2);
if (argv.length === 0) {
  console.error("uso: pilot_window_stats.mjs <log.ndjson> [--from ISO] [--to ISO] [--assert-json f]");
  process.exit(2);
}
const logPath = argv[0];
const flag = (n) => {
  const i = argv.indexOf(n);
  return i === -1 ? null : argv[i + 1];
};
const FROM = flag("--from") ?? "2026-08-21T22:57:00Z";
const TO = flag("--to") ?? "2026-08-25T10:22:00Z";
const assertPath = flag("--assert-json");

// O gate de maturidade (brief-outcome.ts:162-173) libera o batch a partir do
// epoch de 23/08: `written_at <= epochInicio - 24h`, epochs abrem 09:00Z e os
// 280 p2_verdict foram escritos em 2026-08-21T22:51:23Z.
const PRIMEIRO_EPOCH_MADURO = "2026-08-23";

const linhas = readFileSync(logPath, "utf8").split("\n").filter((l) => l.trim());
const todos = linhas.map((l) => JSON.parse(l));
const rec = todos.filter((r) => r.ts >= FROM && r.ts <= TO);

const churnPos = rec.filter((r) => (r.churn ?? 0) > 0);
const preGate = rec.filter((r) => r.epoch < PRIMEIRO_EPOCH_MADURO);
const posGate = rec.filter((r) => r.epoch >= PRIMEIRO_EPOCH_MADURO);
const posGatePos = posGate.filter((r) => (r.churn ?? 0) > 0);

const magnitude = {};
for (const r of churnPos) magnitude[r.churn] = (magnitude[r.churn] ?? 0) + 1;

const porDia = {};
for (const r of rec) {
  const d = r.ts.slice(0, 10);
  porDia[d] ??= { n: 0, churn: 0 };
  porDia[d].n++;
  if ((r.churn ?? 0) > 0) porDia[d].churn++;
}

const freshSizes = new Set(rec.map((r) => (r.fresh_added ?? []).length));
const modos = [...new Set(rec.map((r) => r.modo))];
const servidos = [...new Set(rec.map((r) => r.servido))];

// Série horária PÓS-GATE. Congelada aqui porque a retratação 9 (a série oscila,
// não decai monotonicamente) repousa nela — e uma redação anterior publicou um
// recorte de 25 horas que começava na retomada da MIGRAÇÃO (15:52Z de 23/08),
// não na abertura do gate, somando 85 eventos onde o pós-gate tem 102.
const porHora = {};
for (const r of posGate) {
  const h = r.ts.slice(0, 13);
  porHora[h] ??= { n: 0, churn: 0 };
  porHora[h].n++;
  if ((r.churn ?? 0) > 0) porHora[h].churn++;
}
const taxasHora = Object.keys(porHora)
  .sort()
  .map((h) => +((100 * porHora[h].churn) / porHora[h].n).toFixed(1));
const media = taxasHora.length
  ? +(taxasHora.reduce((a, b) => a + b, 0) / taxasHora.length).toFixed(1)
  : null;
const ordenadas = [...taxasHora].sort((a, b) => a - b);
const mediana = ordenadas.length
  ? ordenadas.length % 2
    ? ordenadas[(ordenadas.length - 1) / 2]
    : +((ordenadas[ordenadas.length / 2 - 1] + ordenadas[ordenadas.length / 2]) / 2).toFixed(1)
  : null;

const out = {
  janela: { from: FROM, to: TO },
  total: rec.length,
  serie_horaria_pos_gate: {
    horas: taxasHora.length,
    registros: posGate.length,
    eventos: posGatePos.length,
    taxas_pct: taxasHora,
    media_pct: media,
    mediana_pct: mediana,
    min_pct: ordenadas[0] ?? null,
    max_pct: ordenadas[ordenadas.length - 1] ?? null,
  },
  churn_pos: churnPos.length,
  deslocamentos: churnPos.reduce((a, r) => a + r.churn, 0),
  magnitude,
  pre_gate: { n: preGate.length, churn_pos: preGate.filter((r) => (r.churn ?? 0) > 0).length },
  pos_gate: {
    n: posGate.length,
    churn_pos: posGatePos.length,
    taxa_pct: posGate.length ? +((100 * posGatePos.length) / posGate.length).toFixed(1) : null,
  },
  por_dia: porDia,
  fresh_added_tamanhos: [...freshSizes],
  modos,
  servidos,
};

if (assertPath) {
  const esperado = JSON.parse(readFileSync(assertPath, "utf8"));
  const a = JSON.stringify(esperado, Object.keys(esperado).sort());
  const b = JSON.stringify(out, Object.keys(out).sort());
  if (a !== b) {
    console.error("DIVERGE do snapshot — a prosa da emenda precisa ser recomputada.");
    console.error("esperado:", a);
    console.error("obtido  :", b);
    process.exit(1);
  }
  console.error("OK — bate com o snapshot.");
}

console.log(JSON.stringify(out, null, 2));
