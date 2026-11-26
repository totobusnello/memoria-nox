/**
 * distill-shadow.ts — criterion C2 in shadow beside the production distiller (2026-11-06).
 *
 * For every block production sends to its model, a second call distils the SAME block under
 * criterion C2 (Paper 3, memoria-nox paper3-construction/lme-run.py DISTILL_SYSTEM_V3: the
 * production prompt plus the identifier and event paragraphs, inserted before the JSON anchor).
 * One JSON line per block goes to a private file: the block text, production's own C0 units for
 * that block, the C2 units. No memory is written to the database and nothing is ingested; the only
 * database write is the provider-cost row every tracked() call makes. A shadow failure never
 * reaches the production path.
 *
 * Why the block and not the session: Paper D's offline replay failed its fidelity control because
 * it rebuilt the input and kept the scheduled-job prompts production drops. Here the input is
 * production's by construction.
 *
 * On only while <dir>/ENABLED exists and the date is before STOP_AFTER. Caps per run: MAX_CALLS
 * shadow calls and MAX_MS of shadow wall time. Protocol: memoria-nox
 * paper-d-c2-production/SHADOW-PROTOCOL.md.
 */
import { appendFileSync, existsSync, mkdirSync, chmodSync } from "fs";
import { createHash } from "crypto";
import { resolve } from "path";
import { tracked } from "./lib/provider-cost.js";

export const SHADOW_DIR = process.env.NOX_DISTILL_SHADOW_DIR ?? "/var/lib/nox-mem/shadow-c2";
export const STOP_AFTER = "2027-01-11";
const MAX_CALLS = 300;
const MAX_MS = 15 * 60 * 1000;
const MODEL = "gemini-2.5-flash-lite";

const ANCHOR = "Responda APENAS com JSON válido:";
const IDENT_PARAGRAPH = "OBRIGATÓRIO: todo identificador que aparecer na conversa tem de ser copiado LETRA POR LETRA no texto da memória — nome de arquivo, caminho, comando, nome de tabela ou de coluna, chave de configuração, número de porta, URL, nome de canal, versão, valor numérico. Nunca trocar por descrição (\"o arquivo de tarefas\"), nunca abreviar, nunca traduzir. Uma memória que diz o que foi decidido mas não diz sobre qual arquivo, comando ou valor não serve para nada: ou carrega o identificador, ou não vale ser extraída.\n\n";
const EVENT_PARAGRAPH = "TAMBÉM OBRIGATÓRIO: fatos concretos sobre a vida do usuário merecem memória mesmo quando ditos de passagem, no meio de outro assunto — rotina, quantidades, valores gastos, durações, idades, lugares, pessoas, compras, viagens, eventos. Extraia cada um como fato (categoria context), com os números e nomes copiados, sem transformá-lo em lição ou preferência, e com importância de pelo menos 0.5.\nQuando a conversa disser quando algo aconteceu (\"há três semanas\", \"ontem\", \"no sábado passado\", \"em 15 de abril\"), copie a expressão de tempo para a memória junto com o evento: a data da conversa não é a data do evento.\nQuando o assistente der uma informação específica que o usuário pode pedir de volta depois — uma lista, um nome, uma recomendação, um número — guarde-a como memória, com os itens na ordem em que foram dados.\n\n";
/** sha256 of Paper 3's DISTILL_SYSTEM_V3; c2Prompt refuses to run on anything else. */
export const C2_SHA256 = "325342a36e742f1e844b7c3792dae3eb47a76879c501678b576cd6df2cc8089d";

export function c2Prompt(c0: string): string {
  if (c0.split(ANCHOR).length !== 2) throw new Error("shadow: C0 anchor missing or repeated");
  const c2 = c0.replace(ANCHOR, IDENT_PARAGRAPH + EVENT_PARAGRAPH + ANCHOR);
  const h = createHash("sha256").update(c2).digest("hex");
  if (h !== C2_SHA256) throw new Error(`shadow: C2 prompt sha256 ${h.slice(0, 12)} differs from Paper 3`);
  return c2;
}

const sha = (s: string) => createHash("sha256").update(s).digest("hex");

interface Unit { text: string; category: string; importance: number }

