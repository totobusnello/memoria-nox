#!/usr/bin/env python3
"""
Helpers for the Paper B census restoration (gates and census). Read-only on every
September artefact; writes only where told.

  cost       <calls.jsonl ...>                      USD from the `usage` blocks the harness logged
  retry-sets --verdicts F... --episodes-dir D --out-dir O
                                                    per panelist, episodes whose row is not `ok`
                                                    (quota/missing): one input file per panelist
  floorless  --verdicts F... --episodes-dir D --out F
                                                    episodes WITHOUT the 3-substantive-verdict
                                                    floor under `pilot_replay.carregar_verdicts`
                                                    (the DeepSeek substitution set, DEVIATIONS §10.31)

Prices are USD per 1M tokens, read on 2026-10-05 from the providers' own pages/API:
  zhipu  glm-5.2         docs.z.ai/guides/overview/pricing           in 1.40  cached 0.26  out 4.40
  xai    grok-4.5        api.x.ai/v1/language-models/grok-4.5        in 2.00  cached 0.30  out 6.00
                         (fields are USD cents per 100M tokens: 20000 / 3000 / 60000)
  google gemini-2.5-pro  ai.google.dev/gemini-api/docs/pricing       in 1.25  out 10.00 (incl. thinking), prompts <= 200k
  deepseek v4-pro        api-docs.deepseek.com/quick_start/pricing   PEAK: miss 1.32  hit 0.044  out 3.96
                         (off-peak is half; PEAK is used as the upper bound)
Anthropic-style `input_tokens` is billed at full price and `cache_read_input_tokens` at the
cached price, which is an upper bound if a provider counts cached tokens inside input_tokens.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import tempfile
from pathlib import Path

P2 = Path(__file__).resolve().parents[2]  # paper2-interventional/, two levels above B-censo/
sys.path.insert(0, str(P2))

PRICE = {  # (input, cached_input, output) USD / 1M tokens
    "zhipu": (1.40, 0.26, 4.40),
    "xai": (2.00, 0.30, 6.00),
    "google": (1.25, 1.25, 10.00),
    "deepseek": (1.32, 0.044, 3.96),
}


def call_cost(row: dict) -> float:
    u = row.get("usage") or {}
    pin, pcache, pout = PRICE[row["panelist"]]
    if "promptTokenCount" in u:  # Gemini
        return (u.get("promptTokenCount", 0) * pin
                + (u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)) * pout) / 1e6
    return (u.get("input_tokens", 0) * pin + u.get("cache_read_input_tokens", 0) * pcache
            + u.get("cache_creation_input_tokens", 0) * pin + u.get("output_tokens", 0) * pout) / 1e6


def cost(paths: list[str]) -> dict:
    agg = collections.defaultdict(lambda: {"calls": 0, "calls_without_usage": 0, "usd": 0.0,
                                           "tokens_in": 0, "tokens_out": 0})
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            a = agg[r["panelist"]]
            a["calls"] += 1
            u = r.get("usage")
            if not u:
                a["calls_without_usage"] += 1
                continue
            a["usd"] += call_cost(r)
            a["tokens_in"] += u.get("promptTokenCount", u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0))
            a["tokens_out"] += (u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
                                if "promptTokenCount" in u else u.get("output_tokens", 0))
    out = {k: {**v, "usd": round(v["usd"], 4)} for k, v in sorted(agg.items())}
    out["TOTAL_usd"] = round(sum(v["usd"] for v in agg.values()), 4)
    return out


def _rows(paths):
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                yield json.loads(line)


def _episodes(d: Path) -> dict[str, str]:
    eps = {}
    for f in sorted(d.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                eps[json.loads(line)["episode_id"]] = line
    return eps


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cost"); c.add_argument("calls", nargs="+")
    r = sub.add_parser("retry-sets")
    r.add_argument("--verdicts", nargs="+", required=True)
    r.add_argument("--episodes-dir", required=True)
    r.add_argument("--out-dir", required=True)
    s = sub.add_parser("secret-scan", help="exit 1 if any episode carries a credential-like string")
    s.add_argument("--episodes-dir", required=True)
    f = sub.add_parser("floorless")
    f.add_argument("--verdicts", nargs="+", required=True)
    f.add_argument("--episodes-dir", required=True)
    f.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.cmd == "cost":
        print(json.dumps(cost(a.calls), indent=2))
        return 0

    eps = _episodes(Path(a.episodes_dir))
    if a.cmd == "secret-scan":
        # Prints episode ids and the 5-char prefix + length of each match, never the value.
        import re
        pat = re.compile(r"(sk-[A-Za-z0-9]{20,}|xox[abpr]-[A-Za-z0-9\-]{10,}|xai-[A-Za-z0-9]{20,}"
                         r"|AIza[0-9A-Za-z_\-]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
                         r"|-----BEGIN [A-Z ]*PRIVATE KEY)")
        hits = 0
        for i, line in eps.items():
            r = json.loads(line)
            ms = pat.findall(r["input_excerpt"] + "\n" + r["result_excerpt"])
            if ms:
                hits += 1
                print(f"{i}\t" + ",".join(f"{m[:5]}…({len(m)})" for m in ms))
        print(f"episodes_with_credential_like_strings\t{hits}\tof\t{len(eps)}")
        return 1 if hits else 0
    if a.cmd == "retry-sets":
        ok, seen = set(), collections.defaultdict(set)
        for row in _rows(a.verdicts):
            seen[row["panelist"]].add(row["episode_id"])
            if row["status"] == "ok":
                ok.add((row["episode_id"], row["panelist"]))
        od = Path(a.out_dir); od.mkdir(parents=True, exist_ok=True)
        for pid, ids in sorted(seen.items()):
            pend = sorted(i for i in ids if (i, pid) not in ok)
            if pend:
                (od / f"retry-{pid}.jsonl").write_text("".join(eps[i] + "\n" for i in pend))
            print(f"{pid}\t{len(pend)}")
        return 0

    # floorless
    from pilot_replay import carregar_verdicts  # unchanged consolidation rule
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as t:
        for row in _rows(a.verdicts):
            t.write(json.dumps(row) + "\n")
    resolved = carregar_verdicts(Path(t.name))
    Path(t.name).unlink()
    pend = [i for i in eps if i not in resolved]
    Path(a.out).write_text("".join(eps[i] + "\n" for i in pend))
    print(f"floorless\t{len(pend)}\tof\t{len(eps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
