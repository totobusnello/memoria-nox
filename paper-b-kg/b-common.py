"""Paper B: what the registered scripts share (PREREGISTRATION.md). Not run on its own.

Loaded by path (importlib), so every script runs under `python3 -I` from any directory, including
the tree `git archive` extracts from the tag. Standard library only.

The citation normalisers are copied verbatim from audits/2026-10-23-kg-s1-recheck-conferidor.py
(the P4 rule: alphanumeric, accent-, markup- and punctuation-insensitive, at least 12 characters),
and the judge prompt is the October prompt of audits/2026-10-22-kg-s1-precision.py with the four
principles of audits/2026-10-23-kg-s1-quatro-principios.md added as explicit rules (§4).
"""
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import random
import re
import sqlite3
import subprocess
import threading
import time
import unicodedata
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
D = "paper-b-kg"
TAG = "paper-b-prereg-v1.0"
SNAPSHOT_NAME = "daily-main-main-20261106030002-3269917-a12b890e65d84fb38d099684c2f802bd.db.gz"
SNAPSHOT_SHA256 = "14f5000a1b4dfe6cd0a0f78e57c0295d52d39049ebeaed1fc707a961af8dac4c"
POPULATION = 17667          # relations with live evidence in CENSUS-2026-11-06.json
N, N_MISMATCH, N_RANDOM = 300, 30, 60
CAP_USD = 1.0
CHUNK_CHARS = 6000          # what the October judge saw
COMMITS = ("FREEZE", "JUDGES", "SHEET", "HUMAN")

# Judge 1 is fixed by §4. Judge 2 is the pre-registration's open choice: the model named in the
# draft (gpt-6-luna) answers only through the Decisions API, which returns probabilities and no
# text, so it cannot copy the eight-word quote §4 requires. The scripts refuse to call judge 2
# until this block names a prose model and its list prices, which the tag then fixes.
JUDGE1 = {"name": "judge1", "family": "google", "model": "gemini-2.5-flash-lite",
          "usd_in": 0.10 / 1e6, "usd_out": 0.40 / 1e6}
JUDGE2 = {"name": "judge2", "family": "openai", "model": None, "usd_in": None, "usd_out": None}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ hashes and private paths
def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def sha_json(o):
    return sha_bytes(json.dumps(o, sort_keys=True, ensure_ascii=False).encode())


def inside_repo(p):
    p = pathlib.Path(p).resolve()
    d = p if p.is_dir() else p.parent
    while not d.exists():
        d = d.parent
    return subprocess.run(["git", "-C", str(d), "rev-parse"], capture_output=True).returncode == 0


def private(p):
    if inside_repo(p):
        raise SystemExit(f"refusing: {p} is inside a git repository; it holds private material")
    p = pathlib.Path(p)
    p.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(p, 0o700)
    return p


def write_private(path, text):
    path = pathlib.Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, 0o600)


def write_public(path, obj):
    """A commitment: counts, seeds and hashes only. Refuses a key or value that looks like text."""
    body = json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    for s in _strings(obj):
        if len(s) > 120 or "\n" in s:
            raise SystemExit(f"refusing to write {path}: a long string would leave the private side")
    pathlib.Path(path).write_text(body, encoding="utf-8")
    return body


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _strings(v)


# ------------------------------------------------------------------ the draw
def seed_of(tag_commit):
    """§3: the integer value of the first eight hex digits of the tag commit's sha."""
    if not re.fullmatch(r"[0-9a-f]{40}", tag_commit or ""):
        raise SystemExit(f"not a commit sha: {tag_commit!r}")
    return int(tag_commit[:8], 16)


POP_SQL = ("SELECT r.id FROM kg_relations r JOIN chunks c ON c.id = r.evidence_chunk_id "
           "ORDER BY r.id")
ROW_SQL = ("SELECT r.id, se.name, se.entity_type, r.relation_type, te.name, te.entity_type, "
           "r.relation_reason, r.created_at, r.evidence_chunk_id, c.source_file, c.chunk_text "
           "FROM kg_relations r "
           "JOIN kg_entities se ON se.id = r.source_entity_id "
           "JOIN kg_entities te ON te.id = r.target_entity_id "
           "JOIN chunks c ON c.id = r.evidence_chunk_id WHERE r.id = ?")


def ro(db_path):
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def population(con):
    return [i for (i,) in con.execute(POP_SQL)]


