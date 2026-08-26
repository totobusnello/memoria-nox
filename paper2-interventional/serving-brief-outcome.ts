/**
 * brief-outcome.ts — Paper 2, componente 2: despacho de braço e boost de desfecho.
 *
 * Espelha o precedente do D2 (`brief-diversity.ts` + `composeBrief`):
 * `off | shadow | active`, fail-open, e em `shadow` computa a variante tratada,
 * loga o deslocamento e serve a NÃO-tratada. Daí `shadow` entregar a medição de
 * ativação pré-tratamento sem servir tratamento e sem sortear braço.
 *
 * Invariantes de desenho:
 *  - função-zero quando controle: `boostsParaCandidatos` devolve mapa vazio e o
 *    chamador nem computa a segunda composição;
 *  - o código NÃO contém a atribuição — ela vem de ASSIGNMENT.json, cujo caminho
 *    e sha256 ficam presos em drop-in registrado;
 *  - falha de resolução ⇒ boost zero, o que NÃO é neutro (converte epoch de
 *    tratamento em controle e enviesa para o nulo) ⇒ loga alto e é contado.
 *
 * ⚠️ O boost entra no estágio (b) — o `ranked.sort` sobre salience completa —
 * e não no pré-rank SQL do `LIMIT 400`. Razão registrada: (a) ordena
 * `last_served ASC` primeiro e um chunk do estudo é nunca-servido, logo está
 * sempre entre os 400; (a) não é vinculante para esta população. Consequência a
 * declarar: a aritmética de severidade só existe em (b) — a chave de (a) não tem
 * termo de recência.
 */

import { createHash } from "node:crypto";
import { appendFileSync, mkdirSync, readFileSync } from "node:fs";
import { dirname } from "node:path";

/** Spread de salience medido no cut do brief, congelado no §2. */
export const P2_DELTA_CUT = 0.043;

export type P2Mode = "off" | "shadow" | "active";

/**
 * Modo do componente 2. Diferente do `parseMode` do epoch-snapshot, este
 * distingue "ausente" de "escrito errado": um valor não reconhecido NÃO cai
 * silenciosamente em `off` — devolve o cru para o /api/health poder gritar.
 * (Lição de 19/08: drop-in sem `[Service]` desligou o snapshot em silêncio e
 * `systemctl is-active` seguia dizendo `active`.)
 */
export function parseP2Mode(raw: string | undefined): {
  mode: P2Mode;
  bruto: string | null;
  reconhecido: boolean;
} {
  if (raw === undefined || raw === "") return { mode: "off", bruto: null, reconhecido: true };
  if (raw === "off" || raw === "shadow" || raw === "active")
    return { mode: raw, bruto: raw, reconhecido: true };
  return { mode: "off", bruto: raw, reconhecido: false };
}

export interface Designacao {
  /** epoch a que a linha se refere, data de início em ISO (YYYY-MM-DD). */
  epoch_inicio: string;
  arm: "control" | "treatment";
  /** múltiplo de Δ_cut; 0 em controle. */
  w: number;
}

export interface ResolucaoDeBraco {
  ok: boolean;
  arm: "control" | "treatment";
  w: number;
  /** motivo quando !ok — o epoch é analisado as-assigned (ITT) de todo modo. */
  motivo?: string;
}

const CONTROLE: ResolucaoDeBraco = { ok: true, arm: "control", w: 0 };

/**
 * Resolve o braço do epoch a partir do ASSIGNMENT.json publicado.
 *
 * Preso por caminho + sha256 nas env vars `NOX_P2_ASSIGNMENT` e
 * `NOX_P2_ASSIGNMENT_SHA256`. Divergência de hash ⇒ recusa (não serve
 * tratamento com sequência não verificada).
 *
 * ⚠️ Toda falha devolve controle com `ok: false`. Isso enviesa para o nulo, então
 * o chamador TEM de logar e contar — a contagem é quantidade pré-comprometida de
 * reporte, não detalhe operacional.
 */
