#!/usr/bin/env node
/**
 * gatilho-designados.mjs — vigia a EXISTÊNCIA E A IDENTIDADE dos chunks designados.
 *
 * ─── Por que este gatilho passou a existir (2026-09-08) ────────────────────
 *
 * Ao apurar por que um replay não reproduzia a janela, medi que **53 dos 141
 * chunks que o canal serve desapareceram do banco vivo** entre `2026-09-07
 * 06:00Z` e `2026-09-08 06:00Z`: todos de `memory/lessons.md`, ids contíguos
 * `308444..308496`. O arquivo reaparece com **60** chunks em ids **novos**
 * (`309034..309093`, `created_at 2026-09-07 23:01:36`).
 *
 * Isto é **reingestão de arquivo**: o conteúdo permanece, a IDENTIDADE muda. O
 * ingest apaga os chunks daquele `source_file` e cria outros. Efeito medido: ~65%
 * dos briefs de qualquer janela de setembro deixaram de ser reproduzíveis pelo
 * replay (400/672 em 09-05, 436/672 em 09-06, 440/672 em 09-07).
 *
 * Os 19 designados sobreviveram — conferido em quatro corpora, 19/19. Mas a
 * reingestão é **por arquivo**, e os 19 vivem em 19 arquivos DISTINTOS de
 * `memory/entities/lessons/`. Editar um deles mata aquele designado, e a
 * designação quebra **em silêncio**: nenhum alarme existia para isso. Os
 * designados são o único ativo insubstituível do ensaio — a designação foi
 * sorteada uma vez, com semente pública, e não se refaz.
 *
 * ─── Duas pernas, porque ausência não cobre tudo ───────────────────────────
 *
 * 1. **Ausência** (`RED`): o id não está em `chunks`. É o que a reingestão
 *    produz, e é fatal — o alvo da intervenção deixou de existir.
 * 2. **Deriva de conteúdo** (`YELLOW`): o id vive mas o `sha256` do
 *    `chunk_text` mudou. Um `UPDATE` no mesmo id preserva a identidade e altera
 *    o alvo; a perna 1 fica **calada** nesse caso, que é a forma de defeito que
 *    a regra 9 do `CLAUDE.md` descreve. Duas perguntas ⇒ duas pernas.
 *
 * ─── O baseline é IMUTÁVEL, e isso é deliberado ────────────────────────────
 *
 * O guarda **cria** o baseline se ele não existir e **nunca** o sobrescreve. Um
 * guarda que reescreve a própria referência conserta-se a si mesmo e cala para
 * sempre: a segunda execução compararia o estado corrompido consigo mesmo e
 * diria `GREEN`. Trocar o baseline exige ação humana explícita, e o `sha256`
 * dele vai para o `DEVIATIONS-FOR-PAPER.md` para ser auditável.
 *
 * ─── Disciplinas herdadas de erro cometido HOJE ────────────────────────────
 *
 * - **Lê o banco VIVO, não o snapshot de epoch.** A morte acontece no vivo; o
 *   snapshot é derivado e só mostra o efeito no dia seguinte.
 * - **Confere o `sha256` do DESIGNATION antes de ler os ids.** Sem isso o
 *   guarda pode vigiar uma designação que já não é a servida.
 * - **Grava o NDJSON em TODOS os caminhos de saída**, inclusive os de recusa.
 *   Hoje mesmo consertei o `gatilho-saturacao.sh`, onde os vereditos por atalho
 *   iam só para um arquivo de status que a execução seguinte SOBRESCREVE — perda
 *   permanente, e justamente dos alarmes de exceção (§10.8).
 *
 * Exit 0 sempre: o estado vive na linha, para o cron não virar alarme.
 */

import Database from "better-sqlite3";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, appendFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

function args(argv) {
  const o = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) { console.error(`argumento solto: ${a}`); process.exit(2); }
    const k = a.slice(2);
    const v = argv[++i];
    if (v === undefined || v.startsWith("--")) { console.error(`--${k} sem valor`); process.exit(2); }
    o[k] = v;
  }
  return o;
}
const A = args(process.argv);
const exigir = (k) => { if (!A[k]) { console.error(`FALTA --${k}`); process.exit(2); } return A[k]; };

const VIVO = resolve(exigir("vivo"));
const DESIG = resolve(exigir("designacao"));
const DESIG_SHA = exigir("designacao-sha256");
const BASE = resolve(exigir("baseline"));

const TS = new Date().toISOString();
const sha = (b) => createHash("sha256").update(b).digest("hex");

function emitir(estado, resto, extra) {
  const linha = `${estado} p2-designados-integros ${resto} ts=${TS}`;
  console.log(linha);
  if (A.status) writeFileSync(resolve(A.status), linha + "\n");
  if (A.ndjson) {
    appendFileSync(resolve(A.ndjson), JSON.stringify({
      ts: TS, tag: "p2_gatilho_designados", estado, linha_status: resto,
      vivo: VIVO, designacao: DESIG, baseline: BASE, ...(extra || {}),
    }) + "\n");
  }
  process.exit(0);
}