def draw(pop, seed, n=N):
    """§3: uniform without replacement over the population ordered by kg_relations.id."""
    return sorted(random.Random(seed).sample(sorted(pop), n))


def mismatch_ids(sample, seed, n=N_MISMATCH):
    """§6: n of the sampled relations, drawn with seed + 3."""
    return sorted(random.Random(seed + 3).sample(sorted(sample), n))


def other_chunk(con, rid, own_source, seed):
    """A live evidence chunk from a different document (source_file), drawn with seed + 3 and the
    relation id, so each choice is reproducible on its own."""
    cands = [cid for (cid,) in con.execute(
        "SELECT DISTINCT c.id FROM kg_relations r JOIN chunks c ON c.id = r.evidence_chunk_id "
        "WHERE c.source_file IS NOT ? ORDER BY c.id", (own_source,))]
    cid = random.Random(f"{seed + 3}:{rid}").choice(cands)
    src, text = con.execute("SELECT source_file, chunk_text FROM chunks WHERE id = ?", (cid,)).fetchone()
    return {"chunk_id": cid, "source_file": src, "chunk_text": text}


def row(con, rid, bucket):
    r = con.execute(ROW_SQL, (rid,)).fetchone()
    if r is None:
        raise SystemExit(f"relation {rid} has no live evidence")
    (rid, s, st, p, o, ot, reason, created, cid, src, text) = r
    return {"relation_id": rid, "source": s, "source_type": st, "predicate": p, "target": o,
            "target_type": ot, "relation_reason": reason, "created_at": created,
            "chunk_id": cid, "source_file": src, "bucket": bucket(src), "chunk_text": text or ""}


# ------------------------------------------------------------------ citation check (P4)
def _acc(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))


_Q = dict.fromkeys(map(ord, "“”‘’«»"), '"')
_D = dict.fromkeys(map(ord, "–—−"), "-")
MIN = 12


def n_markdown(s):
    s = _acc(s or "").translate(_Q).translate(_D)
    s = re.sub(r"<[^>\n]{1,24}>", " ", s)
    s = re.sub(r"\\(.)", r"\1", s)
    s = re.sub(r"[*_`#>|~]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = re.sub(r'\s+([,.;:!?)\]"])', r"\1", s)
    s = re.sub(r'(["(\[])\s+', r"\1", s)
    return s.strip()


def n_alnum(s):
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z ]+", " ", n_markdown(s))).strip()


def quote_ok(quote, text):
    q = n_alnum(quote)
    return len(q) >= MIN and q in n_alnum(text)


def swap_two(quote, rng):
    """§6 negative control: the quote with two of its words swapped (two positions holding
    different words, so the result differs after normalisation). None if no such pair exists."""
    ws = quote.split()
    pairs = [(i, j) for i in range(len(ws)) for j in range(i + 1, len(ws))
             if n_alnum(ws[i]) and n_alnum(ws[j]) and n_alnum(ws[i]) != n_alnum(ws[j])]
    if not pairs:
        return None
    i, j = rng.choice(pairs)
    ws[i], ws[j] = ws[j], ws[i]
    return " ".join(ws)


# ------------------------------------------------------------------ markers (§5 item 2)
EXCEPTION = re.compile(r"\b(exceto|except|unless|other than)\b", re.I)
EXAMPLE = re.compile(r"(\bEx:|\be\.g\.|\bpor exemplo\b)", re.I)


def marker(text):
    """'exception', 'example', 'both' or None: the October enumeration for P1 and P3."""
    a, b = bool(EXCEPTION.search(text or "")), bool(EXAMPLE.search(text or ""))
    return "both" if a and b else "exception" if a else "example" if b else None


# ------------------------------------------------------------------ statistics
def wilson(k, n, z=1.959963984540054):
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(c - h, 4), round(c + h, 4)]


def kappa(a, b):
    """Cohen's kappa for two binary label lists of equal length; None when undefined."""
    n = len(a)
    if not n or n != len(b):
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


