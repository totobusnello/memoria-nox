import json, re, sys, unicodedata, pathlib, collections
PAPER = pathlib.Path(sys.argv[1])/"paper"
man = json.loads((PAPER/"authors-manifest.json").read_text())
md  = (PAPER/"paper-tecnico-nox-mem.md").read_text()

def norm(t):
    t = unicodedata.normalize("NFKD",t).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+"," ",t).strip()

NOSSOS_IDS = set(re.findall(r"arXiv:(\d{4}\.\d{4,5})", md))
NOSSOS_TIT = {norm(v["title"]) for v in man.values()}
for c in re.findall(r"^\[\^[A-Za-z0-9_-]+\]:(.*)$", md, re.M):
    for t in re.findall(r"\*([^*]{12,})\*", c): NOSSOS_TIT.add(norm(t))
NOSSOS_TIT = {t for t in NOSSOS_TIT if len(t) > 14}

def ja_citada(v):
    if v["arxiv"] and v["arxiv"] in NOSSOS_IDS: return "id"
    r = norm(v["raw"])
    for t in NOSSOS_TIT:
        if t in r: return "titulo"
        p = " ".join(t.split(" ")[:6])          # prefixo antes do subtitulo
        if len(t.split(" ")) > 6 and p in r: return "prefixo"
    return None

itens = json.load(open("survey-bibitems.json"))
def acha(frag):
    h = [v for v in itens.values() if norm(frag) in norm(v["raw"])]
    return h[0] if len(h) == 1 else (h if h else None)

CTRL = {"interactive simulacra of human behavior": "genagents",
        "benchmarking chat assistants on long-term interactive memory": "longmemeval",
        "neurobiologically inspired long-term memory": "hipporag",
        "building production-ready ai agents": "mem0",
        "temporal knowledge graph architecture for agent memory": "zep"}
erros, ok = [], []
for frag, chave in CTRL.items():
    v = acha(frag)
    if v is None: erros.append(f"  [{chave}] fragmento nao acha bibitem — controle inutil")
    elif isinstance(v, list): erros.append(f"  [{chave}] fragmento ambiguo ({len(v)} bibitems)")
    elif not ja_citada(v): erros.append(f"  [{chave}] NAO reconhecida: {v['raw'][:70]}")
    else: ok.append(f"{chave}={ja_citada(v)}")
if ja_citada({"raw":"Q. Nada, Zzyzx framework for imaginary retrieval. Journal of Nothing 2099.",
              "arxiv":"9999.99999"}):
    erros.append("  controle NEGATIVO falhou: obra inventada dada como citada")
if erros: sys.exit("CONTROLE FALHOU — classificador nao reportavel:\n"+"\n".join(erros))
print("controle (+):", " · ".join(ok))
print("controle (-): obra inventada -> nao citada  ✓\n")

for v in itens.values(): v["ja"] = ja_citada(v)
nao = [v for v in itens.values() if not v["ja"]]
ja  = [v for v in itens.values() if v["ja"]]
print(f"535 bibitems: {len(ja)} ja citadas ({ {k:sum(1 for v in ja if v['ja']==k) for k in ('id','titulo','prefixo')} }) · {len(nao)} ausentes")
print("\nausentes por centralidade (n de secoes do survey que a citam):")
print("  ", dict(sorted(collections.Counter(v["n_sec"] for v in nao).items())))
alvo = sorted([v for v in nao if v["n_sec"] >= 4], key=lambda v: -v["n_sec"])
print(f"\n{len(alvo)} ausentes citadas por >=4 secoes do survey:\n")
for v in alvo:
    t = re.sub(r"^\S+ et al\.? \(\d{4}[a-z]?\)|^\S+ and \S+ \(\d{4}[a-z]?\)|^\S+ \(\d{4}[a-z]?\)","",v["raw"]).strip()
    print(f"  [{v['n_sec']}sec] {t[:118]}")
json.dump({"ausentes": nao}, open("survey-ausentes.json","w"), indent=0)