export class ShadowRun {
  readonly enabled: boolean;
  readonly reason: string;
  private prompt = "";
  private calls = 0;
  private failed = 0;
  private skipped = 0;
  private readonly started = Date.now();
  private readonly file: string;

  constructor(c0Prompt: string, dryRun: boolean, now = new Date()) {
    this.file = resolve(SHADOW_DIR, `c2-shadow-${now.toISOString().slice(0, 10)}.jsonl`);
    let why = "";
    if (dryRun) why = "dry run";
    else if (!existsSync(resolve(SHADOW_DIR, "ENABLED"))) why = "no ENABLED flag";
    else if (now.toISOString().slice(0, 10) >= STOP_AFTER) why = `past STOP_AFTER ${STOP_AFTER}`;
    else if (!process.env.GEMINI_API_KEY) why = "no GEMINI_API_KEY";
    if (!why) {
      try {
        this.prompt = c2Prompt(c0Prompt);
        mkdirSync(SHADOW_DIR, { recursive: true, mode: 0o700 });
        chmodSync(SHADOW_DIR, 0o700);
      } catch (e) {
        why = String((e as Error).message ?? e).slice(0, 200);
      }
    }
    this.enabled = !why;
    this.reason = why || "on";
    console.log(`[DISTILL-SHADOW] C2 shadow ${this.enabled ? "on" : "off"} (${this.reason})`);
  }

  /** Never throws. c0 is what production's distillBlock returned for this block. */
  async block(meta: { sessionKey: string; agentId: string; blockIndex: number; nBlocks: number;
                      messageCount: number; sessionMtimeMs: number },
              block: string, c0: Unit[]): Promise<void> {
    if (!this.enabled) return;
    if (this.calls >= MAX_CALLS || Date.now() - this.started > MAX_MS) { this.skipped++; return; }
    this.calls++;
    let units: Unit[] = [], ok = false, modelVersion: string | null = null, error: string | null = null;
    let usage: unknown = null;
    try {
      const r = await tracked({ caller: "session-distill.shadow-c2", provider: "gemini", model: MODEL })(
        `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${process.env.GEMINI_API_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ role: "user", parts: [{ text: this.prompt + "\n\nConversa:\n" + block }] }],
            generationConfig: { responseMimeType: "application/json", temperature: 0.1 },
          }),
          signal: AbortSignal.timeout(30_000),
        });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json() as { modelVersion?: string; usageMetadata?: unknown;
        candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
      modelVersion = d.modelVersion ?? null;
      usage = d.usageMetadata ?? null;
      const text = (d.candidates?.[0]?.content?.parts ?? []).map((p) => p.text ?? "").join("");
      if (!text) throw new Error("empty response");
      const mem = (JSON.parse(text) as { memories?: Unit[] }).memories ?? [];
      units = mem.filter((m) => m && typeof m === "object" && (m.importance ?? 0) >= 0.5);
      ok = true;
    } catch (e) {
      this.failed++;
      error = String((e as Error).message ?? e).replace(/key=[^&\s]+/g, "key=REDACTED").slice(0, 200);
    }
    try {
      appendFileSync(this.file, JSON.stringify({
        v: 1, ts: new Date().toISOString(), session_key: meta.sessionKey, agent: meta.agentId,
        block_index: meta.blockIndex, n_blocks: meta.nBlocks, message_count: meta.messageCount,
        session_mtime: new Date(meta.sessionMtimeMs).toISOString(),
        block_sha256: sha(block), block, c0_units: c0,
        c2: { ok, units, model: MODEL, model_version: modelVersion, prompt_sha256: C2_SHA256, usage, error },
      }) + "\n", { mode: 0o600 });
    } catch (e) {
      this.failed++;
      console.log(`[DISTILL-SHADOW] write failed: ${String((e as Error).message ?? e).slice(0, 120)}`);
    }
    await new Promise((r) => setTimeout(r, 1000));
  }

  summary(): void {
    if (!this.enabled) return;
    console.log(`[DISTILL-SHADOW] Done: ${this.calls} C2 calls, ${this.failed} failed, ${this.skipped} blocks over the cap → ${this.file}`);
  }
}
