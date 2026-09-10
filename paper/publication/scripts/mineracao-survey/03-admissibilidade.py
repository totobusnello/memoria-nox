import json, re
aus = json.load(open("survey-ausentes.json"))["ausentes"]
sec = json.load(open("survey-secoes.json"))

# admissibilidade: decidida por mim, contra o que o NOSSO texto discute
ADM = {
 "memory mechanism of large language model":("A","survey do nosso proprio tema; §1.5 Related Work"),
 "survey of self-evolving agents":("A","auto-evolucao — nosso crystallize/reflect"),
 "reasoningbank":("A","destila estrategia de experiencia = analogo do nosso crystallize"),
 "beyond goldfish memory":("A","antecessor direto do LoCoMo/LongMemEval que usamos no §6"),
 "mirix":("A","memoria multi-agente — nosso cross_search entre 6 agentes"),
 "hierarchical schemas":("A","memoria hierarquica de conversa vs. nosso entity/section"),
 "mem-":("B","RL aprende a construir memoria vs. nossa formula fixa de salience"),
 "memory-r1":("B","RL para operacoes de memoria — mesmo contraste"),
 "memory as action":("B","curadoria de contexto vs. nosso retention tipado"),
 "mem1":("B","idem, com consolidacao"),
 "memagent":("B","long-context via memoria"),
 "in prospect and retrospect":("B","reflexao prospectiva/retrospectiva — nosso reflect"),
 "when not to trust language models":("B","quando recuperar vs. parametrico — §1.4"),
 "memsearcher":("C","agentic retrieval, ao lado de IRCoT/Self-Ask que ja citamos"),
 "webcoach":("C","memoria cross-session, mas em agente web (fora do nosso setup)"),
 "webarena":("X","benchmark de agente web — nao medimos"),
 "swe-bench":("X","benchmark de codigo — nao medimos"),
 "osworld":("X","benchmark de SO — nao medimos"),
 "voyager":("X","agente embodied — fora"),
 "efficient memory management":("X","PagedAttention: 'memoria' de KV cache, HOMONIMO"),
 "learning on the job":("X","conducao autonoma — fora"),
}
def limpa(raw):
    t = re.sub(r"^.*?\(\d{4}[a-z]?\)\s*", "", raw, count=1)
    t = re.sub(r"^((?:[A-Z]\.\s*)+[A-ZÖÜÉ][\wÖÜÉéöü'’-]+,?\s*|and\s+|et al\.\s*)+", "", t)
    t = re.sub(r"\s*\.\s*(In |arXiv|Advances|Proceedings|Journal|Transactions).*$", "", t)
    return re.sub(r"\s+"," ",t).strip(" .")

out = []
for v in sorted(aus, key=lambda x: -x["n_sec"]):
    if v["n_sec"] < 4: continue
    t = limpa(v["raw"]); low = v["raw"].lower()
    g, por = next(((g,p) for k,(g,p) in ADM.items() if k in low), ("?","NAO CLASSIFICADA"))
    out.append({"titulo": t, "arxiv": v["arxiv"], "n_sec": v["n_sec"],
                "secoes": v["secoes"], "grupo": g, "porque": por, "raw": v["raw"][:300]})
naoclass = [c for c in out if c["grupo"]=="?"]
assert not naoclass, f"candidata sem classificacao: {[c['titulo'][:50] for c in naoclass]}"
json.dump(out, open("candidatas.json","w"), indent=1, ensure_ascii=False)

for g, rot in [("A","A — entram primeiro (vizinhanca direta, discussao ja existe)"),
               ("B","B — entram com uma frase de contraste no §1.4/§1.5"),
               ("C","C — marginais, entram so se sobrar necessidade"),
               ("X","X — RECUSADAS (seriam enchimento)")]:
    g_ = [c for c in out if c["grupo"]==g]
    print(f"\n{rot}  [{len(g_)}]")
    for c in g_:
        loc = f"arXiv:{c['arxiv']}" if c["arxiv"] else "SEM localizador no survey"
        print(f"  [{c['n_sec']}sec] {c['titulo'][:78]}")
        print(f"          {loc} · {c['porque']}")
print(f"\nadmissiveis (A+B+C) = {sum(1 for c in out if c['grupo'] in 'ABC')} · "
      f"recusadas = {sum(1 for c in out if c['grupo']=='X')}")
print(f"sem localizador entre as admissiveis: "
      f"{sum(1 for c in out if c['grupo'] in 'ABC' and not c['arxiv'])}")
