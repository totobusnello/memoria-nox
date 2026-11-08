import importlib.util, json, os, random, sys, collections
sys.path.insert(0, os.getcwd())
spec = importlib.util.spec_from_file_location("es", "e-smoke.py"); es = importlib.util.module_from_spec(spec); spec.loader.exec_module(es)
lme = es.lme; ep = es.e_prompts
data = {r["question_id"]: r for r in json.load(open(os.path.expanduser("~/datasets/longmemeval/longmemeval_s_cleaned.json")))}
s1 = json.load(open(es.P3 / "stage1-manifest.json"))["stage1"]; v13 = json.load(open(es.P3 / "v13-manifest.json"))["confirm"]
pool = sorted(set(es.all_blocks(data, s1)) - set(es.all_blocks(data, v13)))
sample = random.Random(es.SEED).sample(pool, es.N_BLOCKS)
rs = [json.loads(l) for l in open("runs/smoke-2026-11-08/smoke-calls.ndjson")]
targets = [(r["arm"], r["crit"], r["block"]) for r in rs if r["model"] == "gemini-2.5-pro" and not r["parse_ok"] and r["tcand"] > 1][:24]
shapes = collections.Counter(); usd = 0
for arm, crit, b in targets:
    gen = {"responseMimeType": "application/json", "temperature": 0.1}
    if arm == "b128": gen["thinkingConfig"] = {"thinkingBudget": 128}
    d = lme.post(lme.gurl("gemini-2.5-pro"), {"contents": [{"role": "user", "parts": [{"text": ep.PROMPTS[crit] + "\n\nConversa:\n" + sample[b]}]}], "generationConfig": gen}, {"Content-Type": "application/json"}, timeout=300)
    u = d.get("usageMetadata") or {}; usd += u.get("promptTokenCount", 0) * 1.25e-6 + (u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)) * 10e-6
    txt = "".join(p.get("text", "") for p in ((d.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    try:
        j = json.loads(txt)
        if isinstance(j, dict): s = "dict keys=" + ",".join(sorted(j))
        elif isinstance(j, list): s = "list of " + ",".join(sorted({type(x).__name__ + (":" + "/".join(sorted(x)) if isinstance(x, dict) else "") for x in j})) if j else "list empty"
        else: s = type(j).__name__
    except Exception as e:
        s = "unparseable: starts " + repr(txt.strip()[:2]) + " ends " + repr(txt.strip()[-2:]) + " len " + str(len(txt))
    shapes[(arm, crit, s)] += 1
for k, v in shapes.most_common(): print(v, k)
print("usd", round(usd, 4))
