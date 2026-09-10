"""Mineracao do survey 2602.06052v4 com centralidade lida do proprio bibitem
('Cited by: §x, §y' que o LaTeXML embute) e presenca validada nos dois sentidos."""
import re, json, html, sys, unicodedata, pathlib, collections
h = pathlib.Path("survey.html").read_text(errors="replace")

def norm(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

itens = {}
for m in re.finditer(r'<li id="(bib\.bib\d+)" class="ltx_bibitem[^"]*">(.*?)</li>', h, re.S):
    bid, corpo = m.group(1), m.group(2)
    txt = re.sub(r"\s+"," ", html.unescape(re.sub(r"<[^>]+>"," ",corpo))).strip()
    # 'Cited by: §7.1 , §7.2.1 , ...' -> secoes distintas de PRIMEIRO nivel e completas
    cb = re.search(r"Cited by:(.*)$", txt)
    secs = sorted(set(re.findall(r"§(\d+(?:\.\d+)*)", cb.group(1)))) if cb else []
    corpo_sem_cb = txt[:cb.start()] if cb else txt
    aid = re.search(r"(?:arXiv[:/ ]|abs/)(\d{4}\.\d{4,5})", txt)
    itens[bid] = {"raw": corpo_sem_cb.strip(), "arxiv": aid.group(1) if aid else None,
                  "secoes": secs, "n_sec": len(secs),
                  "n_top": len({s.split(".")[0] for s in secs})}
n_grep = len(re.findall(r"ltx_bibitem", h))
assert len(itens) == n_grep, f"parser {len(itens)} vs marcas {n_grep}"
com_cb = sum(1 for v in itens.values() if v["secoes"])
print(f"{len(itens)} bibitems · {com_cb} com 'Cited by' legivel · "
      f"{len(itens)-com_cb} sem", file=sys.stderr)
assert com_cb > 400, "Cited by nao esta sendo lido"
json.dump(itens, open("survey-bibitems.json","w"), indent=0)
print("distribuicao n_sec:", dict(sorted(collections.Counter(
    v["n_sec"] for v in itens.values()).items())), file=sys.stderr)
