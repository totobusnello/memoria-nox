#!/usr/bin/env python3
"""C2 shadow study: offline test of the registered scripts. No network, no key, no real record.

  python3 -I s-test.py            (from anywhere; needs git)

Builds a synthetic shadow directory (records in the field layout s-common.py assumes) in a
temporary directory outside any repository. Every model call is replaced by Paper D's
deterministic stubs (d-test.py: the distiller copies facts, the reader looks the parameter up, the
judges check the reference string); the writer stub is d-test's plus the two drop reasons it does
not produce. What is tested is the plumbing and every refusal, each with its matching offender:

  1. the eligible-block rule (pure function), one offender per reason, and the 500-character edge
  2. the stopping rule: reached before 2026-12-01, after it, never (shortfall on 2027-01-10)
  3. s-count: counts only; a sentinel planted in block text, unit text, session key and agent
     name appears nowhere in its output or log; a non-count field is refused before printing;
     the real thresholds on a world of 300 blocks from 100 sessions
  4. s-freeze select + commit (smoke): window, exclusions, byte-for-byte copy, modes 700/600; not
     due, existing output, a path inside the repository, a tampered or ineligible frozen record,
     a wrong excluded file and a registered commit outside ~/Backups are refused
  5. s-generate (smoke): Paper D's validation, parity with d-generate on the same text; the draw
     (seed, seed + 1); a tampered manifest is refused
  6. s-run (smoke): estimate without --yes; arms ordered A > C2 > C0, C2-cut = 0; the cut; a
     changed questions file, a cap above US$ 5 and a run that reaches its cap are refused
  7. s-human (smoke, n 20): blind sheet; an edited answer and a changed results.json are refused
  8. s-read (smoke): controls first, H-S1/H-S2, the not-interpreted path
  9. the order of the public history in a scratch repository with a local origin, and the
     commitments and printed output free of the sentinel
"""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import random
import re
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
os.environ.setdefault("GEMINI_API_KEY", "test-not-a-key")
os.environ.setdefault("OPENAI_API_KEY", "test-not-a-key")
FAILS = []
SENT = "ZZSENTINELZZ"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DT = load("dtest_for_shadow", HERE / "d-test.py")      # Paper D's stubs
SC = load("scommon_test", HERE / "s-common.py")


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def refuses(fn, needle):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
    except SystemExit as e:
        return needle in str(e.code)
    return False


def call(fn, *args, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*args, **kw)
    return r, buf.getvalue()


def parsed(r):
    """s-count's JSON block, or {} when it cannot be read (the failing check then says so)."""
    try:
        return json.loads(r.stdout.split("\neligible blocks")[0]) if r.returncode == 0 else {}
    except ValueError:
        return {}


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ stubs
def stub_ask(prompt):
    """d-test's writer, plus an answer over 25 words and a fact without citation."""
    txt, served = DT.stub_ask(prompt)
    d = json.loads(txt)
    cat = "decision" if "- decision:" in prompt else "identificador"
    d["fatos"] += [{"pergunta": "Q longa?", "resposta": " ".join(["palavra"] * 30), "citacoes": ["x"],
                    "categoria": cat},
                   {"pergunta": "Q sem citacao?", "resposta": "curta", "citacoes": [], "categoria": cat}]
    return json.dumps(d), served


