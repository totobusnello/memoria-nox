# Q4 Cost Log

| Run | Date | Systems | Corpus | Cost (USD) | Notes |
|---|---|---|---|---:|---|
| Sat wider partial | 2026-05-23 | nox_mem + mem0 (500-cap) + agentmemory (partial) | nox_mem: full; mem0: 500/6830; agentmemory: 1401/6830 | ~$0.07 | mem0 OpenAI embed 500 chunks × ~$0.0001/embed ≈ $0.05; nox_mem FTS5 = $0.00; agentmemory = $0.00 |
| Previous smoke | 2026-05-23 | nox_mem + mem0 (n=20) + agentmemory (n=5) | partial | ~$0.10 | Earlier partial runs from session |

## Cost breakdown — 2026-05-23 wider partial

- **nox_mem**: $0.00 — FTS5 local eval DB, no API calls
- **mem0 (500-cap)**: ~$0.05 — 500 × OpenAI `text-embedding-3-small` embeds (no LLM extraction, `MEM0_SKIP_LLM_EXTRACTION=1` default)
- **agentmemory**: $0.00 — iii-engine local REST, no external API
- **zep/letta/evermind**: $0.00 — skipped
- **Total**: ~$0.05–0.07

## Cost to run full corpus

| System | Est. full cost | Blocker |
|---|---|---|
| mem0 (full 6830 chunks) | ~$0.68 (embed only) / ~$13–15 (embed + LLM extraction) | OpenAI rate limit + time (~2h) |
| agentmemory (full 6830 chunks) | $0.00 | Time (~2h at 100/min ingest rate) |
| Zep | $0.00 | Docker required |
| Letta | ~$0.10 | LETTA_API_KEY + Docker |
| nox_mem (prod mode) | $0.00 (Gemini flash-lite) | VPS availability for Gemini hybrid |
