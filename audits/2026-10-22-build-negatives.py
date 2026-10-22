#!/usr/bin/env python3
"""Build negatives for the PT-BR set that are TRUE BY CONSTRUCTION.

Item 8 (abstention) needs questions with no answer in the corpus. Measured on
2026-10-22, an LLM judge cannot supply them: given a false-premise query it wrote
in its own reason that the premise was wrong and still returned
`premissa_confere: true`. So the negatives here are not judged at all — they are
*constructed* and then *verified mechanically*.

A candidate survives only if its distinctive token occurs ZERO times in the whole
corpus, checked three ways because each misses something the others catch:

  1. raw substring over every chunk_text, accent- and case-folded — catches the
     token inside a larger word, which an index would not;
  2. FTS5 MATCH on the quoted token — catches what the retriever can actually
     reach, which is what abstention is about;
  3. kg_entities by name — the graph serves triples beside the chunks.

If the token occurs anywhere, the candidate is dropped: a question whose subject
appears in the corpus is not provably unanswerable, and an unprovable negative is
worse than none, because failures to abstain cannot be attributed.

Read-only: mode=ro, writes only its output.
"""
import json, re, sqlite3, sys, unicodedata

DB  = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
OUT = sys.argv[1]

# Candidatos construídos a partir de padrões REAIS do corpus (subcomandos como
# `nox-mem vectorize`, serviços `nox-*`, variáveis `NOX_*`, tabelas `kg_*`), de
# modo que a pergunta pareça pertencer — uma negativa implausível torna a
# abstenção trivial e não mede nada.
CAND = [
  ("rebalance",        "como rodar o nox-mem rebalance em produção"),
  ("defragment",       "o que faz o subcomando nox-mem defragment"),
  ("rehydrate",        "quando usar nox-mem rehydrate depois de um restore"),
  ("bisect",           "como o nox-mem bisect encontra o chunk que quebrou"),
  ("quorum",           "qual o quorum mínimo para o shadow mode virar active"),
  ("nox-ledger",       "qual a porta do nox-ledger"),
  ("nox-sentinel",     "o que o nox-sentinel monitora"),
  ("openclaw-arbiter", "como o openclaw-arbiter resolve conflito entre agentes"),
  ("NOX_RERANK_MODE",  "o que faz a variável NOX_RERANK_MODE"),
  ("NOX_GRAPH_TTL",    "qual o default de NOX_GRAPH_TTL"),
  ("NOX_ANSWER_THRESHOLD", "qual o piso configurado em NOX_ANSWER_THRESHOLD"),
  ("chunk_lineage",    "o que a tabela chunk_lineage guarda"),
  ("kg_claims",        "como a tabela kg_claims se relaciona com kg_relations"),
  ("tier_decay",       "como funciona o tier_decay"),
  ("pain_floor_v2",    "o que mudou no pain_floor_v2"),
  ("salience v4",      "quais pesos a salience v4 usa"),
  ("vec_shards",       "quantos vec_shards o índice usa"),
  ("reflect_quota",    "qual o reflect_quota por agente"),
  ("brief_pinning",    "como funciona o brief_pinning"),
  ("crystallize-batch","como rodar crystallize-batch sem travar o gateway"),
  ("kg-rebuild-shard", "o que o kg-rebuild-shard faz"),
  ("embed_cache_ttl",  "qual o embed_cache_ttl padrão"),
  ("nox-mem fsck",     "como o nox-mem fsck repara o índice"),
  ("tombstone_quarantine", "quanto tempo dura o tombstone_quarantine"),
  ("agent_quota_table","o que a agent_quota_table controla"),
  ("retention_override","como aplicar um retention_override por arquivo"),
  ("semantic_floor",   "qual o semantic_floor usado no RRF"),
  ("chunk_provenance_log", "o que entra no chunk_provenance_log"),
  ("NOX_DUAL_WRITE",   "para que serve NOX_DUAL_WRITE"),
  ("kg_entity_merge",  "como o kg_entity_merge decide fundir duas entidades"),
]

def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
total = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

# 1. substring cru sobre todo o corpus — uma varredura, todos os candidatos
needles = [(tok, fold(tok)) for tok, _ in CAND]
hits_raw = {tok: 0 for tok, _ in CAND}
for (t,) in con.execute("SELECT chunk_text FROM chunks"):
    ft = fold(t)
    for tok, n in needles:
        if n in ft:
            hits_raw[tok] += 1

out = []
for tok, pergunta in CAND:
    # 2. o que o retriever alcança
    try:
        fts = con.execute("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH ?",
                          (" AND ".join(f'"{w}"' for w in re.findall(r"[\w]{2,}", tok)),)).fetchone()[0]
        fts_err = None
    except sqlite3.OperationalError as e:
        fts, fts_err = -1, str(e)
    # 3. o grafo
    kg = con.execute("SELECT COUNT(*) FROM kg_entities WHERE lower(name) LIKE ?",
                     (f"%{fold(tok)}%",)).fetchone()[0]
    limpo = hits_raw[tok] == 0 and fts == 0 and kg == 0
    out.append({"token": tok, "query": pergunta, "raw_hits": hits_raw[tok],
                "fts_hits": fts, "fts_error": fts_err, "kg_hits": kg, "clean": limpo})

limpos = [o for o in out if o["clean"]]
print(f"corpus: {total} chunks")
print(f"candidatos: {len(out)}  ·  LIMPOS (zero em todas as três vias): {len(limpos)}")
print("\ndescartados:")
for o in out:
    if not o["clean"]:
        print(f"  {o['token']:24s} raw={o['raw_hits']:<5} fts={o['fts_hits']:<5} kg={o['kg_hits']}")
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