# ------------------------------------------------------------------ synthetic records
class World:
    def __init__(self, root):
        self.dir = root
        self.dir.mkdir(parents=True)
        self.files = {}
        self.nblock = 0

    def sentence(self, s, b, k):
        return f"Na sessao {s} decidimos que o parametro p{b}x{k} fica em {100 + 7 * k + b} unidades."

    def block(self, s, n=10, long=False):
        """A block of n facts; `long` puts them on one line, as production keeps a line longer than
        2,000 characters whole. Returns (text, [(param, value, k)])."""
        b = self.nblock = self.nblock + 1
        facts = [(f"p{b}x{k}", 100 + 7 * k + b, k) for k in range(n)]
        sents = [self.sentence(s, b, k) + " Seguimos com o resto do trabalho." for k in range(n)]
        if long:
            text = "[USER]: " + " ".join(sents)
        else:
            text = "\n".join(f"[{'USER' if k % 2 == 0 else 'ASSISTANT'}]: {x}" for k, x in enumerate(sents))
        return text, facts

    def record(self, key, agent, text, facts, **over):
        unit = lambda p, v, imp: {"text": f"o parametro {p} fica em {v} unidades", "category": "decision",
                                  "importance": imp}
        r = {"session_key": key, "agent": agent, "v": 1, "block_index": 0, "n_blocks": 1, "message_count": 10,
             "session_mtime": "2026-11-08T10:00:00Z", "block": text, "block_sha256": sha(text),
             "c0_units": [unit(p, v, 0.7) for p, v, k in facts if k % 3 == 0],
             "c2": {"ok": True, "error": None, "prompt_sha256": SC.C2_PROMPT_SHA256, "model_version": "stub",
                    "usage": {"promptTokenCount": 900, "candidatesTokenCount": 80},
                    "units": [unit(p, v, 0.6) for p, v, k in facts if k % 2 == 0]}}
        for k, v in over.items():
            if k.startswith("c2_"):
                r["c2"][k[3:]] = v
            else:
                r[k] = v
        return r

    def add(self, date, rec):
        line = rec if isinstance(rec, str) else json.dumps(rec, ensure_ascii=False)
        self.files.setdefault(date, []).append(line)

    def write(self):
        for d, lines in self.files.items():
            (self.dir / f"c2-shadow-{d}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def uuid(i):
    return f"{i:08x}-0000-4000-8000-{i:012x}"


def small_world(root):
    """Eight sessions over 2026-11-08..12, one offender of each kind, the excluded file, a file
    before the start and one after the freeze date. Returns (world, expected eligible counts)."""
    w = World(root)
    ex = [f"boris:{uuid(900 + i)}" for i in range(3)]
    for i, key in enumerate(ex + [ex[0]]):                # 3 sessions, 4 blocks
        t, f = w.block(900, 3)
        w.add("2026-11-07", w.record(key, "boris", t, f))
    t, f = w.block(901, 6)
    w.add("2026-11-06", w.record(f"boris:{uuid(901)}", "boris", t, f))
    keys = [f"boris:{uuid(i)}" for i in range(1, 8)] + [f"forge:{SENT}-{uuid(8)}"]
    agents = ["boris", "forge"] * 3 + ["boris", f"{SENT}-agent"]
    elig_blocks, elig_sessions = 0, set()
    for i, (key, ag) in enumerate(zip(keys, agents)):
        for j in range(3):
            date = f"2026-11-{8 + (i + j) % 5:02d}"
            t, f = w.block(i + 1, 10 if j else 60, long=(j == 0))
            rec = w.record(key, ag, t, f)
            if i == 0 and j == 1:                         # sentinel in a unit's text
                rec["c2"]["units"].append({"text": f"nota {SENT}", "category": "context", "importance": 0.9})
            if i == 1 and j == 1:                         # sentinel in the block text
                t2 = t + f"\n[USER]: lembrete {SENT}"
                rec.update(block=t2, block_sha256=sha(t2))
            w.add(date, rec)
            elig_blocks += 1
            elig_sessions.add(key)
    # offenders, each with exactly one defect
    base = lambda: w.block(50, 10)
    t, f = base(); w.add("2026-11-09", w.record(f"boris:{uuid(50)}", "boris", t, f, c2_prompt_sha256="0" * 64))
    t, f = base(); w.add("2026-11-09", w.record(f"boris:{uuid(51)}", "boris", t, f, block_sha256=sha(t + "x")))
    t, f = base(); w.add("2026-11-09", w.record(f"boris:{uuid(52)}", "boris", t, f, c2_ok=False, c2_error="HTTP 500"))
    t, f = base(); w.add("2026-11-09", w.record(f"boris:{uuid(53)}", "boris", t, f, c2_error="parse"))
    short = ("[USER]: curto " + SENT).ljust(499, ".")
    w.add("2026-11-10", w.record(f"boris:{uuid(54)}", "boris", short, []))
    edge = "[USER]: exatamente quinhentos".ljust(500, ".")
    w.add("2026-11-10", w.record(f"boris:{uuid(55)}", "boris", edge, []))
    elig_blocks += 1
    elig_sessions.add(f"boris:{uuid(55)}")
    t, f = base(); w.add("2026-11-11", w.record(ex[1], "boris", t, f))   # a later block of an excluded key
    w.add("2026-11-11", '{"session_key": "' + SENT + '", "block": not json')
    w.add("2026-11-11", json.dumps({"session_key": f"boris:{uuid(56)}", "block": "x" * 600,
                                    "block_sha256": sha("x" * 600), "c2": {"ok": True}}))   # no c0
    t, f = base(); w.add("2026-12-02", w.record(f"boris:{uuid(57)}", "boris", t, f))   # after the freeze date
    w.write()
    return w, {"blocks": elig_blocks, "sessions": len(elig_sessions), "ex": set(ex),
               "excluded": {"malformed": 2, "excluded_session": 1, "c2_failed": 2, "prompt_hash": 1,
                            "block_hash": 1, "short_block": 1}}


def big_world(root):
    """100 sessions x 3 blocks, one session a day apart, reaching 300 blocks from 100 sessions on
    the 25th file: 2026-12-02."""
    w = World(root)
    for i in range(3):
        t, f = w.block(900, 3)
        w.add("2026-11-07", w.record(f"boris:{uuid(900 + i)}", "boris", t, f))
    t, f = w.block(900, 3)
    w.add("2026-11-07", w.record(f"boris:{uuid(900)}", "boris", t, f))
    import datetime as dt
    d0 = dt.date(2026, 11, 8)
    for i in range(100):
        date = (d0 + dt.timedelta(days=i // 4)).isoformat()
        for _ in range(3):
            t, f = w.block(i, 8)
            w.add(date, w.record(f"forge:{uuid(i)}", "forge", t, f))
    w.write()
    return w


# ------------------------------------------------------------------ tests
def main():
    T = pathlib.Path(tempfile.mkdtemp(prefix="paper-d-shadow-test."))
    try:
        run_all(T)
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILS else f'{len(FAILS)} FAILED'}")
    return 1 if FAILS else 0


def modes_ok(p):
    p = pathlib.Path(p)
    ok = stat.S_IMODE(p.stat().st_mode) == 0o700
    for q in p.rglob("*"):
        ok &= stat.S_IMODE(q.stat().st_mode) == (0o700 if q.is_dir() else 0o600)
    return ok


def run_all(T):
    print("1. the eligible-block rule")
    L = load("lme_test", HERE.parent / "paper3-construction/lme-run.py")
    check(sha(L.DISTILL_SYSTEM_V3) == SC.C2_PROMPT_SHA256, "the registered C2 hash is Paper 3's DISTILL_SYSTEM_V3")
    w = World(T / "unit")
    t, f = w.block(1, 10)
    good = w.record("boris:k", "boris", t, f)
    check(SC.eligible(good, set()) == (True, None), "a good record is eligible")
    cases = {"prompt_hash": dict(c2_prompt_sha256="1" * 64), "block_hash": dict(block_sha256=sha(t + " ")),
             "c2_failed": dict(c2_ok=False), "excluded_session": {}}
    for why, over in cases.items():
        r = w.record("boris:k", "boris", t, f, **over)
        r2 = dict(r, c2=dict(r["c2"], error="boom")) if why == "c2_failed" else r
        check(SC.eligible(r, {"boris:k"} if why == "excluded_session" else set()) == (False, why),
              f"offender refused for {why}")
        if why == "c2_failed":
            check(SC.eligible(dict(good, c2=dict(good["c2"], error="boom")), set()) == (False, "c2_failed"),
                  "ok with an error is a failed C2 call")
    for n, want in ((499, (False, "short_block")), (500, (True, None))):
        s = "[USER]: x".ljust(n, ".")
        check(SC.eligible(w.record("boris:k", "boris", s, []), set()) == want, f"a block of {n} characters: {want}")
    check(SC.eligible({"session_key": "k"}, set()) == (False, "malformed") and
          SC.eligible(None, set()) == (False, "malformed"), "a malformed record is refused")
    check(SC.eligible(w.record("boris:k", "boris", t, [], c0={"units": []}), set()) == (True, None),
          "a block where C0 returned no unit stays eligible (the comparator's output never selects)")
    check(SC.seed_from_commit("abcdef12" + "0" * 32) == 0xABCDEF12 and
          refuses(lambda: SC.seed_from_commit("abcdef12"), "not a full commit"), "seed = first 8 hex of the tag commit")

    print("2. the stopping rule")
    mk = lambda pairs: {d: {"cum_eligible_blocks": b, "cum_eligible_sessions": s} for d, b, s in pairs}
    st = SC.stopping(mk([("2026-11-20", 310, 101)]), "2026-11-25")
    check(st["reach_date"] == "2026-11-20" and st["freeze_date"] == "2026-12-01" and not st["due"],
          "reached before 2026-12-01: the freeze date is 2026-12-01, not due before it")
    check(SC.stopping(mk([("2026-11-20", 310, 101)]), "2026-12-01")["due"], "due on 2026-12-01")
    st = SC.stopping(mk([("2026-12-01", 299, 150), ("2026-12-05", 300, 99), ("2026-12-09", 320, 100)]), "2026-12-20")
    check(st["freeze_date"] == "2026-12-09" and st["due"] and not st["shortfall"],
          "after 2026-12-01: the first date with 300 blocks AND 100 sessions")
    st = SC.stopping(mk([("2027-01-09", 200, 80)]), "2027-01-09")
    check(st["freeze_date"] is None and not st["due"], "never reached, before 2027-01-10: not due")
    st = SC.stopping(mk([("2027-01-10", 200, 80)]), "2027-01-10")
    check(st["freeze_date"] == "2027-01-10" and st["due"] and st["shortfall"], "2027-01-10 comes first: shortfall")

    print("3. s-count")
    W, want = small_world(T / "shadow")
    recs = [json.loads(l) for d in W.files if "2026-11-08" <= d for l in W.files[d] if l.startswith("{")
            and l.endswith("}")]
    el = [r for r in recs if SC.eligible(r, want["ex"])[0]]
    check(any(SENT in r["session_key"] for r in el) and any(SENT in (r.get("agent") or "") for r in el) and
          any(SENT in r["block"] for r in el) and any(SENT in u["text"] for r in el for u in r["c2"]["units"]),
          "positive control: the sentinel is in an eligible record's key, agent, block and unit text")
    log = T / "counts.log"
    cnt = [sys.executable, "-I", str(HERE / "s-count.py"), "--src", str(W.dir), "--log", str(log)]
    r = subprocess.run(cnt + ["--smoke", "--today", "2026-12-03"], capture_output=True, text=True)
    # the privacy check first, on the raw text, before anything parses the output
    leak = SENT in r.stdout or SENT in r.stderr or (log.exists() and SENT in log.read_text())
    check(r.returncode == 0 and not leak and log.read_text().count("\n") == 1,
          "SENTINEL: nothing of block, unit, key or agent text in the output or the log")
    out = parsed(r)
    tot = out.get("totals", {})
    check(r.returncode == 0 and tot.get("eligible_blocks") == want["blocks"] + 1 and
          tot.get("excluded") == want["excluded"],
          f"counts {tot} (eligible {want['blocks']} + the block after the freeze date)")
    check(out.get("other_files") == {"files_before_start": 2, "files_after_window": 0},
          "the excluded file and the earlier one are outside the window")
    check(set(out.get("per_date", {}).get("2026-11-09", {})) == SC.load("x", HERE / "s-count.py").DAY_KEYS,
          "per date: records, failures, eligible blocks/sessions, cumulative, exclusions by reason")
    check(out.get("stopping", {}).get("threshold_met") is False, "the real thresholds are not met by 26 blocks")
    r = subprocess.run(cnt + ["--today", "2026-12-03"], capture_output=True, text=True)
    check(r.returncode != 0 and "smoke" in r.stderr, "--today without --smoke is refused")
    SCN = load("scount_t", HERE / "s-count.py")
    bad = SCN.measure(W.dir, "2026-12-03", True)
    bad["per_date"]["2026-11-09"]["note"] = SENT
    check(refuses(lambda: SCN.counts_only(bad), "not a permitted count"), "a field outside the positive list is refused")
    bad = SCN.measure(W.dir, "2026-12-03", True)
    bad["stopping"]["reach_date"] = SENT
    check(refuses(lambda: SCN.counts_only(bad), "not a permitted count"), "a text value in a date field is refused")
    shutil.copytree(W.dir, T / "shadow-badex")
    (T / "shadow-badex" / SC.EXCLUDED_FILE).write_text(
        "\n".join((W.dir / SC.EXCLUDED_FILE).read_text().splitlines()[:3]) + "\n")
    r = subprocess.run([sys.executable, "-I", str(HERE / "s-count.py"), "--src", str(T / "shadow-badex"),
                        "--log", str(T / "c2.log"), "--smoke", "--today", "2026-12-03"], capture_output=True, text=True)
    check(r.returncode != 0 and "registered 3 and 4" in r.stderr and SENT not in r.stderr,
          "an excluded file without 3 sessions and 4 blocks is refused")
    BW = big_world(T / "big")
    for today, reach, due in (("2026-12-01", None, False), ("2026-12-02", "2026-12-02", True)):
        r = subprocess.run([sys.executable, "-I", str(HERE / "s-count.py"), "--src", str(BW.dir), "--log",
                            str(T / "big.log"), "--smoke", "--today", today], capture_output=True, text=True)
        s = parsed(r).get("stopping", {})
        check(r.returncode == 0 and s.get("reach_date") == reach and s.get("due") is due,
              f"real thresholds (300 blocks, 100 sessions reached by the 2026-12-02 file): on {today} "
              f"reach {s.get('reach_date')}, due {s.get('due')}")

    print("4. s-freeze")
    FZ = load("sfreeze_t", HERE / "s-freeze.py")
    FZ.C.MIN_BLOCKS, FZ.C.MIN_SESSIONS = 10, 5
    P = T / "private"
    out = P / "freeze"
    check(refuses(lambda: FZ.main(["select", "--src", str(W.dir), "--out", str(T / "nd"), "--smoke",
                                   "--today", "2026-11-30"]), "not due"), "a freeze before 2026-12-01 is refused")
    check(refuses(lambda: FZ.main(["select", "--src", str(W.dir), "--out", str(HERE / "x-out"), "--smoke",
                                   "--today", "2026-12-03"]), "inside a git repository"),
          "PRIVATE: an output inside the repository is refused")
    rc, o = call(FZ.main, ["select", "--src", str(W.dir), "--out", str(out), "--smoke", "--today", "2026-12-03"])
    fz = json.loads((out / "freeze.json").read_text())
    check(rc == 0 and fz["window"] == ["2026-11-08", "2026-12-01"] and
          fz["totals"]["eligible_blocks"] == want["blocks"] and fz["totals"]["eligible_sessions"] == want["sessions"],
          f"window to 2026-12-01; the 2026-12-02 block is not taken ({fz['totals']})")
    src_lines = {l for d in W.files if "2026-11-08" <= d <= "2026-12-01" for l in W.files[d]}
    frozen = [l for p in sorted((out / "records").iterdir()) for l in p.read_text().splitlines()]
    check(len(frozen) == want["blocks"] and all(l in src_lines for l in frozen), "records copied byte for byte")
    check(all(SC.eligible(json.loads(l), set())[0] for l in frozen) and
          not any(SC.r_session(json.loads(l)) in want["ex"] for l in frozen),
          "only eligible records, none of the excluded sessions")
    check(modes_ok(out), "PRIVATE: directory 700, files 600")
    check(SENT not in o and SENT not in (out / "freeze.json").read_text(), "SENTINEL: not in select's output or freeze.json")
    check(refuses(lambda: FZ.main(["select", "--src", str(W.dir), "--out", str(out), "--smoke",
                                   "--today", "2026-12-03"]), "made once"), "a second freeze into the same dir is refused")
    check(refuses(lambda: FZ.main(["commit", "--private", str(P)]), "~/Backups"),
          "a registered commitment outside ~/Backups is refused")
    check(refuses(lambda: FZ.main(["commit", "--private", str(P), "--smoke"]), "--seed"), "a smoke commit needs --seed")
    seed = 0x5EED1234
    rc, o = call(FZ.main, ["commit", "--private", str(P), "--smoke", "--seed", str(seed)])
    fc = json.loads((P / "SHADOW-FREEZE-COMMITMENT.json").read_text())
    check(rc == 0 and fc["seed"] == seed and fc["secondary_seed"] == seed + 1 and
          set(fc["frozen_files_sha256"]) == {f"records/{p.name}" for p in (out / "records").iterdir()},
          "commitment: seed, window and the sha256 of every frozen file")
    check(modes_ok(P), "PRIVATE: the private directory is 700/600 after the commit")
    # tamper: a frozen record whose prompt hash is changed, with the manifest rebuilt to match
    P2 = T / "private-tamper"
    shutil.copytree(P, P2)
    os.chmod(P2, 0o700)
    rp = sorted((P2 / "freeze" / "records").iterdir())[0]
    os.chmod(rp, 0o600)
    lines = rp.read_text().splitlines()
    lines[0] = lines[0].replace(SC.C2_PROMPT_SHA256, "0" * 64)
    rp.write_text("\n".join(lines) + "\n")
    check(refuses(lambda: FZ.main(["commit", "--private", str(P2), "--smoke", "--seed", "1"]), "manifest"),
          "a changed frozen file is refused by the manifest")
    man = json.loads((P2 / "freeze" / "manifest.json").read_text())
    man[f"records/{rp.name}"] = SC.sha_file(rp)
    (P2 / "freeze" / "manifest.json").write_text(json.dumps(man))
    check(refuses(lambda: FZ.main(["commit", "--private", str(P2), "--smoke", "--seed", "1"]), "prompt_hash"),
          "MUTATION: a frozen record with a wrong prompt hash is refused even with a matching manifest")
    lines = rp.read_text().splitlines()
    rec = json.loads(lines[0].replace("0" * 64, SC.C2_PROMPT_SHA256))
    rec["block"] = rec["block"] + " "
    lines[0] = json.dumps(rec, ensure_ascii=False)
    rp.write_text("\n".join(lines) + "\n")
    man[f"records/{rp.name}"] = SC.sha_file(rp)
    (P2 / "freeze" / "manifest.json").write_text(json.dumps(man))
    check(refuses(lambda: FZ.main(["commit", "--private", str(P2), "--smoke", "--seed", "1"]), "block_hash"),
          "MUTATION: a frozen block whose text no longer matches its hash is refused")

    print("5. s-generate")
    GN = load("sgen_t", HERE / "s-generate.py")
    GN.C.N_DRAW = 25
    check(refuses(lambda: GN.main(["--private", str(HERE / "x-priv"), "--smoke"], ask=stub_ask),
                  "inside a git repository"), "PRIVATE: a private dir inside the repository is refused")
    check(refuses(lambda: GN.main(["--private", str(T / "nowhere"), "--smoke"], ask=stub_ask), "missing"),
          "CHAIN: a missing freeze commitment is refused")
    rc, o = call(GN.main, ["--private", str(P), "--smoke"], ask=stub_ask)
    qc = json.loads((P / "SHADOW-QUESTIONS-COMMITMENT.json").read_text())
    check(rc == 0 and qc["questions"]["primary"] == 25 and qc["validated"]["primary"] > 25,
          f"primary set drawn to 25 of {qc['validated']['primary']}")
    d = qc["drops"]["primary"]
    check(all(d.get(k, 0) > 0 for k in ("malformed", "answer_too_long", "category_outside", "no_citation",
                                        "citation_not_verbatim")), f"drops by reason {d}")
    check(qc["writer_over_max_facts"]["primary"] > 0, "outputs over 2 facts counted, not cut")
    val = [json.loads(x) for x in open(P / "validated.jsonl")]
    qs = [json.loads(x) for x in open(P / "questions.jsonl")]
    for s_, sd in (("primary", seed), ("secondary", seed + 1)):
        vv = sorted((q for q in val if q["set"] == s_), key=lambda q: q["qid"])
        exp = sorted(q["qid"] for q in (random.Random(sd).sample(vv, 25) if len(vv) > 25 else vv))
        check(sorted(q["qid"] for q in qs if q["set"] == s_) == exp, f"the {s_} draw uses seed {'+ 1' if sd != seed else ''}".strip())
    texts = {bid: SC.r_block(r) for bid, _, r in SC.frozen_records(P / "freeze")}
    check(all(all(c in texts[q["block"]][q["ev_lo"]:q["ev_hi"]] for c in q["citations"]) for q in qs),
          "every citation lies inside its evidence region, inside the block")
    check(GN.PROMPTS["primary"].count("até 2 fatos") == 1 and GN.PROMPTS["secondary"].count("até 2 fatos") == 1
          and GN.PROMPTS["primary"].replace("até 2 fatos", "até 4 fatos") == GN.SM.PRIMARY,
          "Paper D's prompts, the fact count the only change")
    calls = qc["writer_calls_this_run"]
    rc, _ = call(GN.main, ["--private", str(P), "--smoke"], ask=lambda p: (_ for _ in ()).throw(RuntimeError("no call")))
    check(calls == 2 * qc["blocks"] and json.loads((P / "SHADOW-QUESTIONS-COMMITMENT.json").read_text())
          ["writer_calls_this_run"] == 0, "each block goes to the writer once per prompt; a rerun is served from cache")
    parity(T, GN)
    P3 = T / "private-man"
    shutil.copytree(P, P3)
    os.chmod(P3 / "freeze" / "freeze.json", 0o600)
    (P3 / "freeze" / "freeze.json").write_text("{}")
    check(refuses(lambda: GN.main(["--private", str(P3), "--smoke"], ask=stub_ask), "manifest"),
          "a tampered freeze is refused before any writer call")

    print("6. s-run")
    RN = load("srun_t", HERE / "s-run.py")
    rc, o = call(RN.main, ["--repo", str(HERE.parent), "--private", str(P), "--smoke"], post=DT.stub_post)
    check(rc == 0 and "estimate only" in o and not (P / "run" / "cache.sqlite").exists(), "without --yes nothing is called")
    check(refuses(lambda: RN.main(["--private", str(P), "--smoke", "--cap", "6"], post=DT.stub_post), "US$ 5"),
          "MUTATION: a cap above US$ 5 is refused")
    check(refuses(lambda: call(RN.main, ["--private", str(P), "--smoke", "--yes", "--cap", "0.00001"],
                               post=DT.stub_post), "CAP REACHED"), "MUTATION: the run stops when the ledger passes its cap")
    shutil.rmtree(P / "run")
    rc, o = call(RN.main, ["--repo", str(HERE.parent), "--private", str(P), "--smoke", "--yes"], post=DT.stub_post)
    res = json.loads((P / "run" / "results.json").read_text())
    check(rc == 0 and "sha256" in o and "accuracy" not in o.lower() and SENT not in o,
          "run prints counts and hashes only (SENTINEL absent)")
    check({r["arm"] for r in res["rows"]} == set(SC.ARMS) and len(res["rows"]) == 4 * len(qs), "every arm, every question")
    y = lambda arm: sum(r["j1"] for r in res["rows"] if r["arm"] == arm)
    check(y("A") > y("C2") > y("C0") and y("C2-cut") == 0,
          f"stub arms A {y('A')} > C2 {y('C2')} > C0 {y('C0')}, C2-cut {y('C2-cut')}")
    cb = res["cut_blocks"].values()
    check(any(not b["cut_empty"] and b["cut_units"] > 0 for b in cb) and any(b["cut_empty"] for b in cb),
          "C2-cut re-distils what is left of a long block; a block cut whole is not sent")
    long_q = next(q for q in qs if len(texts[q["block"]]) > 4000)
    cut = RN.cut_block(texts[long_q["block"]], [(q["ev_lo"], q["ev_hi"]) for q in qs if q["block"] == long_q["block"]])
    check(all(c not in cut for c in long_q["citations"]) and len(cut) < len(texts[long_q["block"]]),
          "the cut removes every citation of the block's questions")
    ts = [{"role": "x", "content": "abcdefghij"}]
    check(RN.cut_block("abcdefghij", [(2, 4), (7, 8)]) == "abefgij" ==
          RN.C.DC.cut_regions(ts, [(-3, 10)], [(2, 4), (7, 8)])[0]["content"], "cut_block is d-common.cut_regions on a block")
    rc2, _ = call(RN.main, ["--repo", str(HERE.parent), "--private", str(P), "--smoke", "--yes"], post=DT.stub_post)
    res2 = json.loads((P / "run" / "results.json").read_text())
    check(res2["meta"]["calls"]["cached"] > 0 and res2["meta"]["usd"] == 0, "a rerun is served from the cache")
    qb = (P / "questions.jsonl").read_bytes()
    (P / "questions.jsonl").write_bytes(qb.replace(b"unidades", b"unidade", 1))
    check(refuses(lambda: RN.main(["--private", str(P), "--smoke"], post=DT.stub_post), "questions.jsonl"),
          "a changed questions file is refused before any call")
    (P / "questions.jsonl").write_bytes(qb)

    print("7. s-human")
    HU = load("shum_t", HERE / "s-human.py")
    check(refuses(lambda: HU.main(["make", "--private", str(P), "--n", "20"]), "--smoke"), "n other than 60 needs --smoke")
    rc, o = call(HU.main, ["make", "--private", str(P), "--n", "20", "--smoke"])
    sheet = (P / "human-sample.csv").read_text()
    rows = list(csv.reader(io.StringIO(sheet)))
    check(rc == 0 and rows[0] == HU.H.COLS and len(rows) == 21, f"blind sheet: {rows[0]}")
    for row in rows[1:]:
        row[4] = "s" if row[2] in row[3] else "n"
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    good = buf.getvalue()
    rows[1][3] += " (editado)"
    buf2 = io.StringIO()
    csv.writer(buf2).writerows(rows)
    (P / "human-sample.csv").write_text(buf2.getvalue())
    check(refuses(lambda: call(HU.main, ["commit", "--private", str(P), "--n", "20", "--smoke"]), "texts"),
          "an edited answer in the sheet is refused")
    (P / "human-sample.csv").write_text(good)
    rb = (P / "run" / "results.json").read_bytes()
    (P / "run" / "results.json").write_bytes(rb.replace(b'"usd"', b'"usd" ', 1))
    check(refuses(lambda: call(HU.main, ["commit", "--private", str(P), "--n", "20", "--smoke"]), "results.json"),
          "a results.json other than the committed one is refused")
    (P / "run" / "results.json").write_bytes(rb)
    rc, o = call(HU.main, ["commit", "--private", str(P), "--n", "20", "--smoke"])
    hc = json.loads((P / "SHADOW-HUMAN-COMMITMENT.json").read_text())
    check(rc == 0 and hc["kappa"] == 1.0 and hc["seed"] == seed, f"commit; human = judge here, kappa {hc['kappa']}")

    print("8. s-read")
    RD = load("sread_t", HERE / "s-read.py")
    rc, o = call(RD.main, ["--private", str(P), "--smoke"])
    rj = json.loads((P / "read" / "reading.json").read_text())
    check(rc == 0 and o.startswith("CONTROLS") and set(rj["controls"]) == {"ceiling", "positive", "record_integrity"},
          "controls read first")
    check(rj["controls"]["record_integrity"]["pass"] and rj["controls"]["positive"]["value"] == 0 and rj["interpret"],
          f"integrity passes, C2-cut 0, interpreted ({rj['controls']['ceiling']})")
    h1 = rj["hypotheses"]["H-S1"]["j1"]
    check(h1["estimate"] > 0 and h1["ci95"][0] <= h1["estimate"] <= h1["ci95"][1] and
          h1["n_sessions"] == len({q["uuid"] for q in qs if q["set"] == "primary"}),
          f"H-S1 with sessions as clusters {h1}")
    check(RD.DR.C.SEED == seed and seed != 20261106,
          "the bootstrap runs on the seed of §3 (tag commit), not Paper D's 20261106")
    check("excludes_plus_0.10" in h1 and h1["excludes_plus_0.10"] == (h1["ci95"][1] < 0.10)
          and "lower_bound_above_plus_0.10" not in h1,
          "§5.2: 'excludes +0.10' is the upper bound below +0.10, as in Paper D")
    check("bracket" in rj["hypotheses"]["H-S1"] and "H-S2" in rj["hypotheses"], "judge-2 bracket; H-S2 apart")
    dsc = rj["descriptive"]
    check(dsc["blocks_with_no_unit"]["C0"] >= 1 and set(dsc["by_agent_j1"]) and
          dsc["tokens_and_cost"]["distill"]["C2"]["tokens_in"] == 900 * want["blocks"],
          "descriptives: empty blocks, by agent, C2 tokens from the record")
    RD2 = load("sread_t2", HERE / "s-read.py")
    RD2.C.GATES = {"ceiling": 1.01, "positive": 0.10}
    rc, o = call(RD2.main, ["--private", str(P), "--smoke"])
    rj2 = json.loads((P / "read" / "reading.json").read_text())
    check(not rj2["interpret"] and "NOT INTERPRETED" in o and "[not interpreted]" in o and
          rj2["hypotheses"]["H-S1"]["j1"] == h1, "a failed control: H-S1 reported, every number, not interpreted")
    check(refuses(lambda: RD.main(["--private", str(P)]), "--refs"), "the registered read needs the four commits")

    print("9. the public history, and the public files")
    for n in SC.COMMITS:
        body = (P / f"{n}-COMMITMENT.json").read_text()
        check(SENT not in body and "parametro" not in body, f"SENTINEL: {n}-COMMITMENT.json carries no text")
    order_tests(T)


def parity(T, GN):
    """s-generate's validation on a block equals d-generate's on a window holding the same text."""
    W = World(T / "parity")
    text, _ = W.block(7, 50, long=True)
    full = "user: " + text
    sess = T / "parity.jsonl"
    sess.write_text(json.dumps({"type": "user", "timestamp": "2026-09-01T10:00:00Z",
                                "message": {"role": "user", "content": text}}) + "\n")
    import collections
    dgen = GN.GEN
    dgen.G.ask, keep = stub_ask, dgen.G.ask
    try:
        d_drops = {s: collections.Counter() for s in SC.SETS}
        d_rows = dgen.session_questions(dgen.L.Cache(str(T / "pd.sqlite")), {"writer_calls": 0, "served":
                                        collections.Counter()}, d_drops, "u", sess, "2026-09-01")
    finally:
        dgen.G.ask = keep
    s_drops = {s: collections.Counter() for s in SC.SETS}
    rec = {"session_key": "u", "agent": "a", "block": full}
    s_rows = GN.block_questions(GN.L.Cache(str(T / "ps.sqlite")), {"writer_calls": 0, "served": collections.Counter()},
                                s_drops, collections.Counter(), "b", "2026-09-01", rec, stub_ask)
    key = lambda r: (r["set"], r["category"], r["question"], r["ref"], tuple(r["citations"]), r["ev_lo"], r["ev_hi"])
    check(len(d_rows) > 0 and [key(r) for r in d_rows] == [key(r) for r in s_rows] and d_drops == s_drops,
          f"PARITY with d-generate: {len(s_rows)} questions, drops {dict(s_drops['primary'])}")


def order_tests(T):
    C = SC
    g = lambda repo, *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True)
    origin, repo = T / "origin.git", T / "repo"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True, capture_output=True)
    (T / "nohooks").mkdir()
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false"),
                 ("tag.gpgsign", "false"), ("core.hooksPath", str(T / "nohooks"))):
        g(repo, "config", k, v)
    d = repo / C.D
    d.mkdir()
    PV = T / "pv"
    PV.mkdir()
    bodies = {n: json.dumps({"smoke": False, "n": i}) + "\n" for i, n in enumerate(C.COMMITS)}
    for n, b in bodies.items():
        (PV / f"{n}-COMMITMENT.json").write_text(b)

    def commit(name, body, to="main"):
        (d / name).write_text(body)
        g(repo, "add", str(d / name))
        g(repo, "commit", "-q", "--no-verify", "-m", name)
        g(repo, "push", "-q", "origin", f"HEAD:{to}")
        return g(repo, "rev-parse", "HEAD").stdout.strip()

    commit("SHADOW-PREREGISTRATION.md", "x")
    g(repo, "tag", "-a", C.TAG, "-m", "t")
    g(repo, "push", "-q", "origin", C.TAG)
    tagc = g(repo, "rev-parse", f"{C.TAG}^{{commit}}").stdout.strip()
    refs = [(n, commit(f"{n}-COMMITMENT.json", bodies[n])) for n in C.COMMITS]
    ok = True
    try:
        got = C.chain(repo, PV, refs, False)
    except SystemExit as e:
        ok, got = False, {}
        print("   ", e)
    check(ok and set(got) == set(C.COMMITS), "CHAIN: tag -> freeze -> questions -> results -> human passes")
    check(C.tag_seed(repo) == 1791502125 == 0x6AC8272D and (tagc[:8] == "6ac8272d" or C.tag_seed(repo) != int(tagc[:8], 16)),
          "§10: the seed is the registered 0x6ac8272d, not the digits of the commit the tag points to now")
    (PV / "SHADOW-RESULTS-COMMITMENT.json").write_text(bodies["SHADOW-RESULTS"].replace("2", "9"))
    check(refuses(lambda: C.chain(repo, PV, refs, False), "not the private copy"),
          "CHAIN: a private commitment that differs from the published one is refused")
    (PV / "SHADOW-RESULTS-COMMITMENT.json").unlink()
    check(refuses(lambda: C.chain(repo, PV, refs, False), "missing"), "CHAIN: a missing commitment is refused")
    (PV / "SHADOW-RESULTS-COMMITMENT.json").write_text(bodies["SHADOW-RESULTS"])
    check(refuses(lambda: C.chain(repo, PV, refs[:2], True), "smoke=False"),
          "a registered commitment is refused by a smoke step")
    check(refuses(lambda: C.chain(repo, PV, [refs[0], (refs[1][0], None)], False), "--refs"),
          "CHAIN: a step without the earlier commit is refused")
    check(refuses(lambda: C.chain(repo, PV, [refs[0], (refs[1][0], refs[0][1])], False), "own commit"),
          "CHAIN: two commitments in one commit are refused")
    check(refuses(lambda: C.chain(repo, PV, [(refs[0][0], tagc)], False), "own commit"),
          "CHAIN: a commitment at the tag is refused")
    check(refuses(lambda: C.same_as_tag(repo), "not the tag's"), "code that is not the tag's is refused")
    # out of order: the questions pushed before the freeze
    g(repo, "reset", "-q", "--hard", tagc)
    g(repo, "push", "-q", "-f", "origin", "HEAD:main")
    q2 = commit("SHADOW-QUESTIONS-COMMITMENT.json", bodies["SHADOW-QUESTIONS"])
    f2 = commit("SHADOW-FREEZE-COMMITMENT.json", bodies["SHADOW-FREEZE"])
    check(refuses(lambda: C.chain(repo, PV, [("SHADOW-FREEZE", f2), ("SHADOW-QUESTIONS", q2)], False),
                  "does not descend"), "CHAIN: a commitment out of order is refused")
    commit("SHADOW-FREEZE-COMMITMENT.json", '{"smoke": false, "n": 99}\n')
    check(refuses(lambda: C.chain(repo, PV, [("SHADOW-FREEZE", f2)], False), "written once"),
          "CHAIN: a commitment rewritten after its push is refused")
    g(repo, "checkout", "-q", "-b", "side", tagc)
    s = commit("SHADOW-FREEZE-COMMITMENT.json", bodies["SHADOW-FREEZE"], to="side")
    check(refuses(lambda: C.chain(repo, PV, [("SHADOW-FREEZE", s)], False), "not on origin/main"),
          "CHAIN: a commitment off origin/main is refused")
    # a tag that already carries a commitment of this study
    g(repo, "checkout", "-q", "main")
    g(repo, "tag", "-d", C.TAG)
    g(repo, "tag", "-a", C.TAG, "-m", "t2", f2)
    g(repo, "push", "-q", "-f", "origin", C.TAG)
    check(refuses(lambda: C.DC.ordered(repo, []), "already carries"), "CHAIN: a tag carrying a commitment is refused")


if __name__ == "__main__":
    sys.exit(main())
