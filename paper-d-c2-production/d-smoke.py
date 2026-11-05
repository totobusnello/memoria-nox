#!/usr/bin/env python3
"""Paper D smoke: C0 against C2 on a handful of frozen production sessions, to size the sample (D4).

Not a result. It exercises the pipeline the pre-registration will freeze and measures what the
sample size depends on: how many questions survive generation, how often C0 and C2 disagree on the
same question (the discordant pairs a paired test runs on), whether arm A clears the 0.70 ceiling
gate, and the cost per session.

  GEMINI_API_KEY=... OPENAI_API_KEY=... python3 -I d-smoke.py --dir <private dir> [--cap 1.0]

<private dir> holds select.json and sessions/<uuid>.jsonl (copied by d-select.py, sha256 in
select.json) and receives cache.sqlite and smoke.json. It must be outside the repository.

Pipeline, reusing Paper 3's implementation (paper3-construction/lme-run.py) for every model call
that Paper 3 also made:
  prose      envelope cuts of audits/2026-10-26-replay-build.py (via d-select.py)
  windows    20,000 chars from the start and from the middle (replay-build rule)
  questions  writer glm-5.3 (a third family), C0's declared categories (primary, D1) and C2's two
             extra classes (secondary, never pooled); every citation must be a byte-exact substring
             of its window, or the fact is dropped
  distill    lme-run.distill under C0 and C2 over the whole session's blocks (full window)
  arms       A: the evidence region of the window (citations +/- 1,500 chars, replay rule);
             C0, C2: all units of the session, "[date] [category] text", no retrieval
  reader     lme-run.answer, reader R0 = production ANSWER_SYSTEM, gemini-2.5-flash-lite (D6)
  judges     lme-run.judge (gpt-6-luna, P(contem) > 0.5) and lme-run.judge2 (family 2)

Prints counts only. Questions, answers and units stay in <private dir>/smoke.json.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


L = load("lme", ROOT / "paper3-construction/lme-run.py")
G = load("gen", ROOT / "paper-a-eval-ptbr/holdout-generate.py")
S = load("sel", HERE / "d-select.py")

WINDOW, PAD = 20_000, 1_500
CATS = """- decision: decisões tomadas pelo usuário ou pelo agente
- preference: preferências do usuário (como ele quer as coisas feitas)
- lesson: lições aprendidas (erros, fixes, insights técnicos)
- context: contexto de projeto relevante (nomes, status, detalhes)"""
COMMON = """Para cada fato devolva:
- "pergunta": pergunta AUTOCONTIDA. Precisa nomear explicitamente as entidades (arquivo, cron,
  número, pessoa, projeto, comando) para que alguém SEM acesso a este trecho entenda o que se
  pergunta. NUNCA use "isso", "esse arquivo", "o horário escolhido", "a decisão acima".
- "resposta": a resposta curta e factual, no máximo 25 palavras.
- "citacoes": trechos VERBATIM deste texto, copiados caractere por caractere exatamente como
  aparecem, que juntos sustentam a resposta. Cada trecho entre 20 e 300 caracteres.