export function resolverBraco(
  epochInicioISO: string,
  env: NodeJS.ProcessEnv = process.env,
): ResolucaoDeBraco {
  const caminho = env.NOX_P2_ASSIGNMENT;
  if (!caminho) return { ...CONTROLE, ok: false, motivo: "NOX_P2_ASSIGNMENT ausente" };
  const shaEsperado = env.NOX_P2_ASSIGNMENT_SHA256;
  if (!shaEsperado)
    return { ...CONTROLE, ok: false, motivo: "NOX_P2_ASSIGNMENT_SHA256 ausente" };
  let cru: Buffer;
  try {
    cru = readFileSync(caminho);
  } catch (e) {
    return { ...CONTROLE, ok: false, motivo: `ASSIGNMENT ilegível: ${String(e)}` };
  }
  const sha = createHash("sha256").update(cru).digest("hex");
  if (sha !== shaEsperado)
    return { ...CONTROLE, ok: false, motivo: `sha256 divergente (${sha.slice(0, 12)}…)` };
  let linhas: Designacao[];
  try {
    const parsed = JSON.parse(cru.toString("utf8")) as { epochs?: Designacao[] };
    linhas = parsed.epochs ?? [];
  } catch (e) {
    return { ...CONTROLE, ok: false, motivo: `ASSIGNMENT inválido: ${String(e)}` };
  }
  const linha = linhas.find((l) => l.epoch_inicio === epochInicioISO);
  if (!linha)
    return { ...CONTROLE, ok: false, motivo: `epoch ${epochInicioISO} ausente da sequência` };
  if (linha.arm === "control") return CONTROLE;
  if (!Number.isFinite(linha.w) || linha.w <= 0)
    return { ...CONTROLE, ok: false, motivo: `w inválido para tratamento: ${String(linha.w)}` };
  return { ok: true, arm: "treatment", w: linha.w };
}

interface DbMinimo {
  prepare(sql: string): { all(...a: unknown[]): unknown[] };
}

/**
 * Boost por candidato, para os chunks da população do estudo.
 *
 * A população é definida pelo **join autoritativo** com `p2_verdict.chunk_id` —
 * o elo registrado — e não por padrão de `source_file`. Duas implementações de
 * "que chunk é do estudo" escreveriam a população errada em silêncio.
 *
 * `W_OUTCOME = w · Δ_cut · severity_pain`, aditivo (a lição v3.4 do Paper 1: boost
 * multiplicativo empilhável é instável).
 *
 * ⚠️ Aplica a **regra de designação registrada** — um chunk por grupo de
 * assinatura, `argmin (C − base)/(Δ_cut·sev)` — com a constante `C` explícita
 * como parâmetro, porque ela está sob emenda: `C` foi registrada como
 * `CUT_FRESH = 0.7342`, um limiar que o `pick` não aplica. Manter explícita para
 * que a troca seja um diff, não uma reinterpretação.
 */
export function boostsParaCandidatos(
  db: DbMinimo,
  candidatos: { id: number; salienceBase: number }[],
  w: number,
  cDesignacao: number,
  /**
   * Inicio do epoch corrente, em ms. Quando presente, aplica o GATE DE
   * MATURIDADE registrado: so entra na populacao tratada o chunk escrito
   * >= 1 epoch (24 h) ANTES do inicio do epoch.
   *
   * §3:642 define `Opportunity` exigindo que o episodio tenha sido "written >= 1
   * epoch length before the epoch start", e §2:550 declara a consequencia:
   * "the chunk cannot act in the epoch it is written". A primeira versao deste
   * modulo NAO tinha o gate — impulsionava qualquer chunk de p2_verdict que
   * aparecesse no pool, o que contradiz o registro. Achado em 2026-08-21 ao
   * ligar o shadow com chunks reais.
   *
   * O ancora e `written_at` (o instante da ESCRITA), nao o timestamp da falha:
   * lock de 2026-08-16, §2 linha 202.
   */
  epochInicioMs?: number,
): Map<number, number> {
  const vazio = new Map<number, number>();
  if (w <= 0 || candidatos.length === 0) return vazio;
  const porId = new Map(candidatos.map((c) => [c.id, c.salienceBase]));
  const ids = [...porId.keys()];
  let linhas: { chunk_id: number; severity: string; sig_primary: string }[];
  const corte =
    epochInicioMs === undefined
      ? null
      : new Date(epochInicioMs - 86400000).toISOString().slice(0, 19).replace("T", " ");
  try {
    linhas = db
      .prepare(
        `SELECT chunk_id, severity, sig_primary FROM p2_verdict
          WHERE chunk_id IN (${ids.map(() => "?").join(",")})` +
          (corte === null ? "" : " AND written_at <= ?"),
      )
      .all(...(corte === null ? ids : [...ids, corte])) as typeof linhas;
  } catch {
    return vazio; // p2_verdict ausente (write path nunca acionado) — fail-open
  }
  if (linhas.length === 0) return vazio;

  // Designação: um por grupo de assinatura, o de menor w_min.
  const porSig = new Map<string, { chunk_id: number; sev: number; wMin: number }>();
  for (const l of linhas) {
    const sev = SEVERIDADE_PAIN[l.severity];
    if (sev === undefined || sev <= 0) continue; // S0 não tem chunk
    const base = porId.get(l.chunk_id);
    if (base === undefined) continue;
    const wMin = (cDesignacao - base) / (P2_DELTA_CUT * sev);
    const atual = porSig.get(l.sig_primary);
    if (!atual || wMin < atual.wMin) porSig.set(l.sig_primary, { chunk_id: l.chunk_id, sev, wMin });
  }
  const out = new Map<number, number>();
  for (const { chunk_id, sev } of porSig.values()) out.set(chunk_id, w * P2_DELTA_CUT * sev);
  return out;
}