# ------------------------------------------------------------------ the judges
PROMPT = """Abaixo há uma TRIPLA extraída de um grafo de conhecimento e o TRECHO que foi registrado
como sua evidência. Decida se o trecho sustenta a tripla **como ela está escrita**.

TRIPLA:  ({s}) --[{p}]--> ({o})

TRECHO (a evidência registrada):
---
{t}
---

Regras:
- Os dois lados têm de aparecer no trecho, ou ser inequívocos a partir dele.
- A relação `{p}` tem de ser a que o trecho afirma. "Aparecem na mesma frase" NÃO é relação,
  a menos que a relação declarada seja exatamente de menção conjunta.
- Se a tripla INVERTE a relação (troca quem faz e quem sofre, ou afirma o que o trecho exclui),
  ela NÃO é sustentada, mesmo com as duas entidades lado a lado e uma frase literal.
- Se o predicado é mais pobre ou mais genérico que o trecho, mas não o contradiz nem o inverte,
  a tripla É sustentada.
- Um nome de exemplo dentro de um exemplo ilustrativo (um modelo, um marcador de lugar como
  "Fulano", "X" ou "<nome>") não é uma entidade: a tripla que o usa NÃO é sustentada.
- Formatação (negrito, tabelas, pontuação, quebras de linha) nunca é motivo para rejeitar.
- Se sustenta, copie as **8 primeiras palavras** da frase do trecho que sustenta, exatamente
  como aparecem, sem reescrever e sem juntar pedaços de lugares diferentes.

Devolva JSON:
{{"sustenta": true|false,
  "oito_palavras": "<... ou vazio>",
  "erro": "nenhum"|"entidade_ausente"|"relacao_errada"|"so_co_ocorrencia"|"vago_demais"|"invertida",
  "motivo": "<uma frase>"}}"""


def prompt(item, text):
    return PROMPT.format(s=item["source"], p=item["predicate"], o=item["target"],
                         t=(text or "")[:CHUNK_CHARS])


def jload(txt):
    """The October tolerant JSON reader (audits/2026-10-22-kg-s1-precision.py)."""
    def fix(o):
        if isinstance(o, list):
            return next((x for x in o if isinstance(x, dict)), None)
        return o if isinstance(o, dict) else None
    for att in (txt, re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", txt or "")):
        for f in (lambda s: json.loads(s, strict=False),
                  lambda s: json.JSONDecoder(strict=False).raw_decode(s.lstrip())[0]):
            try:
                return fix(f(att))
            except Exception:
                pass
        m = re.search(r"[\{\[].*[\}\]]", att or "", re.S)
        if m:
            try:
                return fix(json.loads(m.group(0), strict=False))
            except Exception:
                pass
    return None


class Cache:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.db.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT)")
            self.db.commit()
        os.chmod(path, 0o600)

    def get(self, k):
        with self.lock:
            r = self.db.execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def put(self, k, v):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO c VALUES (?,?)", (k, json.dumps(v)))
            self.db.commit()


class Ledger:
    def __init__(self, cap=CAP_USD):
        self.cap, self.usd, self.calls, self.cached = cap, 0.0, 0, 0
        self.lock = threading.Lock()

    def add(self, usd):
        with self.lock:
            self.usd += usd
            self.calls += 1
            if self.usd > self.cap:
                raise SystemExit(f"CAP REACHED: US$ {self.usd:.4f} > {self.cap}")


def post(url, body, hdr, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdr)
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode(errors='replace')[:160]}"
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
        time.sleep(2 * (a + 1))
    raise RuntimeError(last)


def call_gemini(judge, text):
    d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{judge['model']}"
             f":generateContent?key={os.environ['GEMINI_API_KEY']}",
             {"contents": [{"parts": [{"text": text}]}],
              "generationConfig": {"temperature": 0.0, "maxOutputTokens": 700,
                                   "responseMimeType": "application/json"}},
             {"Content-Type": "application/json"})
    c = (d.get("candidates") or [{}])[0]
    out = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or []).strip()
    u = d.get("usageMetadata") or {}
    tin = u.get("promptTokenCount", 0) or 0
    tout = (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0)
    return out, tin, tout, d.get("modelVersion")


