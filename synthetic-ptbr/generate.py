#!/usr/bin/env python3
"""Write the synthetic corpus: free text by Claude around markers; planted sentences by this script.

  python3 -I synthetic-ptbr/generate.py --out <corpus dir> --raw <records dir>
          [--only <path>[,<path>...]] [--budget 5.0] [--workers 6] [--dry-run]

The model never writes a planted sentence. Each file's prompt shows the sentences, each behind a
marker ([[A]], [[B]] ...), and asks for free text with every marker alone on its own line, once.
This script then replaces each marker with its sentence (twice, as two paragraphs, for a
duplicated primary). So a value reaches the corpus only through the planner, and the model's own
text is checked BEFORE assembly: markers exactly once, no digit, no '@' or link, no form of any
planted value, no term of the account the CLI runs under. A failing text is redrawn (3 attempts at
most) and every attempt is recorded.

Isolation (PLANO.md, «Geração isolada»; measured 2026-11-25): `claude -p` runs in an EMPTY
temporary directory with --tools "" --setting-sources "" --strict-mcp-config
--no-session-persistence and a system prompt of its own, so no CLAUDE.md, hook, brief, memory or
MCP reaches it. One thing the CLI always attaches and no flag removes: the account e-mail. That is
why the account's terms are read at run time from ~/.claude.json and refused in the output; they
are never written to disk or printed.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import random
import re
import string
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import s_common as C  # noqa: E402

MODEL = "claude-sonnet-5-5"
FLAGS = ["--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
         "--output-format", "json"]
SYSTEM = ("Você escreve textos fictícios em português do Brasil para um conjunto de dados público "
          "sobre a memória de trabalho de uma equipe de agentes de uma pequena editora fictícia. "
          "Use apenas as informações fictícias que receber. Nunca escreva dígitos, números, datas, "
          "valores, códigos, horários, e-mails, links, nem nomes de pessoas, empresas ou lugares "
          "reais. Responda só com o texto pedido, sem comentários.")
ATTEMPTS = 3
MIN_WORDS, MAX_WORDS = 90, 420
EDITORA = "Editora Casa do Tinteiro"
TIMELINE_SPLIT = "=== LINHA DO TEMPO ==="
KIND_LABEL = {"daily": "nota diária", "decision": "registro de decisão", "lesson": "registro de lição",
              "entity": "ficha de entidade"}


def account_terms():
    """Terms of the account the CLI runs under. Never printed, never written."""
    try:
        acc = json.loads((pathlib.Path.home() / ".claude.json").read_text())["oauthAccount"]
    except Exception:
        return []
    terms = []
    email = (acc.get("emailAddress") or "").lower()
    if "@" in email:
        local, domain = email.split("@", 1)
        terms += [local, domain.split(".")[0]]
    terms += [w.lower() for w in (acc.get("displayName") or "").split() if len(w) > 2]
    return sorted({t for t in terms if len(t) > 2})


def markers_for(items):
    return {it["id"]: f"[[{string.ascii_uppercase[i]}]]" for i, it in enumerate(items)}


def prompt_for(f, plan):
    items = f["items"]
    mk = markers_for(items)
    ents = sorted({x["entity"] for x in plan["facts"]
                   if x["id"] in {it["value"].split("-")[0] for it in items}})
    if f["kind"] == "entity":
        ents = [f["entity"]]
    lines = [f"Escreva uma {KIND_LABEL[f['kind']]} da {EDITORA}, escrita pelo agente {f['author_agent']}."]
    if f["kind"] == "entity":
        lines.append(f"A ficha é sobre «{f['entity']}». Escreva primeiro um resumo do estado atual "
                     f"(um ou dois parágrafos curtos), depois uma linha só com «{TIMELINE_SPLIT}», e "
                     "depois de três a cinco eventos curtos, um por linha, cada um começando com «- ».")
    lines.append(f"Assuntos do dia: {f['topics'][0]} e {f['topics'][1]}.")
    if ents:
        lines.append("Pode mencionar: " + "; ".join(ents) + ".")
    if items:
        lines.append("O texto deve conter os marcadores abaixo, cada um sozinho numa linha, exatamente "
                     "uma vez, entre parágrafos seus. Cada marcador será trocado depois pela frase "
                     "indicada; escreva o texto em volta de modo que a frase faça sentido ali, mas não "
                     "repita, resuma nem parafraseie a frase, e não cite em nenhum outro lugar os "
                     "números, datas, valores ou códigos dela.")
        for it in items:
            where = " (no resumo, antes da linha do tempo)" if it.get("section") == "compiled" else ""
            lines.append(f"{mk[it['id']]}{where} = «{it['text']}»")
    lines.append(f"Tamanho: entre {MIN_WORDS + 30} e {MAX_WORDS - 120} palavras no total. Sem título. "
                 "Nenhum dígito em lugar nenhum: escreva «na semana seguinte», nunca datas ou números.")
    return "\n".join(lines), mk


def validate(text, f, mk, forbidden_forms, acct):
    """Problems with the model's own text, before any marker is replaced."""
    probs = []
    for iid, m in mk.items():
        n = text.count(m)
        if n != 1:
            probs.append(f"marker {m} found {n}x")
        elif not re.search(r"(^|\n)\s*" + re.escape(m) + r"\s*(\n|$)", text):
            probs.append(f"marker {m} not alone on its line")
    bare = text
    for m in mk.values():
        bare = bare.replace(m, "")
    if re.search(r"\d", bare):
        probs.append("digit in model text")
    if "@" in bare or re.search(r"https?:|www\.", bare, re.I):
        probs.append("e-mail or link in model text")
    low = bare.lower()
    for form in forbidden_forms:
        if C.form_spans(low, form.lower()):
            probs.append("a planted value form in model text")
            break
    if any(re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", low) for t in acct):
        probs.append("an account term in model text")
    if re.search(r"\[\[[A-Z]\]\]", bare):
        probs.append("unknown marker")
    words = len(bare.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        probs.append(f"{words} words")
    if f["kind"] == "entity":
        if bare.count(TIMELINE_SPLIT) != 1:
            probs.append("timeline separator missing")
        else:
            cut = text.index(TIMELINE_SPLIT)
            for it in f["items"]:
                if it.get("section") == "compiled" and text.find(mk[it["id"]]) > cut:
                    probs.append(f"marker {mk[it['id']]} after the timeline")
    return probs


SECTION_HEADINGS = ["Manhã", "Tarde", "Contexto", "Andamento", "Registro", "Observações",
                    "Conversas", "Encaminhamentos"]
SECTION_MIN_WORDS = 35      # a section closes once it holds this many words
DUP_MIN_WORDS = 22          # a duplicated section must survive the chunker's <20-word merge


def sectioned(text, mk, items, rng):
    """Split the model's text into `## ` sections, the unit nox-mem chunks on (chunkMarkdown splits
    on `##`/`###` headings and merges a piece under 20 words into the one before it; measured on
    3.5.2 and 3.11.1, 2026-11-25). Without sections every file was ONE chunk, and an edit anywhere
    in a file would change the planted sentence's chunk.

    Rules: a marker never opens a section (the planted sentence stays with the paragraph that
    introduces it); a duplicated primary's section holds that marker and nothing planted besides,
    and is written twice, identical, so the chunker makes two byte-identical chunks."""
    marker_of = {m: iid for iid, m in mk.items()}
    dup = {m for iid, m in mk.items() if items[iid]["count"] > 1}
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]

    def plain(p):
        return items[marker_of[p]]["text"] if p in marker_of else p

    def words(ps):
        return sum(len(plain(p).split()) for p in ps)

    secs, cur = [], []
    for i, p in enumerate(paras):
        nxt = paras[i + 1] if i + 1 < len(paras) else None
        if cur and p not in marker_of and (nxt in dup or words(cur) >= SECTION_MIN_WORDS):
            secs.append(cur)
            cur = []
        cur.append(p)
        if p in dup:
            secs.append(cur)
            cur = []
    if cur:
        secs.append(cur)
    # a duplicated section too short to survive the merge takes in the plain section before it
    for k in range(len(secs)):
        if secs[k] and secs[k][-1] in dup:
            while words(secs[k]) < DUP_MIN_WORDS and k > 0 and secs[k - 1] and \
                    not any(q in marker_of for q in secs[k - 1]):
                secs[k] = secs[k - 1] + secs[k]
                secs[k - 1] = []
    secs = [x for x in secs if x]
    heads = rng.sample(SECTION_HEADINGS, min(len(SECTION_HEADINGS), len(secs)))
    heads += [SECTION_HEADINGS[i % len(SECTION_HEADINGS)] for i in range(len(secs) - len(heads))]
    first_is_dup = bool(secs) and secs[0][-1] in dup
    out = []
    for k, sec in enumerate(secs):
        body = "\n\n".join(plain(p) for p in sec)
        block = body if (k == 0 and not first_is_dup) else f"## {heads[k]}\n\n{body}"
        out.append(block)
        if sec[-1] in dup:
            out.append(block)
    return "\n\n".join(out)


def assemble(f, text, mk, rng):
    items = {it["id"]: it for it in f["items"]}
    if f["kind"] in ("daily", "decision", "lesson"):
        body = sectioned(text, mk, items, rng)
        if f["kind"] == "daily":
            return f"# {f['date']}\n\n{body}\n"
        title = ("Decisão" if f["kind"] == "decision" else "Lição") + ": " + f["topics"][0]
        return f"# {title}\n\n{body}\n"
    body = text.strip()
    for iid, m in mk.items():
        it = items[iid]
        rep = it["text"] if it["count"] == 1 else "\n\n".join([it["text"]] * it["count"])
        body = re.sub(r"[ \t]*" + re.escape(m) + r"[ \t]*", lambda _m: rep, body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    compiled, timeline = body.split(TIMELINE_SPLIT, 1)
    events = [ln.strip()[2:].strip() for ln in timeline.splitlines() if ln.strip().startswith("- ")]
    days = sorted(rng.sample(range(178), len(events)), reverse=True)
    tl = "\n".join(f"- **{(dt.date(2027, 1, 4) + dt.timedelta(days=d)).isoformat()}** — [nota] {e}"
                   for d, e in zip(days, events))
    fm = (f"---\nname: {f['entity']}\ndescription: Ficha de {f['entity']} na {EDITORA}, editora "
          f"fictícia.\ntype: reference\n---\n\n")
    return f"{fm}{compiled.strip()}\n\n## Timeline\n\n{tl}\n"


def reassemble(plan, raw, out, check=False):
    """Rebuild the corpus from the generation records alone, with no model call. With check=True,
    compare against what is on disk instead of writing; the committed corpus must be exactly this."""
    diff = []
    for f in plan["files"]:
        rec = json.loads((pathlib.Path(raw) / (f["path"] + ".json")).read_text(encoding="utf-8"))
        last = rec["attempts"][-1]
        if last["problems"]:
            diff.append(f"{f['path']}: no accepted attempt")
            continue
        _, mk = prompt_for(f, plan)
        rng = random.Random(f"{plan['seed']}:{f['path']}")
        want = assemble(f, last["text"], mk, rng)
        op = pathlib.Path(out) / f["path"]
        if check:
            if not op.exists() or op.read_text(encoding="utf-8") != want:
                diff.append(f["path"])
        else:
            op.parent.mkdir(parents=True, exist_ok=True)
            op.write_text(want, encoding="utf-8")
    return diff


def call_claude(prompt, workdir, budget_call):
    r = subprocess.run(["claude", "-p", prompt, "--model", MODEL, "--system-prompt", SYSTEM,
                        "--max-budget-usd", str(budget_call)] + FLAGS,
                       cwd=workdir, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=300)
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": f"rc={r.returncode} non-json stdout", "cost": 0.0}
    return {"text": d.get("result") or "", "cost": float(d.get("total_cost_usd") or 0.0),
            "models": sorted((d.get("modelUsage") or {}).keys()), "stop": d.get("stop_reason"),
            "is_error": bool(d.get("is_error")), "error": None if not d.get("is_error") else "is_error"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--budget", type=float, default=5.0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reassemble", action="store_true",
                    help="rebuild --out from the records in --raw, no model call")
    ap.add_argument("--check", action="store_true",
                    help="with --reassemble: exit 1 if --out differs from the rebuild")
    a = ap.parse_args()

    plan = C.load_plan()
    if a.reassemble:
        diff = reassemble(plan, a.raw, a.out, check=a.check)
        for d in diff[:20]:
            print(f"  ! {d}")
        print(f"reassemble{' --check' if a.check else ''}: {'FAIL, ' + str(len(diff)) if diff else 'ok'}")
        return 1 if diff else 0
    files = plan["files"]
    if a.only:
        want = set(a.only.split(","))
        files = [f for f in files if f["path"] in want]
    out, raw = pathlib.Path(a.out), pathlib.Path(a.raw)
    forms = [form for _, form in C.all_value_forms(plan)]
    acct = account_terms()
    print(f"generate: {len(files)} file(s), model {MODEL}, budget US$ {a.budget:.2f}, "
          f"{len(acct)} account term(s) refused")
    if a.dry_run:
        p, _ = prompt_for(files[0], plan)
        print(p)
        return 0

    spent = [0.0]
    lock = threading.Lock()
    stop = threading.Event()

    def one(f):
        if stop.is_set():
            return f["path"], "skipped (budget)"
        prompt, mk = prompt_for(f, plan)
        rng = random.Random(f"{plan['seed']}:{f['path']}")
        attempts = []
        with tempfile.TemporaryDirectory(prefix="gen-") as work:     # empty cwd for every call
            for _ in range(ATTEMPTS):
                with lock:
                    if spent[0] >= a.budget:
                        stop.set()
                        break
                res = call_claude(prompt, work, 0.25)
                with lock:
                    spent[0] += res["cost"]
                probs = [res["error"]] if res.get("error") else validate(res["text"], f, mk, forms, acct)
                rec = {"cost_usd": res["cost"], "models": res.get("models"), "stop": res.get("stop"),
                       "problems": probs}
                # an attempt that tripped the account check is recorded without its text
                rec["text"] = None if "an account term in model text" in probs else res.get("text")
                attempts.append(rec)
                if not probs:
                    break
        record = {"path": f["path"], "model_requested": MODEL, "flags": FLAGS, "system": SYSTEM,
                  "prompt": prompt, "attempts": attempts}
        rp = raw / (f["path"] + ".json")
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(C.dump_json(record), encoding="utf-8")
        if attempts and not attempts[-1]["problems"]:
            op = out / f["path"]
            op.parent.mkdir(parents=True, exist_ok=True)
            op.write_text(assemble(f, attempts[-1]["text"], mk, rng), encoding="utf-8")
            return f["path"], f"ok in {len(attempts)}"
        return f["path"], "FAILED: " + "; ".join(attempts[-1]["problems"] if attempts else ["budget"])

    results = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for path, status in ex.map(one, files):
            results.append((path, status))
            print(f"  {status:24s} {path}", flush=True)
    bad = [p for p, s in results if not s.startswith("ok")]
    print(f"generate: {len(results) - len(bad)} ok, {len(bad)} not written, US$ {spent[0]:.4f} reported")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
