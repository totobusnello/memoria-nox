# Suggested Interview Questions — nox-mem

For podcast hosts, journalists, and conference moderators who want to give Toto
Busnello a useful on-ramp. These questions are designed to surface the most
interesting material without requiring deep technical preparation.

Feel free to use any of these verbatim, adapt them, or ignore them entirely.
For a pre-interview briefing call, contact lab@nuvini.com.br.

---

## Origin Story

1. **Where did this start?** What was the specific moment or frustration that made
   you think "I need to build a memory system from scratch"?

2. **You've operated at board and advisor level across technology, finance, and
   real estate. That's not the typical background for someone publishing AI
   infrastructure research. How did those experiences shape what you built?**

3. **The name "nox-mem" — nox is Latin for night. Is there a story behind that?**

---

## The Core Ideas

4. **You use the phrase "pain-weighted salience." Can you explain that to someone
   who has never thought about how AI agents remember things?**

5. **Most AI memory systems use some form of semantic similarity search. What's
   wrong with that as the primary signal?**

6. **The system has three retrieval layers — BM25, semantic embeddings, and a
   knowledge graph. Why three? What does each one catch that the others miss?**

---

## The Hard Engineering Decisions

7. **You chose SQLite over a dedicated vector database. A lot of people would
   consider that an unusual choice for a production AI system. Walk me through
   that decision.**

8. **You published eleven ablation studies before launch, each with runner code
   attached. That's a level of methodological rigor that's unusual outside of
   academic research. Why did you impose that discipline on yourself?**

9. **There's an experiment in the audit log called "G6" where you thought you'd
   found a regression and it turned out to be a database swap artifact. What
   happened, and what did that teach you?**

10. **The "Hard Mutex" configuration — what is it, and why did it take four
    separate ablation experiments (G10 through G10d) to get it right?**

---

## Failure and Reversal

11. **You rolled back a production change within six hours. What happened, and
    what does that incident say about how you run this system?**

12. **At what point did you realize you'd been measuring things incorrectly, and
    what did you do about it?**

---

## Personal Motivation

13. **You built this as an independent project, outside of any company or
    institution. Why not do this inside one of the boards or funds you're part of?**

14. **The three strategic pillars of nox-mem are Quality, Autonomy, and Product —
    in that order. Why that order? What happens when you invert it?**

15. **"Yours by design" is in the tagline. What does ownership of AI memory mean
    to you, and why do you think it matters beyond just a technical preference?**

---

## Looking Forward

16. **You have a benchmark comparison against five competitors scheduled for
    launch. What happens if nox-mem doesn't win?**

17. **The roadmap mentions a local embedding pathway — running without Gemini API.
    Is that an admission that the current design has a dependency problem?**

18. **What does success look like for nox-mem one year from now? Not in terms of
    GitHub stars — in terms of what it changes for the people using it.**
