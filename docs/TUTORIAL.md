# Build Your First Memory-Enabled Agent

> **Estimated time:** ~30 minutes  
> **Prerequisite:** [QUICKSTART.md](QUICKSTART.md) completed, nox-mem running locally

This tutorial walks you through building a minimal CLI chatbot that **actually remembers** — across sessions, across restarts. By the end you'll have a working Python script that retrieves relevant past memories before replying, stores new ones after each turn, and surfaces pain-weighted context when things matter most.

Jump to any section:

| Step | Topic |
|---|---|
| §1 | [What we'll build](#1-what-well-build) |
| §2 | [Prerequisites](#2-prerequisites) |
| §3 | [Verify nox-mem is reachable](#3-step-1-verify-nox-mem-is-reachable) |
| §4 | [Ingest a seed chunk](#4-step-2-ingest-a-seed-chunk) |
| §5 | [Build the search function](#5-step-3-build-the-search-function) |
| §6 | [Build the ingest function](#6-step-4-build-the-ingest-function) |
| §7 | [Compose the prompt](#7-step-5-compose-the-prompt) |
| §8 | [Call your LLM](#8-step-6-call-your-llm) |
| §9 | [Tie it together](#9-step-7-tie-it-together) |
| §10 | [Add pain-weighted feedback](#10-step-8-add-pain-weighted-feedback) |
| §11 | [Try USE-CASES patterns](#11-step-9-try-use-cases-patterns) |
| §12 | [Going to production](#12-step-10-going-to-production) |
| §13 | [Troubleshooting](#13-troubleshooting) |
| §14 | [What's next](#14-whats-next) |
| §15 | [Complete code: my_agent.py](#15-complete-code-my_agentpy) |

---

## §1 What we'll build

A minimal **memory-enabled chatbot** — a single Python script (`my_agent.py`) that:

1. Accepts input from the user
2. Searches nox-mem for relevant prior context before replying
3. Composes a prompt: system instructions + retrieved memories + current input
4. Calls an LLM (Gemini, OpenAI, Anthropic — or a local echo stub if you prefer)
5. Stores the conversation turn back into nox-mem
6. Lets the user flag frustration (pain score `0.7`) so those chunks rank higher next time
7. Repeats until `/quit`

The key insight: memories accumulated in session 1 are **automatically retrieved** in session 2. The agent gets smarter the more you talk to it, without you touching any code.

This skeleton is deliberately minimal. Once it works, you'll recognize it as the foundation behind every pattern in [USE-CASES.md](USE-CASES.md).

---

## §2 Prerequisites

Before starting:

- **QUICKSTART completed** — nox-mem is installed, built, and the API is running locally (`node dist/index.js` or `nox-mem-api`)
- **Python 3.10+** — check with `python3 --version`
- **`requests` library** — `pip install requests` (only stdlib + requests needed)
- **Gemini API key** (optional) — free tier at [aistudio.google.com](https://aistudio.google.com). If you don't have one, the tutorial ships an echo stub so you can follow every step without it
- **~30 minutes** of focused time

No Docker, no database setup, no cloud service. nox-mem runs on your disk.

---

## §3 Step 1: Verify nox-mem is reachable

Before writing any code, confirm the API is up:

```bash
curl http://localhost:18802/api/health | jq '{schemaVersion, totalChunks, vectorCoverage}'
```

Expected output:

```json
{
  "schemaVersion": 10,
  "totalChunks": 1234,
  "vectorCoverage": {
    "embedded": 1234,
    "total": 1234,
    "pct": 100
  }
}
```

What each field means:

| Field | What it tells you |
|---|---|
| `schemaVersion` | Should be 10 (current) |
| `totalChunks` | How many memory chunks are indexed — 0 is fine if you just installed |
| `vectorCoverage.pct` | Should be 100 — if lower, run `node dist/index.js vectorize` |

**Not working?** Jump to [QUICKSTART.md — §5 Troubleshooting](QUICKSTART.md) first, then come back here.

---

## §4 Step 2: Ingest a seed chunk

Let's give the agent its first memory so you can see retrieval working from the start.

Create a preference file:

```bash
cat > /tmp/my-preferences.md << 'EOF'
# My preferences

- I prefer concise, direct answers. No preamble.
- I work in Python and TypeScript primarily.
- When I ask about errors, always suggest checking logs first.
- I find it annoying when agents repeat what I just said back to me.
EOF
```

Ingest it:

```bash
node dist/index.js ingest /tmp/my-preferences.md
```

Verify retrieval:

```bash
node dist/index.js search "preferences communication style"
```

You should see your preference chunk appear in the results. If it doesn't show within a second — nox-mem ingests synchronously by default, so something else is wrong (check `dist/` exists; run `npm run build` if not).

**What just happened under the hood:**

1. The markdown file was split into semantic chunks (roughly paragraph-sized)
2. Each chunk was indexed in FTS5 (full-text search, BM25 scoring)
3. A 3072-dimension embedding was generated via Gemini and stored in `vec_chunks` (sqlite-vec)
4. On search, BM25 + semantic scores are fused via RRF (Reciprocal Rank Fusion, k=60)

Both paths are live from the first ingest. There's no separate "vectorize later" step unless you're ingesting in batch offline mode.

---

## §5 Step 3: Build the search function

Create `my_agent.py` and add the search function:

```python
#!/usr/bin/env python3
"""
my_agent.py — minimal memory-enabled chatbot using nox-mem
"""
import json
import subprocess
import sys
import requests

NOX_API = "http://localhost:18802"


def search_memory(query: str, limit: int = 5) -> list[dict]:
    """
    Retrieve the top-k relevant chunks from nox-mem.
    Returns a list of {score, snippet, source_file} dicts.
    Falls back to empty list on any error (agent still works, just blind).
    """
    try:
        resp = requests.get(
            f"{NOX_API}/api/search",
            params={"q": query, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        print(f"[memory] search failed: {e}", file=sys.stderr)
        return []
```

Test it from a Python REPL to verify it works before continuing:

```bash
python3 -c "
import my_agent
results = my_agent.search_memory('preferences communication style')
for r in results:
    print(r.get('score'), r.get('snippet', '')[:80])
"
```

You should see the chunk you ingested in Step 2 appear with a non-zero score.

---

## §6 Step 4: Build the ingest function

Add the ingest function to `my_agent.py`:

```python
def remember(text: str, pain: float = 0.2, importance: float = 0.5) -> bool:
    """
    Store a text chunk in nox-mem via the HTTP ingest API.

    pain: 0.1 (trivial) → 1.0 (production outage, highest urgency)
    importance: 0.1 (ephemeral) → 1.0 (permanent reference)

    Returns True on success.
    """
    try:
        resp = requests.post(
            f"{NOX_API}/api/ingest",
            json={
                "text": text,
                "source_file": "agent/conversation.md",
                "type": "conversation",
                "pain": pain,
                "importance": importance,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[memory] ingest failed: {e}", file=sys.stderr)
        return False
```

**When should you set `pain` higher?**

`pain` models the emotional weight of a memory — how much it hurt or mattered in the moment. Higher pain = higher retrieval priority in future sessions (nox-mem's salience formula is `recency × pain × importance`).

| Situation | Suggested `pain` |
|---|---|
| Normal conversation turn | `0.2` (default) |
| User mentioned frustration or a bug | `0.5` |
| Production error, user upset | `0.7` |
| Critical incident, major failure | `0.9` |

**When should you set `importance` higher?**

`importance` models how long this memory should stay relevant. A user preference (`"I hate bullet lists"`) is highly important and should be retrieved forever. A routine chitchat turn is low importance and can fade.

| Situation | Suggested `importance` |
|---|---|
| Chitchat, routine turn | `0.3` |
| Factual exchange, context | `0.5` (default) |
| User preference or standing instruction | `0.8` |
| Architecture decision, key constraint | `0.9` |

---

## §7 Step 5: Compose the prompt

Add the prompt builder:

```python
SYSTEM_PROMPT = """You are a helpful assistant with access to the user's past conversations.
Use the provided memory snippets to personalize your response.
Be concise. Never repeat the user's question back to them.
If memories are irrelevant to the current question, ignore them."""


def build_prompt(user_input: str, memories: list[dict]) -> str:
    """
    Build a prompt that leads with system instructions,
    surfaces retrieved memories in the middle,
    and ends with the current user input.

    This order matters: LLMs exhibit primacy bias — instructions placed
    first are followed more reliably. Memories in the middle provide
    context without overpowering the current query. The user's actual
    question at the end is what the model is "completing".
    """
    parts = [SYSTEM_PROMPT, ""]

    if memories:
        parts.append("## Relevant memories from past conversations\n")
        for i, mem in enumerate(memories, 1):
            snippet = mem.get("snippet", "").strip()
            source = mem.get("source_file", "unknown")
            score = mem.get("score", 0)
            if snippet:
                parts.append(f"{i}. [{source} | score={score:.3f}]\n{snippet}\n")
        parts.append("")

    parts.append(f"## User message\n{user_input}")
    return "\n".join(parts)
```

The three-zone layout (system → memories → input) is a deliberate choice:

- **System prompt first:** LLMs follow instructions more reliably when they appear before content
- **Memories mid-section:** retrieved context frames the reply without competing with the live query
- **User input last:** the model is "completing" the conversation, so the last thing in context is what it's responding to

---

## §8 Step 6: Call your LLM

Add a pluggable LLM function. The default is an echo stub — fully functional for testing without any API key:

```python
def call_llm(prompt: str) -> str:
    """
    Call your LLM of choice. Swap the implementation below.

    Default: echo stub (no API key required, useful for testing memory flow).
    Uncomment one of the plug-in sections to use a real model.
    """
    # ── ECHO STUB (default) ──────────────────────────────────────────────────
    # Useful for testing that memory retrieval + storage works before wiring LLM.
    lines = [l for l in prompt.split("\n") if l.startswith("## User message")]
    user_msg = prompt.split("## User message\n")[-1].strip() if lines else prompt
    return f"[echo] You said: {user_msg}"

    # ── GEMINI (uncomment to enable) ─────────────────────────────────────────
    # import os, google.generativeai as genai
    # genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    # model = genai.GenerativeModel("gemini-2.5-flash-lite")
    # response = model.generate_content(prompt)
    # return response.text

    # ── OPENAI (uncomment to enable) ─────────────────────────────────────────
    # import os
    # from openai import OpenAI
    # client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    # resp = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # return resp.choices[0].message.content

    # ── ANTHROPIC (uncomment to enable) ──────────────────────────────────────
    # import os, anthropic
    # client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # msg = client.messages.create(
    #     model="claude-haiku-4-5",
    #     max_tokens=1024,
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # return msg.content[0].text
```

The echo stub is intentionally first so the file runs without modification. Once you're happy that memory retrieval is working, delete the stub and uncomment whichever LLM you prefer. For Gemini: `pip install google-generativeai`. For OpenAI: `pip install openai`. For Anthropic: `pip install anthropic`.

**Cost note:** `gemini-2.5-flash-lite` is recommended for the LLM call in development — it's cheap and fast. Don't use the same key for both embeddings (which nox-mem handles) and your agent LLM call if you're near free-tier quota limits.

---

## §9 Step 7: Tie it together

Add the main loop:

```python
def main():
    print("Memory-enabled agent ready. Type /quit to exit, /! to flag frustration.")
    print("─" * 60)

    last_memory_text = None  # used by pain-feedback in Step 8

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input == "/quit":
            print("Bye.")
            break

        # Retrieve relevant past memories
        memories = search_memory(user_input)
        if memories:
            print(f"[memory] retrieved {len(memories)} chunk(s)")

        # Build prompt and call LLM
        prompt = build_prompt(user_input, memories)
        response = call_llm(prompt)
        print(f"\n{response}")

        # Store this turn (moderate defaults)
        turn_text = f"User: {user_input}\nAgent: {response}"
        remember(turn_text, pain=0.2, importance=0.4)
        last_memory_text = turn_text


if __name__ == "__main__":
    main()
```

Run it:

```bash
python3 my_agent.py
```

Talk to it:

```
> What are my preferences?
[memory] retrieved 3 chunk(s)

[echo] You said: What are my preferences?
```

With the echo stub the LLM response is boring, but notice: **memory retrieval already works**. Switch to a real LLM and the agent will pull `my-preferences.md` from Step 2 into its context automatically. Try asking again after a few turns — your conversation history will surface as additional context.

Restart the script. Ask the same question. The memories from the previous session are **still there**, retrieved from disk. This is the core value proposition: persistence without a database service, without a vector cloud, without vendor lock-in.

---

## §10 Step 8: Add pain-weighted feedback

Replace the `main()` loop section that handles `/!` with this extended version:

```python
def update_chunk_pain(chunk_id: int, pain: float) -> bool:
    """
    Update the pain score of an existing chunk via HTTP PATCH.
    Higher pain = higher salience score on future retrieval.
    """
    try:
        resp = requests.patch(
            f"{NOX_API}/api/chunks/{chunk_id}",
            json={"pain": pain},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[memory] pain update failed: {e}", file=sys.stderr)
        return False
```

And update the main loop to handle `/!`:

```python
        # Pain-weighted feedback: user signals frustration
        if user_input.startswith("/!"):
            actual_input = user_input[2:].strip()
            if not actual_input:
                print("[memory] usage: /! <your frustrated message here>")
                continue

            memories = search_memory(actual_input)
            prompt = build_prompt(actual_input, memories)
            response = call_llm(prompt)
            print(f"\n{response}")

            # Store with elevated pain — this turn hurt
            turn_text = f"User: {actual_input}\nAgent: {response}"
            remember(turn_text, pain=0.7, importance=0.6)
            print("[memory] stored with pain=0.7 (frustration flagged)")
            last_memory_text = turn_text
            continue
```

Try it:

```
> /! This keeps breaking and I don't understand why
[memory] retrieved 2 chunk(s)
[echo] You said: This keeps breaking and I don't understand why
[memory] stored with pain=0.7 (frustration flagged)
```

**Why this matters.** nox-mem's salience formula is `recency × pain × importance`. A chunk ingested with `pain=0.7` will consistently outrank lower-pain chunks at similar recency. The next time the user asks something related to "breaking" or "why", that frustrated turn will surface near the top of context — giving your agent advance warning that this topic is sensitive.

This is the mechanism behind proactive agents: instead of treating all memories equally, high-pain moments carry forward naturally. No manual tagging, no separate alert system.

---

## §11 Step 9: Try USE-CASES patterns

You now have a working foundation. The skeleton you just built maps directly to patterns in [USE-CASES.md](USE-CASES.md):

| Pattern | How to extend `my_agent.py` |
|---|---|
| **Pattern 1 — Conversational agent** | Already done. Add `source_prefix` filter by user ID to isolate per-user memory |
| **Pattern 2 — Second brain / PKM** | Change `remember()` to ingest markdown files from your notes folder |
| **Pattern 3 — Code-aware agent** | Pass source files through `ingest` before asking code questions |
| **Pattern 4 — Multi-agent shared memory** | Multiple agents write to the same nox-mem API; search is already shared |
| **Pattern 5 — Decision audit trail** | Set `type=decision` and `importance=0.9` when storing decisions |
| **Pattern 9 — Personal CRM** | Use entity files (`memory/entities/person/<slug>.md`) for contacts |

Each pattern in USE-CASES.md shows the exact CLI/curl calls. Translating them to Python just means replacing the `curl` call with the `requests` equivalents you already built here.

---

## §12 Step 10: Going to production

Before deploying your agent anywhere beyond localhost:

**1. Salience mode: shadow first**

nox-mem's salience scoring defaults to `NOX_SALIENCE_MODE=shadow`. In shadow mode the scores are computed and exposed via `/api/health.salience` but don't affect ranking yet. Run in shadow for at least 7 days to build a baseline before switching to `active`. Jumping straight to `active` on a small corpus gives noisy results.

```bash
# Check current mode
curl http://localhost:18802/api/health | jq .salience
```

**2. VPS sizing**

For a single-user agent, nox-mem fits on the smallest VPS (1 vCPU, 1 GB RAM). At 70k+ chunks the DB is ~150 MB. See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed sizing tables.

**3. Backup discipline**

Never run destructive operations (`reindex`, `consolidate`, `crystallize`) without either `--dry-run` or the pre-op snapshot. The `withOpAudit()` wrapper creates an atomic snapshot automatically when called from code. From the CLI, pass `--dry-run` first:

```bash
node dist/index.js reindex --dry-run
```

**4. Monitoring**

The F10 production health dashboard (if installed) shows chunk growth, vector coverage, salience distribution, and query latency at `/api/health`. Set a cron that pings `/api/health` every 15 minutes and alerts if `vectorCoverage.pct` drops below 99%.

**5. Embedding costs**

Gemini `gemini-embedding-001` (3072d, the model nox-mem uses) costs approximately **$0.0001 per query** on the paid tier. At 1000 queries/day that's $3/month. The free tier handles ~1500 requests/day — plenty for personal use. Monitor at [aistudio.google.com](https://aistudio.google.com).

---

## §13 Troubleshooting

**"Search returns nothing / empty results"**

```bash
curl http://localhost:18802/api/health | jq .vectorCoverage
```

If `embedded < total`, run `node dist/index.js vectorize`. This happens when ingest completes but embeddings were queued (offline mode or quota hit).

**"Slow responses (>3s per search)"**

Gemini embedding calls dominate latency. p50 is ~940ms, p95 ~2.3s — this is expected when the embedding model is cold. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full latency table and advice on warm-up. If you're consistently seeing >5s, check network latency to the Gemini API endpoint.

**"Memory doesn't seem to be improving"**

Two common causes:

1. Pain scores all at default `0.2` — nothing is being weighted higher. Use `/!` deliberately for a few turns and check if those surface first.
2. The corpus is very small (< 50 chunks). With few chunks, RRF scores compress — everything looks equally relevant. Ingest more context (past notes, conversation logs) to give retrieval something to differentiate.

**"Out of memory / DB growing fast"**

At 100k+ chunks, consider running `node dist/index.js consolidate` (deduplicate near-identical chunks) and `node dist/index.js crystallize` (merge high-salience related chunks). Both support `--dry-run`. See scale advice in [USE-CASES.md — §Limitations](USE-CASES.md).

**For general questions** → [FAQ.md](FAQ.md)

---

## §14 What's next

**Ideas for your next agent:**

- **Meeting notes agent** — ingest every meeting transcript, ask "what did we decide about X?" before the next sync
- **Code review companion** — ingest PR descriptions + review comments, let the agent learn your team's review patterns
- **Research assistant** — feed it papers and notes, query it like a second brain that actually reads

**Go deeper:**

- [USE-CASES.md](USE-CASES.md) — 10 concrete patterns, ready to adapt
- [ARCHITECTURE.md](ARCHITECTURE.md) — how hybrid search + RRF + salience actually works under the hood
- [paper/paper-tecnico-nox-mem.md](../paper/paper-tecnico-nox-mem.md) — full technical treatment with benchmarks
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute improvements back
- [GitHub Discussions](https://github.com/totobusnello/memoria-nox/discussions) — share what you built

---

## §15 Complete code: `my_agent.py`

Copy this entire file to get started without assembling the pieces above:

```python
#!/usr/bin/env python3
"""
my_agent.py — minimal memory-enabled chatbot using nox-mem

Prerequisites:
  pip install requests
  # optional, uncomment your LLM in call_llm():
  # pip install google-generativeai   # Gemini
  # pip install openai                # OpenAI
  # pip install anthropic             # Anthropic

Usage:
  python3 my_agent.py

Commands during chat:
  /quit          exit
  /! <message>   flag frustration (stores with pain=0.7)
"""
import sys
import requests

NOX_API = "http://localhost:18802"

SYSTEM_PROMPT = """You are a helpful assistant with access to the user's past conversations.
Use the provided memory snippets to personalize your response.
Be concise. Never repeat the user's question back to them.
If memories are irrelevant to the current question, ignore them."""


# ── Memory: search ────────────────────────────────────────────────────────────

def search_memory(query: str, limit: int = 5) -> list[dict]:
    """Retrieve top-k relevant chunks from nox-mem hybrid search."""
    try:
        resp = requests.get(
            f"{NOX_API}/api/search",
            params={"q": query, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"[memory] search failed: {e}", file=sys.stderr)
        return []


# ── Memory: ingest ────────────────────────────────────────────────────────────

def remember(text: str, pain: float = 0.2, importance: float = 0.5) -> bool:
    """Store a text chunk in nox-mem.

    pain: 0.1 trivial → 1.0 production outage
    importance: 0.1 ephemeral → 1.0 permanent reference
    """
    try:
        resp = requests.post(
            f"{NOX_API}/api/ingest",
            json={
                "text": text,
                "source_file": "agent/conversation.md",
                "type": "conversation",
                "pain": pain,
                "importance": importance,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[memory] ingest failed: {e}", file=sys.stderr)
        return False


def update_chunk_pain(chunk_id: int, pain: float) -> bool:
    """Elevate the pain score of an existing chunk."""
    try:
        resp = requests.patch(
            f"{NOX_API}/api/chunks/{chunk_id}",
            json={"pain": pain},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[memory] pain update failed: {e}", file=sys.stderr)
        return False


# ── Prompt composition ────────────────────────────────────────────────────────

def build_prompt(user_input: str, memories: list[dict]) -> str:
    """Three-zone prompt: system → memories → user input.

    Order matters: instructions first (primacy), memories mid (context),
    user input last (what the model is completing).
    """
    parts = [SYSTEM_PROMPT, ""]

    if memories:
        parts.append("## Relevant memories from past conversations\n")
        for i, mem in enumerate(memories, 1):
            snippet = mem.get("snippet", "").strip()
            source = mem.get("source_file", "unknown")
            score = mem.get("score", 0)
            if snippet:
                parts.append(f"{i}. [{source} | score={score:.3f}]\n{snippet}\n")
        parts.append("")

    parts.append(f"## User message\n{user_input}")
    return "\n".join(parts)


# ── LLM call ─────────────────────────────────────────────────────────────────

def call_llm(prompt: str) -> str:
    """Call your LLM. Default: echo stub (no API key needed).
    Uncomment a section below to switch to a real model.
    """
    # ── ECHO STUB (default — delete this block when using a real LLM) ────────
    user_msg = prompt.split("## User message\n")[-1].strip()
    return f"[echo] You said: {user_msg}"

    # ── GEMINI ────────────────────────────────────────────────────────────────
    # import os, google.generativeai as genai
    # genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    # model = genai.GenerativeModel("gemini-2.5-flash-lite")
    # return model.generate_content(prompt).text

    # ── OPENAI ────────────────────────────────────────────────────────────────
    # import os
    # from openai import OpenAI
    # client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    # resp = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # return resp.choices[0].message.content

    # ── ANTHROPIC ─────────────────────────────────────────────────────────────
    # import os, anthropic
    # client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # msg = client.messages.create(
    #     model="claude-haiku-4-5",
    #     max_tokens=1024,
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # return msg.content[0].text


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print("Memory-enabled agent ready.")
    print("Commands: /quit to exit, /! <message> to flag frustration.")
    print("─" * 60)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("Bye.")
            break

        # Frustration feedback path
        if user_input.startswith("/!"):
            actual_input = user_input[2:].strip()
            if not actual_input:
                print("[memory] usage: /! <your frustrated message here>")
                continue
            memories = search_memory(actual_input)
            if memories:
                print(f"[memory] retrieved {len(memories)} chunk(s)")
            prompt = build_prompt(actual_input, memories)
            response = call_llm(prompt)
            print(f"\n{response}")
            turn_text = f"User: {actual_input}\nAgent: {response}"
            remember(turn_text, pain=0.7, importance=0.6)
            print("[memory] stored with pain=0.7 (frustration flagged)")
            continue

        # Normal path
        memories = search_memory(user_input)
        if memories:
            print(f"[memory] retrieved {len(memories)} chunk(s)")
        prompt = build_prompt(user_input, memories)
        response = call_llm(prompt)
        print(f"\n{response}")
        turn_text = f"User: {user_input}\nAgent: {response}"
        remember(turn_text, pain=0.2, importance=0.4)


if __name__ == "__main__":
    main()
```

Run it:

```bash
python3 my_agent.py
```

---

*Next: [USE-CASES.md](USE-CASES.md) — ten concrete patterns to build on top of this skeleton.*
