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
 * A chave de ordenação da designação. O layout de bytes vive AQUI e em
 * `paper2-interventional/designation_verify.py`, e em nenhum outro lugar.
 *
 * `SHA256( seed_hex ‖ "|" ‖ chunk_id )`, tudo ASCII: a seed é a string hex
 * minúscula (NÃO os 32 bytes decodificados), o separador é obrigatório, o
 * chunk_id é o inteiro em decimal.
 *
 * ⚠️ O separador não é decorativo. `extract_episodes.py:226` faz
 * `sha256(seed + episode_id)` sem ele e reproduziu 293 de 1.576 episódios
 * (`EXTENSION-SEED-2026-08-11.md:49-64`). Havia três implementações inline da
 * derivação neste repo e nenhuma compartilhada.
 *
 * ⚠️ `sig_primary` NÃO entra na chave, e é deliberado: todos os 19 valores reais
 * contêm `|`, o próprio separador, o que tornaria o layout não-injetivo. Como cada
 * chunk pertence a exatamente um grupo (verificado: 0 de 55 em mais de um, uma vez
 * excluídas as linhas S0, que têm `chunk_id NULL`), o campo não carregaria
 * informação — só ambiguidade. Registro em `DECISION-designacao-2026-08-25.md`, §B.
 */
export function chaveDeDesignacao(seedHex: string, chunkId: number): string {
  return createHash("sha256").update(`${seedHex}|${chunkId}`, "ascii").digest("hex");
}

/**
 * Deriva o conjunto designado sobre a tabela INTEIRA — um chunk por grupo de
 * assinatura, o de menor chave.
 *
 * Global, não condicional ao pool: a designação de um grupo não pode depender de
 * quem apareceu no brief de agora. Sob a regra anterior isso era invisível porque
 * cada fatia recomputava o argmin local, e `boostsParaCandidatos` é chamada ≥2
 * vezes por brief com fatias diferentes (`brief.ts:714`, `:753`, `:843-851`).
 *
 * ⚠️ Esta função é a DERIVAÇÃO, usada para produzir a declaração de seed e nos
 * testes. Ela NÃO é a fonte do que se serve: `p2_verdict` é tabela viva
 * (`write-path.ts:189` insere), então recomputar a cada brief faria o conjunto
 * designado mudar quando uma adjudicação nova entrasse — o oposto de congelado.
 * Quem serve lê o arquivo preso por sha256 em `carregarDesignados`.
 *
 * Filtra `severity` positiva E `chunk_id IS NOT NULL`. Hoje as duas condições
 * coincidem exatamente (225 linhas S0, todas com chunk_id nulo), mas a coincidência
 * é fato do dado e não restrição de schema — se divergirem, quero as duas mordendo.
 */
export function designadosGlobais(db: DbMinimo, seedHex: string): Map<string, number> {
  const linhas = db
    .prepare(
      `SELECT DISTINCT sig_primary, chunk_id FROM p2_verdict
        WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2','S3','S4')`,
    )
    .all() as { sig_primary: string; chunk_id: number }[];
  const grupos = new Map<string, number[]>();
  for (const l of linhas) {
    const g = grupos.get(l.sig_primary);
    if (g) g.push(l.chunk_id);
    else grupos.set(l.sig_primary, [l.chunk_id]);
  }
  const out = new Map<string, number>();
  for (const [sig, ids] of grupos) {
    // Ordena por (chave, chunk_id). A chave já é total na prática; o segundo termo
    // torna o desempate explícito em vez de herdado da ordem de linhas do SQLite —
    // exatamente o defeito que esta regra existe para consertar.
    let melhor = ids[0];
    let melhorChave = chaveDeDesignacao(seedHex, melhor);
    for (const id of ids.slice(1)) {
      const k = chaveDeDesignacao(seedHex, id);
      if (k < melhorChave || (k === melhorChave && id < melhor)) {
        melhor = id;
        melhorChave = k;
      }
    }
    out.set(sig, melhor);
  }
  return out;
}

/** sha256 canônico do conjunto designado. Mesma serialização do Python. */
export function impressaoDoConjunto(desig: Map<string, number>): string {
  const ordenado = [...desig.keys()].sort();
  const canon = `{${ordenado.map((k) => `${JSON.stringify(k)}:${desig.get(k)}`).join(",")}}`;
  return createHash("sha256").update(canon, "utf8").digest("hex");
}

export interface DesignadosCarregados {
  ok: boolean;
  ids: Set<number>;
  seed: string | null;
  motivo?: string;
}