/** Espelha `SEVERITY_PAIN` do write-path; duplicado aqui para não acoplar módulos. */
const SEVERIDADE_PAIN: Record<string, number> = {
  S0: 0,
  S1: 0.25,
  S2: 0.5,
  S3: 0.75,
  S4: 1.0,
};

/**
 * Data de inicio do epoch corrente, em ISO (YYYY-MM-DD).
 *
 * Fronteira registrada: 06:00 BRT = 09:00 UTC. Antes das 09:00 UTC o epoch
 * corrente comecou no dia anterior.
 */
export function epochInicioISO(nowMs: number): string {
  const d = new Date(nowMs);
  const antes = d.getUTCHours() < 9;
  const base = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  const ms = antes ? base - 86400000 : base;
  return new Date(ms).toISOString().slice(0, 10);
}

/**
 * Dose do modo `shadow`, declarada por env.
 *
 * O `shadow` mede ATIVACAO -- com que frequencia um boost de `w` deslocaria algo
 * -- e essa pergunta antecede o sorteio: nao ha ASSIGNMENT.json ainda. Por isso
 * `shadow` NAO resolve braco; le `NOX_P2_SHADOW_W`. Default 0 = nao computa nada.
 */
export function doseDeShadow(env: NodeJS.ProcessEnv = process.env): number {
  const w = Number(env.NOX_P2_SHADOW_W ?? "0");
  return Number.isFinite(w) && w > 0 ? w : 0;
}

/**
 * Constante da regra de designacao. Registrada como `CUT_FRESH = 0.7342` -- um
 * limiar que o `pick` nao aplica (ver BAR-RETRACTION-2026-08-20). Fica explicita
 * e sobrescrivel para que a emenda seja um diff, nao uma reinterpretacao.
 */
export function cDesignacao(env: NodeJS.ProcessEnv = process.env): number {
  const c = Number(env.NOX_P2_C_DESIGNACAO ?? "0.7342");
  return Number.isFinite(c) ? c : 0.7342;
}

let avisouFaltaDeLog = false;

/**
 * Log de decisao por brief, append-only NDJSON.
 *
 * `pruneEpochs(keep=3)` destroi o snapshot fisico em 3 dias, entao ESTE log tem
 * de bastar sozinho para replay. Espelha `logar()` do write-path, com duas
 * diferencas deliberadas:
 *
 *  1. **Sem caminho default.** A licao do PR #43 e que isolar o DB nao isola o
 *     log: com default, um teste rodando `composeBrief` num DB em memoria
 *     escreveria no log de replay de PRODUCAO. Exige `NOX_P2_SERVING_LOG`
 *     explicito; sem ele, nao escreve.
 *  2. **Nunca lanca.** O caminho de serving nao pode degradar por causa de log —
 *     `composeBrief` tem fail-open, e uma excecao aqui derrubaria o brief para
 *     `buildBrief`. Falta de config avisa UMA vez em stderr e segue.
 *
 * A ausencia do log com o modo ligado e defeito de operacao, nao de serving:
 * fica visivel no journal sem parar a frota.
 */
export function logarDecisaoDeServing(
  linha: Record<string, unknown>,
  env: NodeJS.ProcessEnv = process.env,
): void {
  const caminho = env.NOX_P2_SERVING_LOG;
  if (!caminho) {
    if (!avisouFaltaDeLog) {
      avisouFaltaDeLog = true;
      console.error(
        JSON.stringify({
          tag: "p2_serving_log_ausente",
          efeito: "decisoes NAO estao sendo persistidas — replay impossivel",
          conserto: "definir NOX_P2_SERVING_LOG no drop-in registrado",
        }),
      );
    }
    return;
  }
  try {
    mkdirSync(dirname(caminho), { recursive: true });
    appendFileSync(
      caminho,
      JSON.stringify({ ts: new Date().toISOString(), ...linha }) + "\n",
    );
  } catch (err) {
    console.error("[p2-serving] log falhou:", (err as Error).message);
  }
}

/** Reseta o aviso-uma-vez. Só para teste. */
export function _resetAvisoDeLog(): void {
  avisouFaltaDeLog = false;
}

/** Inicio do epoch (ISO YYYY-MM-DD) em ms UTC, na fronteira registrada 09:00. */
export function epochInicioMs(epochISO: string): number {
  return Date.parse(epochISO + "T09:00:00Z");
}
