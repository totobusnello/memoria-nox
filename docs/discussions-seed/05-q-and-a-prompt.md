# Q&A: Ask anything — deployment, scaling, integration, methodology

Open thread for questions about nox-mem. No question is too basic or too deep.

## Common categories

**Production deployment**
- VPS sizing — what spec do you actually need for N chunks?
- Cost — what does running nox-mem at scale realistically cost?
- Monitoring — what to watch (`/api/health`, disk, latency P95)?
- Backup and recovery — how does `withOpAudit` and the nightly backup work?

**Scaling**
- When does SQLite stop being the right choice?
- What happens to search latency at 250k chunks vs 70k?
- When would you graduate to a distributed vector store?

**Integration**
- How do I wire nox-mem to LangChain / LlamaIndex / CrewAI?
- MCP server setup — which hosts have you tested it on?
- Session ID management — how do you share context across CLI and API?

**Methodology and benchmarks**
- How do you interpret nDCG@10 and MRR in the context of memory retrieval?
- How does your eval corpus compare to LongMemEval or LoCoMo?
- What does the ablation setup look like for adding a new ranking signal?

**Roadmap**
- When will feature X land?
- Is there a timeline for provider abstraction (Ollama support)?

## Before posting

Check `docs/FAQ.md` first — common operational questions are already answered there. If your question isn't covered, post here.

## Reply SLA

Best-effort 48h for straightforward questions. Some questions need deeper investigation and may take longer, or may get parked as research items. If a question surfaces a real bug or missing doc, I'll file an issue and link it back here.

Go ahead.
