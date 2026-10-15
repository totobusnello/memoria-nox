#!/usr/bin/env python3
"""§2.1: build the task catalog (no brief content) and have GPT author 50 underspecified requests.
Writes /root/medicoes/7b/h_requests.jsonl and refuses to overwrite it (frozen once written)."""
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.corpus import build_strata, load_turns  # noqa: E402
from probe.llm import build_catalog_guard, openai_json, preflight  # noqa: E402
from probe.scaffold import agent_root  # noqa: E402

OUT = "/root/medicoes/7b/h_requests.jsonl"
AGENTS = ("main", "nox", "boris", "forge", "cipher", "atlas", "lex")
SEED = 20261014
PROMPT = """You are writing test requests for a team of AI agents. Below is a catalog of the tasks they do
(scheduled prompts, real human messages, and each agent's role). Write exactly 50 requests that a person
on this team would plausibly send to one of these agents. Each request must leave ONE argument implicit,
the way people do when they assume shared context (e.g. "redo the digest like last time but skip the long
threads" leaves implicit which digest and where it goes). Spread requests across agents in proportion to
the catalog. Return a JSON array of 50 objects with keys: request (Portuguese, as the team writes),
owner_agent (one of {agents}), source_task (short label of the catalog entry it derives from),
implicit_argument (what was left unstated).

CATALOG:
{catalog}
"""


def soul_role(agent):
    p = os.path.join(agent_root(agent), "SOUL.md")
    return "\n".join(open(p, encoding="utf-8").read().split("\n")[:60]) if os.path.isfile(p) else ""


def main():
    if os.path.exists(OUT):
        sys.exit(f"{OUT} exists: H requests are frozen")
    turns = load_turns("/root/.claude-nuvini-team/projects", "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z")
    strata = build_strata(turns)
    reps = {}
    for t in strata["C"]:
        reps.setdefault(t["template"], t)
    parts = [f"[scheduled prompt — {t['agent']}]\n{t['text'][:1500]}" for t in reps.values()]
    parts += [f"[human message — {t['agent']}]\n{t['text'][:1500]}" for t in strata["R"]]
    parts += [f"[role — {a}]\n{soul_role(a)}" for a in AGENTS if soul_role(a)]
    catalog = "\n\n---\n\n".join(parts)
    build_catalog_guard(catalog)
    served = preflight()
    reqs = openai_json(PROMPT.format(agents=", ".join(AGENTS), catalog=catalog))
    assert isinstance(reqs, list) and len(reqs) == 50, f"expected 50 requests, got {len(reqs)}"
    assert all(r.get("owner_agent") in AGENTS and r.get("request") for r in reqs)
    ids = list(range(50))
    random.Random(SEED).shuffle(ids)
    pilot = set(ids[:10])
    with open(OUT, "w", encoding="utf-8") as f:
        for i, r in enumerate(reqs):
            f.write(json.dumps({"h_id": f"H{i:02d}", **{k: r[k] for k in
                    ("request", "owner_agent", "source_task", "implicit_argument")},
                    "set": "pilot" if i in pilot else "main"}, ensure_ascii=False) + "\n")
    sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print(json.dumps({"served": served, "n": 50, "sha256": sha, "catalog_sha256": hashlib.sha256(catalog.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