def call_openai(judge, text):
    d = post("https://api.openai.com/v1/chat/completions",
             {"model": judge["model"], "temperature": 0,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": text}]},
             {"Content-Type": "application/json",
              "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    out = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    u = d.get("usage") or {}
    return out.strip(), u.get("prompt_tokens", 0) or 0, u.get("completion_tokens", 0) or 0, d.get("model")


CALLERS = {"google": call_gemini, "openai": call_openai}


def ready(judge):
    missing = [k for k in ("model", "usd_in", "usd_out") if judge.get(k) is None]
    if missing:
        raise SystemExit(f"refusing: {judge['name']} has no {', '.join(missing)}; "
                         "the pre-registration must name it before the tag")


def judge_one(judge, cache, led, item, text, caller=None):
    """One verdict: the judge's claim, its quote, the P4 check, and verified = claim and check."""
    p = prompt(item, text)
    k = sha_bytes(json.dumps([judge["model"], p]).encode())
    hit = cache.get(k)
    if hit is not None:
        led.cached += 1
        return hit
    out, tin, tout, served = (caller or CALLERS[judge["family"]])(judge, p)
    led.add(tin * judge["usd_in"] + tout * judge["usd_out"])
    j = jload(out)
    if j is None or not isinstance(j.get("sustenta"), bool):
        raise RuntimeError(f"{judge['name']}: no boolean verdict")
    q = (j.get("oito_palavras") or "").strip()
    v = {"claims": j["sustenta"], "quote": q[:300], "quote_ok": quote_ok(q, text),
         "error_kind": str(j.get("erro") or "")[:40], "reason": str(j.get("motivo") or "")[:300],
         "served": served, "tin": tin, "tout": tout}
    v["verified"] = v["claims"] and v["quote_ok"]
    cache.put(k, v)
    return v


# ------------------------------------------------------------------ the public history
def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()[:200]}")
    return r


def commit_of(repo, ref):
    return git(repo, "rev-parse", f"{ref}^{{commit}}").stdout.strip()


def exists_at(repo, ref, name):
    return git(repo, "cat-file", "-e", f"{ref}:{D}/{name}-COMMITMENT.json", check=False).returncode == 0


def written_once(repo, name, c, main="origin/main"):
    hist = git(repo, "log", "--full-history", "--format=%H", main, "--",
               f"{D}/{name}-COMMITMENT.json").stdout.split()
    if hist != [c]:
        raise SystemExit(f"{name}-COMMITMENT.json on {main} was not written once, by {c[:12]}")


def tag_commit(repo, tag=TAG, main="origin/main", fetch=True):
    """The tag's commit, checked to be on the public main branch and to carry no commitment."""
    if fetch:
        git(repo, "fetch", "-q", "--tags", "origin", "main")
    if git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False).returncode:
        raise SystemExit(f"tag {tag} not found")
    t = commit_of(repo, tag)
    if git(repo, "merge-base", "--is-ancestor", t, main, check=False).returncode:
        raise SystemExit(f"tag {tag} is not on {main}")
    for n in COMMITS:
        if exists_at(repo, t, n):
            raise SystemExit(f"the tag already carries a {n}-COMMITMENT.json")
    return t


def ordered(repo, refs, tag=TAG, main="origin/main", fetch=True):
    """refs = [(name, commit), ...] in the registered order (COMMITS), after the tag. Each
    commitment is its own commit, descends from the previous one, is on the public main branch,
    was written once, and did not exist at the previous step. Returns the parsed commitments."""
    names = [n for n, _ in refs]
    if names != list(COMMITS[:len(names)]):
        raise SystemExit(f"commitments must come in the order {COMMITS}, got {names}")
    prev_name, prev = "tag", tag_commit(repo, tag, main, fetch)
    out = {"_tag": prev}
    for name, ref in refs:
        c = commit_of(repo, ref)
        if c == prev:
            raise SystemExit(f"the {name} commitment is the {prev_name}'s own commit")
        if git(repo, "merge-base", "--is-ancestor", prev, c, check=False).returncode:
            raise SystemExit(f"{ref} does not descend from the {prev_name} ({prev[:12]})")
        if git(repo, "merge-base", "--is-ancestor", c, main, check=False).returncode:
            raise SystemExit(f"{ref} is not on {main}")
        if exists_at(repo, prev, name):
            raise SystemExit(f"{name}-COMMITMENT.json already exists at the {prev_name}")
        written_once(repo, name, c, main)
        out[name] = json.loads(git(repo, "show", f"{c}:{D}/{name}-COMMITMENT.json").stdout)
        out[name]["_commit"] = c
        prev_name, prev = name, c
    return out


def same_private(commitment, key, path):
    got = sha_file(path)
    if commitment.get(key) != got:
        raise SystemExit(f"refusing: {path} sha256 {got[:12]} is not the committed {key}")
