#!/usr/bin/env python3
"""Nova VERSÃO (v1.0.3) do registro do nox-mem no Zenodo, a partir da v1.0.2 publicada.
Cria o rascunho da versão, reserva o DOI, sobe o PDF e confere por readback.
NUNCA publica: o botão "Publish" é do Toto.

Lições aplicadas (feedback_rdm_put_silently_drops_legacy_shaped_metadata):
- base de escrita = a versão PUBLICADA lida em RDM e normalizada para o shape de escrita;
- PUT só com {access, files, metadata}; readback campo a campo contra a referência;
- DOI reservado explicitamente (o PUBLISHED.md registra o quase-registro sem DOI).
Token: ZENODO_TOKEN no ambiente (nunca impresso). `.draft-id-v103` retoma o mesmo rascunho.
"""
import hashlib, json, os, pathlib, sys, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PDF = REPO / "paper/build/paper-tecnico-nox-mem.pdf"
PREV = "23041503"  # v1.0.2 publicada
API = "https://zenodo.org/api"
TOK = os.environ["ZENODO_TOKEN"]
RDM = "application/vnd.inveniordm.v1+json"
VERSION, DATE = "1.0.3", "2026-10-03"
ORCID = "0009-0007-5911-8141"

V103 = """<h3>What changed in v1.0.3 (2026-10-03; review and audit passes 2026-10-04)</h3>
<ul>
  <li><strong>(A) Form and framing.</strong> A disclosure of generative AI use is added after
      the Conclusion, in line with arXiv's guidance: engineering and writing assistance, and
      read-only review by LLM-based reviewers from other model families. Product and roadmap
      framing is removed (go-to-market language, internal decision codes, "Autonomy pillar"
      labels); the pre-specified success criterion is kept and named as such. The duplicated,
      empty 6.8 heading is gone.</li>
  <li><strong>(B) Corrections after review</strong>, each checked against the run artifacts
      and the EverMemBench paper: Zep ranks third (behind EverOS and nox-mem), not fourth;
      EverMemBench Table 4 has a Gemini-3-Flash column, so the 63.28% Overall is compared with
      MemOS on the same backbone (59.27%, +4.01 pp) and the GPT-4.1-mini comparison is
      labelled cross-backbone; combinations of retrieval-stage knobs are sub-additive, and the
      "retrieval ceiling" claims are withdrawn; the embedding-matched comparison no longer
      attributes the reversal to the embedder or to the architecture.</li>
  <li><strong>(C) Metric and aggregation.</strong> F_MH is described as LLM-judged accuracy (it
      was called "strict EM"). nox-mem is also reported in Table 4's own aggregation (63.77%,
      +4.50 pp on the same backbone); in that aggregation the Gemini-2.5-flash cross-backbone
      margin is &minus;0.06 pp. MemOS's F_MH is 18.88%, a GPT-4.1-mini figure.</li>
  <li><strong>(D) Intervals and attributions.</strong> The IterB interval is IterB's own (95% CI
      [6.27, 9.79]; paired per-batch difference [0.25, 3.76]); the Wave C interval is recomputed
      with the t distribution; task setup is the leading, not established, account of the F_MH
      gap; HyperMem's 92.73% is a LoCoMo figure.</li>
  <li><strong>(E) Audit pass</strong>, every statement re-checked against the code, the run
      artifacts and the cited papers. Section 3.4 now describes what the code does:
      <code>crystallize</code> stores caller-supplied procedures (no LLM, no promotion between
      chunk types), <em>pain</em> is fixed at ingest by a keyword rule and never raised
      afterwards, <code>reflect</code> answers on request without writing back, and nightly
      consolidation only extracts into topic files. EverMemBench F_MH is compared per backbone
      (6.02% against MemOS's 10.84% on Gemini-3-Flash). The per-category table of the
      embedding-matched comparison (6.4) is recomputed after a permuted LoCoMo category map was
      found; nox-mem still leads all five categories. EverOS outperforming nox-mem is stated in
      the abstract. Mem0's 66.88% on LoCoMo is an LLM-judge score, not F1, and the F1 ranking
      built on it is withdrawn; MuSiQue and HotpotQA reference figures are read from their
      source tables; several "significant" labels are corrected to what paired per-batch
      intervals support; the nox-mem RSS is the 399 MB measurement of 2026-05-29; smoke-run
      figures that no artifact reproduces are replaced by rescored ones.</li>
  <li><strong>(F) Final review</strong>: the LoCoMo per-category retrieval cells match the
      archived run (single-hop 80.36%, temporal 77.96%), and an unsupported +2.8 pp
      date-normalization figure is replaced by the measured session-date injection (temporal
      F1 +15.94 pp); the MuSiQue and HotpotQA runs are described as working over each
      question's own candidate paragraphs, so they measure the reader, not retrieval;
      LightRAG's default stack is in-process storage; a Fisher test that treated paired runs
      as independent is withdrawn; the conclusion no longer reports the pre-specified
      criterion as met.</li>
  <li><strong>(G) Tone and provenance</strong>: the comparison of Section 6 is described as
      pre-specified (execution plan committed to the public repository before the first run;
      not registered with an external registry), and the all-Gemini variant as a planned side
      experiment. The deployability and cost-ratio arguments of 5.7.2, 6.8 and 6.9 are cut;
      competitor RAM and cold-start estimates move to the supplement as the author's
      estimates; the observability and monitoring subsections move to the supplement. Three
      figures from a Mem0 re-execution whose script and per-query output were not retained are
      removed. The boost formula is defined once (score = base &times; (1 + sum of deltas)),
      and the per-category table of 6.4 cites the script that recomputes it. A final
      mechanical check restores two headings that rendered as plain text (5.2 and item F3 of
      7.2), the missing EverMind-AI entry of 6.3.1, and the &delta; symbol of 4.1, which the
      previous PDF build dropped. No measured result changed in this part.</li>
  <li>The headline measurements (63.28% EverMemBench Overall, the nDCG@10 values of 6.3 and
      6.3.2, KG-path 2.5 ms p50, 399 MB) are unchanged. <code>paper/claims_check.py</code>
      passes all 21 guards. The full list, with every changed number, is in
      <code>paper/CHANGELOG.md</code>.</li>
</ul>

"""


