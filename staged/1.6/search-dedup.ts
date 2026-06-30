/**
 * search-dedup.ts — 4-layer diversity filter for hybrid search results.
 *
 * Fase 1.6 — aplicado DEPOIS do RRF fusion, não interfere com scoring.
 * Inspiração: garrytan/gbrain search/dedup.ts.
 *
 * Layers (na ordem):
 *   1. Top 3 per source_file (evita 8 chunks do mesmo arquivo)
 *   2. Jaccard text-similarity >0.85 entre prefixos de 180 chars removido
 *      (dedup textual sem custo de embedding; captura consolidations próximas)
 *   3. No single chunk_type pode ser >60% do resultado final
 *      (força diversidade entre lesson / decision / code / conversation)
 *   4. Max 2 chunks per source_file no resultado final (limit-wise)
 *
 * Não perde resultados únicos: se limit=5 e dedup cortar pra 3, 3 é o certo.
 * Melhor cobertura < ruído repetido.
 */

import type { SearchResult } from "./search.js";

const SIMILARITY_THRESHOLD = 0.85;
const PREFIX_LEN = 180;
const MAX_PER_FILE_PRE = 3;
const MAX_PER_FILE_FINAL = 2;
const TYPE_SATURATION_RATIO = 0.6;

/**
 * Jaccard similarity em shingles de 3 palavras. Cheap, good enough for
 * "este chunk é quase o mesmo que aquele".
 */
function jaccardSim(a: string, b: string): number {
  const shingles = (s: string): Set<string> => {
    const tokens = s.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);
    const sh = new Set<string>();
    for (let i = 0; i < tokens.length - 2; i++) sh.add(tokens[i] + " " + tokens[i + 1] + " " + tokens[i + 2]);
    if (sh.size === 0 && tokens.length > 0) sh.add(tokens.join(" "));
    return sh;
  };
  const A = shingles(a.substring(0, PREFIX_LEN));
  const B = shingles(b.substring(0, PREFIX_LEN));
  if (A.size === 0 || B.size === 0) return 0;
  let inter = 0;
  for (const x of A) if (B.has(x)) inter++;
  const union = A.size + B.size - inter;
  return union > 0 ? inter / union : 0;
}

export function dedupe(results: SearchResult[], limit: number): SearchResult[] {
  if (results.length === 0) return results;

  // Layer 1: max MAX_PER_FILE_PRE por source_file (preserva ordem de score)
  const perFileCount = new Map<string, number>();
  const afterFileCap: SearchResult[] = [];
  for (const r of results) {
    const c = perFileCount.get(r.source_file) || 0;
    if (c < MAX_PER_FILE_PRE) {
      afterFileCap.push(r);
      perFileCount.set(r.source_file, c + 1);
    }
  }

  // Layer 2: remove near-duplicates por Jaccard
  const afterJaccard: SearchResult[] = [];
  for (const r of afterFileCap) {
    const isDup = afterJaccard.some((kept) => jaccardSim(r.chunk_text, kept.chunk_text) >= SIMILARITY_THRESHOLD);
    if (!isDup) afterJaccard.push(r);
  }

  // Layer 3: satura no máximo TYPE_SATURATION_RATIO de um único chunk_type
  // Aplica só se há diversidade disponível — senão retorna o que tem.
  const maxOfType = Math.max(1, Math.ceil(limit * TYPE_SATURATION_RATIO));
  const typeCount = new Map<string, number>();
  const afterTypeCap: SearchResult[] = [];
  const benched: SearchResult[] = [];
  for (const r of afterJaccard) {
    const c = typeCount.get(r.chunk_type) || 0;
    if (c < maxOfType) {
      afterTypeCap.push(r);
      typeCount.set(r.chunk_type, c + 1);
    } else {
      benched.push(r);
    }
  }
  // Se não chegamos no limit, recuperamos do banco (melhor ter mais resultados)
  while (afterTypeCap.length < limit && benched.length > 0) {
    afterTypeCap.push(benched.shift()!);
  }

  // Layer 4: final cap MAX_PER_FILE_FINAL por source_file
  const finalFileCount = new Map<string, number>();
  const final: SearchResult[] = [];
  for (const r of afterTypeCap) {
    const c = finalFileCount.get(r.source_file) || 0;
    if (c < MAX_PER_FILE_FINAL) {
      final.push(r);
      finalFileCount.set(r.source_file, c + 1);
    }
    if (final.length >= limit) break;
  }

  return final;
}
