# Key Quotes — nox-mem

Pre-approved soundbites for press use. All may be attributed to
**Toto Busnello, creator of nox-mem**.

Quotes may be used verbatim or paraphrased. No further permission required.
For fresh quotes or follow-up, contact lab@nuvini.com.br.

---

## On Autonomy and Vendor Independence

> "Memory for LLM agents shouldn't lock you into a vendor's cloud. Your agent's
> history of what worked and what hurt belongs to you — in a file you can read,
> copy, and delete."

> "SQLite is not a compromise. It is a philosophy. You own the file. You own the
> memory. No subscription, no API rate limit on your own history."

> "Every cloud memory service I evaluated had the same fine print: your data
> lives in their infrastructure. nox-mem's answer to that is a .db file on your
> machine."

---

## On Pain-Weighted Salience

> "Pain-weighted salience means agents remember the things that hurt to forget."

> "Cosine similarity doesn't know what mattered. It knows what was similar. Those
> are very different questions."

> "The pain score is the design primitive I wish every memory system had. When
> you ingest a production outage lesson, you mark it 1.0. When you ingest a
> meeting note, you mark it 0.2. The formula does the rest."

> "An experienced colleague doesn't retrieve the most semantically similar memory.
> They retrieve the one that shaped their judgment. nox-mem tries to approximate
> that."

---

## On Open Methodology

> "Every benchmark we publish has the runner code attached — no hidden methodology."

> "I ran eleven ablation experiments before shipping a single scoring change. Not
> because it was fast. Because it was the only honest way to know if I was
> improving things or fooling myself."

> "Open methodology is the only credible foundation for memory system comparisons.
> If you can't reproduce the number, the number is marketing."

> "Pre-registration is how clinical trials earn trust. I applied the same
> discipline to retrieval experiments. Pre-state the hypothesis, run the eval,
> publish the result — good or bad."

---

## On Deployment Simplicity

> "The single-file SQLite deployment makes nox-mem the antithesis of MLOps sprawl."

> "You should be able to run production-grade AI memory on the same laptop you
> write code on. Not because it doesn't scale — because complexity is a cost that
> should be earned."

> "Node.js, SQLite, and a Gemini API key. That's the full dependency list. I want
> an experienced engineer to be able to read every layer of the stack."

> "The hardest engineering decision I made was choosing not to build a distributed
> system. Simplicity is defensible. Complexity needs to justify itself."

---

## On Benchmarks and Cross-System Comparison

> "When you read nDCG@10 0.8 from a competitor, ask one question first: how
> much of the retrieval corpus was actually ingested? Seven percent ingested
> means ninety-three percent of real queries land in a dead zone."

> "We published two nox-mem numbers — FTS5-only and Gemini hybrid — because
> hiding the FTS5 baseline would be dishonest. The 0.3753 is the fair comparison
> point for BM25 systems. The 0.6380 is what happens when you add semantic search.
> Both numbers matter."

> "Letta is 2000× slower on retrieval latency. That is not a bug. It is an
> architectural choice. Their system reasons before it retrieves. The question
> is whether your use case needs reasoning or speed. The honest answer depends
> on what you're building."

> "We had to mark two competitors as 'not evaluated' in the COMPARISON table.
> That is embarrassing to publish. It would have been easier to skip them
> silently or say 'results pending.' I'd rather say: Zep requires an OpenAI
> key our protocol doesn't inject; EverMind's repo returned 404. Those are
> real facts, and they matter."

---

## On the Broader AI Infrastructure Moment

> "We are in the phase of AI infrastructure where every vendor is racing to become
> the memory layer. I think that's the wrong frame. Memory should be owned by the
> entity whose experience it represents."

> "The paper is CC BY 4.0. Not because I'm generous. Because if the methodology
> is right, I want people to build on it. And if it's wrong, I want to be
> corrected in public."

> "Benchmarks without runner code are opinions. I'm publishing runner code."

> "The Q/A/P framework — Quality, Autonomy, Product — is in that order on
> purpose. Numbers first. Then freedom from lock-in. Then the interface people
> actually use. If you invert that order, you get beautiful products with
> unmeasured quality and permanent vendor dependency."