- "categoria": %s.
Responda SÓ com JSON: {"fatos":[{"pergunta":"...","resposta":"...","citacoes":["..."],"categoria":"..."}]}"""
# primary (D1): C0's declared categories, as in audits/2026-10-26-replay-generate.py
PRIMARY = ("Você recebe um trecho de uma conversa real entre um usuário e agentes de IA.\n\n"
           "Extraia até 4 fatos que mereçam ser lembrados a longo prazo, EXATAMENTE nestas "
           "categorias (são as que o sistema de memória declara guardar):\n" + CATS + "\n\n"
           "Ignore cumprimentos, confirmações e conteúdo repetido. Prefira decision e lesson.\n\n"
           + COMMON % "uma das quatro acima")
# secondary (D1): the two classes C2 adds (IDENT_PARAGRAPH, EVENT_PARAGRAPH of lme-run.py)
SECONDARY = ("Você recebe um trecho de uma conversa real entre um usuário e agentes de IA.\n\n"
             "Extraia até 3 fatos de UMA destas duas classes, e só delas:\n"
             "- identificador: um identificador exato citado na conversa (nome de arquivo, caminho, "
             "comando, tabela, coluna, chave de configuração, porta, URL, versão, valor numérico), "
             "perguntado de modo que a resposta seja o identificador LETRA POR LETRA;\n"
             "- passagem: um fato concreto dito de passagem, no meio de outro assunto (quantidade, "
             "valor, duração, data, lugar, pessoa).\n"
             "Se o trecho não tiver fato assim, devolva lista vazia; NÃO invente.\n\n"
             + COMMON % "\"identificador\" ou \"passagem\"")


def parse(txt):
    txt = (txt or "").strip()
    txt = re.sub(r"^```(?:json)?|```$", "", txt).strip()
    try:
        d = json.loads(txt)
        return d.get("fatos", d) if isinstance(d, dict) else d
    except Exception:
        out = []
        for m in re.finditer(r"\{[^{}]*\"pergunta\"[^{}]*\}", txt):
            try:
                out.append(json.loads(m.group(0)))
            except Exception:
                pass
        return out


def turns(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            s = S.turn_text(o)
            if s:
                role, _, content = s.partition(": ")
                out.append({"role": role, "content": content})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--cap", type=float, default=1.0)
    a = ap.parse_args()
    D = pathlib.Path(a.dir)
    if subprocess.run(["git", "-C", str(D), "rev-parse"], capture_output=True).returncode == 0:
        sys.exit("refusing: --dir is inside a git repository")
    sel = json.load(open(D / "select.json"))
    cache, led = L.Cache(str(D / "cache.sqlite")), L.Ledger(a.cap)
    rows, gen = [], collections.Counter()
    for c in sel["chosen"]:
        u = c["uuid"]
        ts = turns(D / "sessions" / f"{u}.jsonl")
        full = "\n\n".join(f"{t['role']}: {t['content']}" for t in ts)
        wins = {0: full[:WINDOW]}
        mid = max(0, len(full) // 2 - WINDOW // 2)
        if mid > 0:
            wins[mid] = full[mid:mid + WINDOW]
        units = {}
        for crit in ("C0", "C2"):
            us = []
            for b in L.session_blocks(ts):
                us += L.distill(cache, led, crit, b)["units"]
            units[crit] = us
        for off, w in wins.items():
            for set_name, prompt in (("primary", PRIMARY), ("secondary", SECONDARY)):
                key = L.h("gen", G.MODEL, prompt, w)
                hit = cache.get(key)
                if hit is None:
                    txt, served = G.ask(prompt + "\n\nTRECHO:\n" + w)
                    hit = {"text": txt, "served": served}
                    cache.put(key, "gen", hit)
                    gen["calls"] += 1
                for f in parse(hit["text"]) or []:
                    if not isinstance(f, dict) or not f.get("pergunta") or not f.get("resposta"):
                        gen["malformed"] += 1
                        continue
                    cits = [x for x in f.get("citacoes") or [] if isinstance(x, str)]
                    locs = [(w.find(x), w.find(x) + len(x)) for x in cits]
                    if not cits or any(b < 0 for b, _ in locs):
                        gen[f"{set_name}_citation_not_verbatim"] += 1
                        continue
                    lo, hi = min(b for b, _ in locs), max(e for _, e in locs)
                    gen[f"{set_name}_kept"] += 1
                    rows.append({"uuid": u, "set": set_name, "window": off,
                                 "category": f.get("categoria"), "question": f["pergunta"],
                                 "ref": f["resposta"], "span": hi - lo,
                                 "evidence": w[max(0, lo - PAD):hi + PAD],
                                 "date": c["last_event"]})
        for r in rows:
            if r["uuid"] == u:
                r["units"] = {k: len(v) for k, v in units.items()}
                r["material"] = {k: "\n".join(f"[{c['last_event']}] [{x.get('category')}] {x.get('text')}"
                                              for x in v) or "(vazio)" for k, v in units.items()}
    for r in rows:
        r["arms"] = {}
        for arm in ("A", "C0", "C2"):
            mat = r["evidence"] if arm == "A" else r["material"][arm]
            ans = L.answer(cache, led, mat, "PERGUNTA: " + r["question"], reader="R0")["text"]
            j1 = L.judge(cache, led, r["ref"], ans, r["question"])
            j2 = L.judge2(cache, led, r["ref"], ans, r["question"])
            r["arms"][arm] = {"answer": ans, "j1": (j1["contem"] or 0) > L.THR,
                              "j1_contradiz": (j1["contradiz"] or 0) > L.THR, "j2": bool(j2["correta"])}
    json.dump({"select": sel, "generation": gen, "rows": rows, "usd": led.usd, "calls": led.n},
              open(D / "smoke.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"sessions {len(sel['chosen'])} · writer calls {gen['calls']} · generation {dict(gen)}")
    for s in ("primary", "secondary"):
        rs = [r for r in rows if r["set"] == s]
        if not rs:
            print(f"{s}: no questions")
            continue
        print(f"{s}: {len(rs)} questions")
        for j in ("j1", "j2"):
            acc = {arm: sum(r["arms"][arm][j] for r in rs) / len(rs) for arm in ("A", "C0", "C2")}
            b = sum(r["arms"]["C2"][j] and not r["arms"]["C0"][j] for r in rs)
            c_ = sum(r["arms"]["C0"][j] and not r["arms"]["C2"][j] for r in rs)
            print(f"  {j}: A {acc['A']:.3f} · C0 {acc['C0']:.3f} · C2 {acc['C2']:.3f} · "
                  f"discordant C2-only {b}, C0-only {c_} (of {len(rs)})")
    units = {crit: sum(r["units"][crit] for r in {r["uuid"]: r for r in rows}.values()) for crit in ("C0", "C2")}
    print(f"units over the sessions with questions: {units}")
    print(f"ledger US$ {led.usd:.4f} · calls {led.n} (writer glm-5.3 not priced here)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