def call(method, path, body=None, ctype="application/json", raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("Accept", RDM)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            t = r.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} em {method} {path}: {e.read()[:800]!r}")


def ids(x):
    return {"id": x["id"]} if isinstance(x, dict) and "id" in x else x


# Frases herdadas da v1.0.2 que a v1.0.3 corrige (CHANGELOG, partes C e E). Cada uma tem de
# aparecer exatamente 1x na descrição publicada; se não, o script para em vez de publicar texto velho.
INHERITED = [
    ("in a single-file SQLite store you can host yourself.",
     "in single-file SQLite stores you can host yourself."),
    ("operator-assigned severity in [0.1, 1.0], persisted on every chunk &mdash;",
     "operator-assignable severity in [0.1, 1.0], otherwise fixed at ingest by a keyword rule,\npersisted on every chunk &mdash;"),
    ("The system is a single SQLite file with provider-swappable embeddings,",
     "Each store is a single SQLite file with provider-swappable embeddings,"),
    ("Deployed in production since March 14, 2026,", "Deployed in production since March 2026,"),
    ("with four residual\nconfounds declared. On EverMemBench, nox-mem\nreaches 63.28% Overall with Gemini-3-flash against MemOS numbers obtained on GPT-4.1-mini,\nso the backbones differ and this is not a state-of-the-art claim.</p>",
     "with four residual\nconfounds declared. EverOS, measured later over the same corpus and queries, outperforms\nnox-mem on both datasets (overall nDCG@10 0.646 vs 0.501), with a mandatory cross-encoder\nwhose share of the gap is unmeasured; Zep ranks third, ahead of Mem0. On EverMemBench, nox-mem\nreaches 63.28% Overall with Gemini-3-flash, 4.01 pp above the 59.27% published for MemOS on\nthe same backbone and below that backbone's 72.61% full-context baseline, so this is not a\nstate-of-the-art claim.</p>"),
    ("<li><strong>On the EverMemBench F_MH multi-hop track the system sits at 3&ndash;7%,</strong>\n      against 18.88% strict EM for the best published system on that track (&sect;5.4).</li>",
     "<li><strong>On the EverMemBench F_MH multi-hop track the system sits at 6.02%</strong>\n      with Gemini-3-flash, against 10.84% for MemOS on the same backbone; the best\n      memory-augmented F_MH in the benchmark's Table 4 is 18.88% (MemOS, GPT-4.1-mini); all\n      LLM-judged (&sect;5.4).</li>"),
]

# referência: v1.0.2 publicada, em RDM, normalizada para escrita
ref = call("GET", f"/records/{PREV}")
m0 = ref["metadata"]
desc = m0["description"]
for old, new in INHERITED:
    if desc.count(old) != 1:
        sys.exit(f"esperava 1x a frase herdada {old[:60]!r}, achei {desc.count(old)}")
    desc = desc.replace(old, new)
# Parte G (2026-10-04): "pre-registered" -> "pre-specified" onde a descricao herdada o tiver.
# Contagem livre (0 ou mais) porque a descricao da v1.0.2 nao esta neste repositorio; depois,
# a guarda exige que nenhuma ocorrencia sobreviva, em vez de confiar na troca.
for old, new in (("pre-registered", "pre-specified"), ("pre-register ", "pre-specify "),
                 ("Pre-registered", "Pre-specified"), ("pre-registration", "pre-specification")):
    print(f"troca herdada {old!r}: {desc.count(old)}x")
    desc = desc.replace(old, new)
