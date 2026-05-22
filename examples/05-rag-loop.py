#!/usr/bin/env python3
"""
RAG-style loop using nox-mem as retrieval backend.

Steps:
  1. Search nox-mem for relevant chunks (hybrid: BM25 + semantic)
  2. Build a prompt with retrieved chunks as context
  3. Print the ready-to-send prompt to stdout

The script does NOT call any LLM provider — it shows exactly what you'd
send to OpenAI / Anthropic / Gemini. Plug in your preferred client.

Stdlib only — no pip install required.

Usage:
    ./examples/05-rag-loop.py [question]
    BASE_URL=http://localhost:18802 ./examples/05-rag-loop.py "How does salience work?"
"""

import json
import os
import sys
from urllib.request import urlopen
from urllib.parse import urlencode

BASE_URL = os.environ.get("BASE_URL", "http://187.77.234.79:18802").rstrip("/")

# ── Config ────────────────────────────────────────────────────────────────────
RETRIEVAL_LIMIT = 5        # chunks to retrieve
SNIPPET_MAX_LEN = 400      # chars per chunk in the context block
SYSTEM_PROMPT = (
    "You are a knowledgeable assistant. Answer the user's question using ONLY "
    "the context provided below. If the context does not contain enough "
    "information, say so honestly. Cite chunk sources when relevant."
)


# ── Retrieval ─────────────────────────────────────────────────────────────────

def search(query: str, limit: int = RETRIEVAL_LIMIT) -> list[dict]:
    """GET /api/search — returns ranked chunks."""
    params = urlencode({"q": query, "limit": limit})
    with urlopen(f"{BASE_URL}/api/search?{params}", timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("results", [])


# ── Prompt builder ─────────────────────────────────────────────────────────────

def build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    lines = []
    for i, c in enumerate(chunks, 1):
        source = c.get("source_file") or c.get("source") or "?"
        score = c.get("score")
        score_str = f"{float(score):.3f}" if score is not None else "?"
        snippet = (c.get("snippet") or "").strip()[:SNIPPET_MAX_LEN]
        lines.append(f"[{i}] source={source} score={score_str}")
        lines.append(snippet)
        lines.append("")
    return "\n".join(lines).strip()


def build_prompt(question: str, context: str) -> dict:
    """
    Returns a messages list in OpenAI / Anthropic-compatible format.
    Plug into your preferred client:

        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=prompt["messages"],
        )

        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=prompt["system"],
            messages=prompt["messages"],
        )
    """
    return {
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"<context>\n{context}\n</context>\n\n"
                    f"Question: {question}"
                ),
            }
        ],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "How does salience work?"

    # Step 1: Retrieve
    print(f"[1/3] Searching nox-mem for: {question!r}")
    chunks = search(question)
    if not chunks:
        print("No chunks retrieved — try a different query.")
        sys.exit(1)
    print(f"      Retrieved {len(chunks)} chunk(s)")

    # Step 2: Build context
    print("[2/3] Building context block...")
    context = build_context_block(chunks)

    # Step 3: Assemble prompt
    print("[3/3] Assembling LLM prompt")
    prompt = build_prompt(question, context)

    print()
    print("=" * 70)
    print("READY-TO-SEND PROMPT (copy into your LLM client)")
    print("=" * 70)
    print()
    print(f"SYSTEM:\n{prompt['system']}")
    print()
    print("USER MESSAGE:")
    print(prompt["messages"][0]["content"])
    print()
    print("=" * 70)
    print("To call OpenAI:")
    print("  pip install openai")
    print("  OPENAI_API_KEY=... python3 -c \"")
    print("    import openai, json")
    print("    c = openai.OpenAI()")
    print("    r = c.chat.completions.create(model='gpt-4o', messages=<messages>)")
    print("    print(r.choices[0].message.content)")
    print("  \"")
    print()
    print("To call Anthropic:")
    print("  pip install anthropic")
    print("  ANTHROPIC_API_KEY=... python3 -c \"")
    print("    import anthropic")
    print("    c = anthropic.Anthropic()")
    print("    r = c.messages.create(model='claude-opus-4-5', max_tokens=1024,")
    print("          system=<system>, messages=<messages>)")
    print("    print(r.content[0].text)")
    print("  \"")


if __name__ == "__main__":
    main()
