import urllib.request, urllib.parse, re, sys, time, json

def query(titulo, tenta=3):
    q = urllib.parse.urlencode({"search_query": f'ti:"{titulo}"',
                                "max_results": "5", "start": "0"})
    url = "http://export.arxiv.org/api/query?" + q
    for i in range(tenta):
        try:
            with urllib.request.urlopen(url, timeout=40) as r: xml = r.read().decode()
            if len(xml) < 200: time.sleep(3); continue
            out = []
            for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
                aid = re.search(r"<id>http://arxiv\.org/abs/(\d{4}\.\d{4,5})", e)
                tit = re.search(r"<title>(.*?)</title>", e, re.S)
                aut = re.findall(r"<name>([^<]+)</name>", e)
                if aid and tit:
                    out.append({"id": aid.group(1),
                                "titulo": re.sub(r"\s+"," ",tit.group(1)).strip(),
                                "autores": aut})
            return out
        except Exception as ex:
            if i == tenta-1: return {"erro": str(ex)}
            time.sleep(3)
    return {"erro": "corpo vazio em todas as tentativas"}

# CONTROLE POSITIVO: titulos cujo ID nos conhecemos
CTRL = {"LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory":"2410.10813",
        "HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering":"1809.09600"}
print("CONTROLE POSITIVO — a busca por titulo tem de devolver o ID conhecido")
for t, esperado in CTRL.items():
    r = query(t); time.sleep(3)
    if isinstance(r, dict): sys.exit(f"  FALHOU (rede): {r['erro']}")
    ids = [x["id"] for x in r]
    print(f"  {t[:44]:46} -> {ids[:3]} {'✓' if esperado in ids else '✗ ESPERADO '+esperado}")
    if esperado not in ids:
        sys.exit("CONTROLE FALHOU: a busca nao acha ID conhecido — resultado nao confiavel")
print("  ⇒ busca confiavel\n")

ALVOS = ["A survey on the memory mechanism of large language model based agents",
         "From isolated conversations to hierarchical schemas dynamic tree memory representation",
         "Beyond Goldfish Memory: Long-Term Open-Domain Conversation",
         "When Not to Trust Language Models: Investigating Effectiveness of Parametric and Non-Parametric Memories",
         "In Prospect and Retrospect: Reflective Memory Management for Long-term Personalized Dialogue Agents"]
res = {}
for t in ALVOS:
    r = query(t); time.sleep(3)
    print(f"--- {t[:66]}")
    if isinstance(r, dict): print(f"    ERRO: {r['erro']}"); continue
    if not r: print("    (nenhum resultado)"); continue
    for x in r[:2]:
        print(f"    {x['id']}  {x['titulo'][:70]}")
        print(f"           autores: {', '.join(a.split()[-1] for a in x['autores'][:8])}")
    res[t] = r
json.dump(res, open("arxiv-busca.json","w"), indent=1)