if "pre-regist" in desc.lower():
    sys.exit("a descricao herdada ainda diz pre-regist*: conferir a mao antes de seguir")
meta = {
    "resource_type": ids(m0["resource_type"]),
    "title": m0["title"],
    "publication_date": DATE,
    "version": VERSION,
    "creators": m0["creators"],
    "rights": [ids(r) for r in m0["rights"]],
    "subjects": m0["subjects"],
    "languages": [ids(l) for l in m0.get("languages", [])],
    "related_identifiers": [
        {**{k: v for k, v in r.items() if k not in ("relation_type", "resource_type")},
         "relation_type": ids(r["relation_type"]),
         **({"resource_type": ids(r["resource_type"])} if "resource_type" in r else {})}
        for r in m0.get("related_identifiers", [])],
    "description": desc.replace("<h3>What changed in v1.0.2", V103 + "<h3>What changed in v1.0.2", 1),
    "publisher": m0.get("publisher", "Zenodo"),
}
if V103 not in meta["description"]:
    sys.exit("âncora 'What changed in v1.0.2' não achada na descrição")
if any(o in meta["description"] or n not in meta["description"] for o, n in INHERITED):
    sys.exit("uma frase herdada da v1.0.2 não foi trocada")
for c in meta["creators"]:
    po = c["person_or_org"]
    if po.get("family_name") == "Busnello" and not po.get("identifiers"):
        po["identifiers"] = [{"scheme": "orcid", "identifier": ORCID}]
    for a in c.get("affiliations", []):
        a.pop("id", None) if not a.get("id") else None

# 1. rascunho da nova versão
idf = HERE / ".draft-id-v103"
if idf.exists():
    rid = idf.read_text().strip()
    print("retomando rascunho", rid)
else:
    rid = call("POST", f"/records/{PREV}/versions")["id"]
    idf.write_text(rid)
    print("rascunho de nova versão criado", rid)
call("PUT", f"/records/{rid}/draft", {"access": ref["access"], "files": {"enabled": True}, "metadata": meta})

# 2. DOI
d = call("GET", f"/records/{rid}/draft")
doi = (d.get("pids") or {}).get("doi", {}).get("identifier")
if not doi:
    doi = call("POST", f"/records/{rid}/draft/pids/doi")["pids"]["doi"]["identifier"]
print("DOI reservado:", doi)

# 3. PDF (só ele; apaga qualquer arquivo herdado)
key = PDF.name
for e in call("GET", f"/records/{rid}/draft/files").get("entries", []):
    call("DELETE", f"/records/{rid}/draft/files/{e['key']}")
call("POST", f"/records/{rid}/draft/files", [{"key": key}])
call("PUT", f"/records/{rid}/draft/files/{key}/content", ctype="application/octet-stream", raw=PDF.read_bytes())
call("POST", f"/records/{rid}/draft/files/{key}/commit")

# 4. readback contra a referência + as mudanças pretendidas
rb = call("GET", f"/records/{rid}/draft")
m = rb["metadata"]
probs = []
for f in ("title", "version", "publication_date", "description", "publisher"):
    if m.get(f) != meta[f]:
        probs.append(f"{f} difere")
if len(m.get("creators", [])) != len(meta["creators"]) or \
   m["creators"][0]["person_or_org"].get("identifiers", [{}])[0].get("identifier") != ORCID:
    probs.append("creators/ORCID difere")
for f in ("rights", "subjects", "languages", "related_identifiers"):
    if len(m.get(f, [])) != len(m0.get(f, [])):
        probs.append(f"{f}: {len(m.get(f, []))} vs {len(m0.get(f, []))} na v1.0.2")
if (m.get("resource_type") or {}).get("id") != m0["resource_type"]["id"]:
    probs.append("resource_type difere")
ents = call("GET", f"/records/{rid}/draft/files").get("entries", [])
md5 = "md5:" + hashlib.md5(PDF.read_bytes()).hexdigest()
if [e["key"] for e in ents] != [key] or ents[0].get("checksum") != md5 or ents[0].get("status") != "completed":
    probs.append(f"arquivos: {[(e['key'], e.get('checksum'), e.get('status')) for e in ents]}")
print("PDF:", key, md5)
print("published:", rb.get("is_published"), "| status:", rb.get("status"))
print("PROBLEMAS:" if probs else "readback OK — nada divergente", *probs, sep="\n  ")
print("rascunho para revisar e publicar: https://zenodo.org/uploads/" + rid)