// ─── o DESIGNATION tem de ser o que a produção serve ───────────────────────
if (!existsSync(DESIG)) emitir("RED", `motivo=designacao-nao-existe caminho=${DESIG}`);
const bytesDesig = readFileSync(DESIG);
const shaDesig = sha(bytesDesig);
if (shaDesig !== DESIG_SHA) {
  emitir("RED", `motivo=designacao-sha256-divergente esperado=${DESIG_SHA.slice(0, 12)} obtido=${shaDesig.slice(0, 12)}`,
    { sha_esperado: DESIG_SHA, sha_obtido: shaDesig });
}
let ids;
try {
  const doc = JSON.parse(bytesDesig.toString("utf8"));
  ids = doc.designados_ids;
  if (!Array.isArray(ids) || ids.length === 0 || !ids.every((x) => Number.isInteger(x))) {
    emitir("RED", `motivo=designados_ids-ausente-ou-invalido`);
  }
} catch (e) {
  emitir("RED", `motivo=designacao-ilegivel detalhe=${String(e.message).slice(0, 80)}`);
}
ids = [...ids].sort((a, b) => a - b);

if (!existsSync(VIVO)) emitir("RED", `motivo=banco-vivo-nao-existe caminho=${VIVO}`);
const db = new Database(VIVO, { readonly: true, fileMustExist: true });

/**
 * `chunk_text` entra no hash junto com `source_file`: um designado que mude de
 * arquivo é outro chunk para efeito de canal, mesmo com o texto igual.
 */
const q = db.prepare("SELECT id, source_file, chunk_text FROM chunks WHERE id = ?");
const atual = new Map();
const ausentes = [];
for (const id of ids) {
  const r = q.get(id);
  if (!r) { ausentes.push(id); continue; }
  atual.set(id, { source_file: r.source_file, sha256_texto: sha(String(r.chunk_text ?? "")) });
}
db.close();

// ─── baseline: cria uma vez, nunca sobrescreve ─────────────────────────────
if (!existsSync(BASE)) {
  if (ausentes.length > 0) {
    emitir("RED", `motivo=baseline-ausente-e-designados-ja-faltam ausentes=${ausentes.join(",")} ` +
      `presentes=${atual.size}/${ids.length} ACAO=nao criei baseline sobre estado ja quebrado`,
      { ausentes, presentes: atual.size, total: ids.length });
  }
  const doc = { criado_em: TS, designacao: DESIG, designacao_sha256: shaDesig,
                total: ids.length, chunks: Object.fromEntries(atual) };
  const corpo = JSON.stringify(doc, null, 1) + "\n";
  writeFileSync(BASE, corpo);
  emitir("GREEN", `motivo=baseline-criado presentes=${atual.size}/${ids.length} ` +
    `baseline_sha256=${sha(corpo).slice(0, 12)}`,
    { baseline_criado: true, baseline_sha256: sha(corpo), presentes: atual.size, total: ids.length });
}

const baseDoc = JSON.parse(readFileSync(BASE, "utf8"));
const shaBase = sha(readFileSync(BASE));

if (ausentes.length > 0) {
  emitir("RED", `motivo=designados-AUSENTES-do-banco ausentes=${ausentes.join(",")} ` +
    `presentes=${atual.size}/${ids.length} baseline_sha256=${shaBase.slice(0, 12)} ` +
    `ACAO=reingestao por arquivo mata o id do designado; a designacao NAO se refaz — parar analise e registrar`,
    { ausentes, presentes: atual.size, total: ids.length, baseline_sha256: shaBase });
}

const derivou = [];
for (const [id, cur] of atual) {
  const b = baseDoc.chunks?.[String(id)];
  if (!b) { derivou.push(`${id}:fora-do-baseline`); continue; }
  if (b.sha256_texto !== cur.sha256_texto) derivou.push(`${id}:texto`);
  else if (b.source_file !== cur.source_file) derivou.push(`${id}:arquivo`);
}
if (derivou.length > 0) {
  emitir("YELLOW", `motivo=designados-presentes-mas-com-DERIVA n=${derivou.length} ` +
    `quais=${derivou.join(",")} presentes=${atual.size}/${ids.length} ` +
    `baseline_sha256=${shaBase.slice(0, 12)} ACAO=id preservado e conteudo alterado — o alvo mudou sem morrer`,
    { deriva: derivou, presentes: atual.size, total: ids.length, baseline_sha256: shaBase });
}

emitir("GREEN", `motivo=todos-integros presentes=${atual.size}/${ids.length} ` +
  `baseline_sha256=${shaBase.slice(0, 12)}`,
  { presentes: atual.size, total: ids.length, baseline_sha256: shaBase });