const SEM_DESIGNADOS: DesignadosCarregados = { ok: false, ids: new Set(), seed: null };

/**
 * Lê o conjunto designado CONGELADO, preso por caminho + sha256.
 *
 * Mesmo par de env vars que `resolverBraco` usa, mesma razão: divergência de hash
 * ⇒ recusa, porque servir tratamento a partir de um conjunto não verificado é pior
 * que não servir. Ausente ⇒ mapa vazio, e o chamador grita.
 *
 * O arquivo é exatamente a saída de `designation_verify.py`, e é o que a declaração
 * de seed publica. Não há caminho default: a lição do PR #43 é que isolar o DB não
 * isola o log, e um default aqui serviria tratamento em teste.
 */
export function carregarDesignados(
  env: NodeJS.ProcessEnv = process.env,
): DesignadosCarregados {
  const caminho = env.NOX_P2_DESIGNATION;
  if (!caminho) return { ...SEM_DESIGNADOS, motivo: "NOX_P2_DESIGNATION ausente" };
  const shaEsperado = env.NOX_P2_DESIGNATION_SHA256;
  if (!shaEsperado)
    return { ...SEM_DESIGNADOS, motivo: "NOX_P2_DESIGNATION_SHA256 ausente" };
  let cru: Buffer;
  try {
    cru = readFileSync(caminho);
  } catch (e) {
    return { ...SEM_DESIGNADOS, motivo: `DESIGNATION ilegível: ${String(e)}` };
  }
  const sha = createHash("sha256").update(cru).digest("hex");
  if (sha !== shaEsperado)
    return { ...SEM_DESIGNADOS, motivo: `sha256 divergente (${sha.slice(0, 12)}…)` };
  let doc: { seed?: string; designados?: Record<string, number> };
  try {
    doc = JSON.parse(cru.toString("utf8"));
  } catch (e) {
    return { ...SEM_DESIGNADOS, motivo: `DESIGNATION inválido: ${String(e)}` };
  }
  const designados = doc.designados;
  if (!designados || typeof designados !== "object")
    return { ...SEM_DESIGNADOS, motivo: "campo `designados` ausente" };
  const ids = new Set<number>();
  for (const v of Object.values(designados)) {
    if (!Number.isInteger(v)) return { ...SEM_DESIGNADOS, motivo: `chunk_id não inteiro: ${String(v)}` };
    ids.add(v);
  }
  if (ids.size === 0) return { ...SEM_DESIGNADOS, motivo: "conjunto designado vazio" };
  return { ok: true, ids, seed: typeof doc.seed === "string" ? doc.seed : null };
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
 * ⚠️ Aplica a regra de designação **substituta**, decidida em 2026-08-26
 * (`DECISION-designacao-2026-08-25.md`, opção B): sorteio pseudoaleatório com seed
 * declarada, um chunk por grupo, `argmin SHA256(seed ‖ "|" ‖ chunk_id)`.
 *
 * A regra ANTERIOR — `argmin (C − base)/(Δ_cut·sev)` com `C = CUT_FRESH = 0.7342`
 * — foi removida, não deixada como código morto, por três defeitos medidos e
 * retratados na `AMENDMENT-v1.12.md` (retratações 3, 4, 13, 26, 27):
 *
 *  1. `C` era um limiar que o `pick` nunca aplica — a emenda retrata o referente;
 *  2. o desempate registrado nomeava `created_at`, coluna que não existe em
 *     `p2_verdict` — não era não-implementado, era não-implementável;
 *  3. `w_min` derivava de `salienceBase`, que inclui
 *     `0.20 · log1p(access_count)/log(1000)`, e `access_count` é mutável por
 *     tráfego de busca exógeno ⇒ a designação não era função só de dados
 *     congelados. Empate exato em 4 dos 7 grupos multi-membro, e nesses o
 *     designado saía da ordem incidental de linhas do SQLite.
 *
 * Consequência de tipo: `salienceBase` deixou de ser lido. O parâmetro se estreita
 * para `{ id }` justamente para que o compilador prove que não é mais consultado.
 */
export function boostsParaCandidatos(
  db: DbMinimo,
  candidatos: { id: number }[],
  w: number,
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
  env: NodeJS.ProcessEnv = process.env,
): Map<number, number> {
  const vazio = new Map<number, number>();
  if (w <= 0 || candidatos.length === 0) return vazio;

  const d = carregarDesignados(env);
  if (!d.ok) {
    // Não neutro: converte tratamento em controle e enviesa pro nulo, igual à
    // falha de resolução de braço. Grita uma vez por processo e é contado.
    if (!avisouFaltaDeDesignacao) {
      avisouFaltaDeDesignacao = true;
      console.error(
        JSON.stringify({ tag: "p2_designation_seed_ausente", motivo: d.motivo ?? null }),
      );
    }
    return vazio;
  }
  conferirDrift(db, d, env);

  // Interseção com o pool. O conjunto designado é GLOBAL e congelado: um grupo
  // cujo designado não apareceu neste pool simplesmente não recebe boost — não se
  // promove o segundo colocado, porque isso reintroduziria dependência do pool.
  const ids = candidatos.map((c) => c.id).filter((id) => d.ids.has(id));
  if (ids.length === 0) return vazio;

  // Gate de maturidade e severidade vêm do DB, e SÓ para os designados.
  const corte =
    epochInicioMs === undefined
      ? null
      : new Date(epochInicioMs - 86400000).toISOString().slice(0, 19).replace("T", " ");
  let linhas: { chunk_id: number; severity: string }[];
  try {
    linhas = db
      .prepare(
        `SELECT chunk_id, severity FROM p2_verdict
          WHERE chunk_id IN (${ids.map(() => "?").join(",")})` +
          (corte === null ? "" : " AND written_at <= ?"),
      )
      .all(...(corte === null ? ids : [...ids, corte])) as typeof linhas;
  } catch {
    return vazio; // p2_verdict ausente (write path nunca acionado) — fail-open
  }

  const out = new Map<number, number>();
  for (const l of linhas) {
    const sev = SEVERIDADE_PAIN[l.severity];
    if (sev === undefined || sev <= 0) continue; // S0 não tem chunk
    // `set`, não `+=`: um chunk designado em dois grupos recebe UM boost. Hoje não
    // ocorre (0 de 55 em mais de um grupo), e a asserção do teste trava isso.
    out.set(l.chunk_id, w * P2_DELTA_CUT * sev);
  }
  return out;
}

let avisouFaltaDeDesignacao = false;
let conferiuDrift = false;

/** Só para teste: o aviso é uma-vez-por-processo e a ordem dos testes o consumiria. */
export function _resetAvisoDeDesignacao(): void {
  avisouFaltaDeDesignacao = false;
  conferiuDrift = false;
}

/**
 * Guarda de drift: recomputa a designação sobre `p2_verdict` como está AGORA e
 * compara com o conjunto congelado. Divergência ⇒ grita; o arquivo continua sendo
 * a autoridade.
 *
 * Existe porque `p2_verdict` é tabela viva. Se uma adjudicação nova entrar num
 * grupo, o argmin daquele grupo pode mudar, e sem esta comparação o conjunto
 * servido e o conjunto derivável divergiriam em silêncio — a diferença entre
 * "congelado" e "congelado e verificado". Uma vez por processo: a query é de 55
 * linhas, mas o brief é caminho quente.
 */
function conferirDrift(db: DbMinimo, d: DesignadosCarregados, env: NodeJS.ProcessEnv): void {
  if (conferiuDrift || d.seed === null) return;
  conferiuDrift = true;
  if (env.NOX_P2_DESIGNATION_SKIP_DRIFT === "1") return;
  let vivo: Map<string, number>;
  try {
    vivo = designadosGlobais(db, d.seed);
  } catch {
    return; // p2_verdict ausente — o fail-open do caminho principal já cobre
  }
  const idsVivos = new Set(vivo.values());
  const faltando = [...d.ids].filter((i) => !idsVivos.has(i));
  const sobrando = [...idsVivos].filter((i) => !d.ids.has(i));
  if (faltando.length || sobrando.length) {
    console.error(
      JSON.stringify({
        tag: "p2_designation_drift",
        congelados: d.ids.size,
        derivados_agora: idsVivos.size,
        no_arquivo_e_nao_derivado: faltando.sort((a, b) => a - b),
        derivado_e_nao_no_arquivo: sobrando.sort((a, b) => a - b),
      }),
    );
  }
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

// `cDesignacao()` foi REMOVIDA em 2026-08-26, junto com `NOX_P2_C_DESIGNACAO`.
// Devolvia `CUT_FRESH = 0.7342`, um limiar que o `pick` nunca aplica, e a emenda
// v1.12 retrata o referente (retratações 3, 4, 13). Deixar uma constante retratada
// viva "para o diff ficar legível" é convite a reuso — a regra que a consumia foi
// substituída inteira (ver `boostsParaCandidatos` e
// `DECISION-designacao-2026-08-25.md`). Se aparecer numa branch antiga, é do
// período pré-emenda e não deve voltar.

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
