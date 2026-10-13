#!/usr/bin/env python3
"""sprint-stanford-telemetry-deposit.py — validate the provider_telemetry export
prepared for a Zenodo deposit, recompute every number the 2026-09-08 e-mail to the
arXiv:2606.06448 authors asserted, write derived summaries, and run the privacy scan.

Read-only on its input. Writes only into --out (the deposit directory).

Usage:
  python3 sprint-stanford-telemetry-deposit.py --deposit <dir>

Exit code != 0 when: schema/window/contiguity check fails, a privacy check fails,
or a recomputed e-mail claim does not match at the rounding the e-mail used.
"""
import argparse, csv, hashlib, json, math, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

WIN_START_MS = 1786060800000  # 2026-08-07T00:00:00Z
WIN_END_MS = 1788825600000    # 2026-09-08T00:00:00Z (exclusive)
COLS = ["id", "timestamp_ms", "provider", "model", "op_type", "tokens_in", "tokens_out",
        "cost_estimate_usd", "latency_ms", "success", "caller", "phase", "tokens_src"]
# Closed vocabularies. Anything outside these is a privacy/schema failure, because a
# free-text value in a categorical column is exactly how content leaks into a dataset.
VOCAB = {
    "provider": {"gemini"},
    "model": {"gemini-embedding-001", "gemini-2.5-flash-lite"},
    "op_type": {"embed", "complete", "health_check"},
    "success": {"0", "1"},
    "phase": {"construction", "query", "maintenance"},
    "tokens_src": {"api", "estimated"},
    "caller": {"embed.embedQuery", "embed.batchEmbedDoc", "compact.gemini",
               "consolidate.gemini", "session-distill.gemini", "search-expansion.expand",
               "digest.gemini", "kg-llm.extract"},
}
SMOKE_TEST_IDS = {1, 2, 3, 4}  # deployment smoke test, 2026-08-07 (see README)

PRIVACY_PATTERNS = {
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "tailscale_100x": re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"),
    "vps_hostname": re.compile(r"srv\d{6,}", re.I),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "openai_like_key": re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),
    "groq_key": re.compile(r"\bgsk_[A-Za-z0-9]{20,}"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "bearer": re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}"),
    "key_param": re.compile(r"[?&]key=[A-Za-z0-9_\-]{10,}"),
    "private_path": re.compile(r"(/root/|/Users/|/home/|/var/lib/|/var/backups/|\.openclaw)"),
    "discord_webhook": re.compile(r"discord(?:app)?\.com/api/webhooks", re.I),
    "phone_br": re.compile(r"\+?55\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}"),
}
# Organisation/person names that must never appear in a public artifact of this project.
# Compared case-insensitively as whole words.
DENY_WORDS = ["nuvini", "galapagos", "galápagos", "treviso", "lombardia", "granix",
              "generantis", "whatsapp", "slack", "toto", "busnello_private"]


def utc(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def load(path):
    with open(path, newline="") as f:
        r = csv.reader(f)
        header = next(r)
        rows = [dict(zip(header, row)) for row in r]
    return header, rows


def validate(header, rows):
    errs = []
    if header != COLS:
        errs.append(f"header mismatch: {header}")
    ids = [int(x["id"]) for x in rows]
    if ids != list(range(ids[0], ids[0] + len(ids))):
        errs.append("ids not contiguous / not sorted")
    for x in rows:
        ts = int(x["timestamp_ms"])
        if not (WIN_START_MS <= ts < WIN_END_MS):
            errs.append(f"id {x['id']} outside window")
        for c, vocab in VOCAB.items():
            if x[c] not in vocab:
                errs.append(f"id {x['id']} column {c} value outside vocabulary")
        for c in ("tokens_in", "tokens_out", "latency_ms"):
            if x[c] == "" or int(x[c]) < 0:
                errs.append(f"id {x['id']} {c} null/negative")
        if float(x["cost_estimate_usd"]) < 0:
            errs.append(f"id {x['id']} negative cost")
    return errs


def recompute(rows):
    n = len(rows)
    cost = [float(x["cost_estimate_usd"]) for x in rows]
    total = math.fsum(cost)
    out = {"n_rows": n, "total_usd": total}
    ph = defaultdict(lambda: {"ops": 0, "usd": [], "tin": 0, "tout": 0, "days": set()})
    for x in rows:
        p = ph[x["phase"]]
        p["ops"] += 1
        p["usd"].append(float(x["cost_estimate_usd"]))
        p["tin"] += int(x["tokens_in"])
        p["tout"] += int(x["tokens_out"])
        p["days"].add(utc(int(x["timestamp_ms"])).date().isoformat())
    out["phases"] = {}
    for k, p in sorted(ph.items()):
        usd = math.fsum(p["usd"])
        out["phases"][k] = {
            "ops": p["ops"], "pct_ops": 100 * p["ops"] / n,
            "usd": usd, "pct_usd": 100 * usd / total,
            "usd_per_op": usd / p["ops"],
            "tokens_in": p["tin"], "tokens_out": p["tout"],
            "mean_tokens_in_per_call": p["tin"] / p["ops"],
            "usd_per_1k_input_tokens": 1000 * usd / p["tin"],
            "days_with_activity": len(p["days"]),
        }
    all_days = {utc(int(x["timestamp_ms"])).date().isoformat() for x in rows}
    out["days_with_data"] = len(all_days)
    # Concentration
    srt = sorted(rows, key=lambda x: float(x["cost_estimate_usd"]), reverse=True)
    top3 = srt[:3]
    out["top3"] = [{"id": int(x["id"]), "caller": x["caller"], "tokens_in": int(x["tokens_in"]),
                    "usd": float(x["cost_estimate_usd"])} for x in top3]
    top3_usd = math.fsum(float(x["cost_estimate_usd"]) for x in top3)
    out["top3_pct_ops"] = 100 * 3 / n
    out["top3_pct_usd"] = 100 * top3_usd / total
    c_usd = out["phases"]["construction"]["usd"]
    out["construction_pct_usd_without_top3"] = 100 * (c_usd - top3_usd) / (total - top3_usd) \
        if all(x["phase"] == "construction" for x in top3) else None
    acc, k = 0.0, 0
    for x in srt:
        acc += float(x["cost_estimate_usd"]); k += 1
        if acc >= total / 2:
            break
    out["calls_for_half_spend"] = k
    out["calls_for_half_spend_pct_ops"] = 100 * k / n
    out["queries_per_day"] = out["phases"]["query"]["ops"] / out["days_with_data"]
    # Weekly amortisation as recomputed in docs/STANFORD-A1-A3-MESSAGE.md:
    # (construction + maintenance USD) / query count, per ISO week (UTC), x1e-5 USD.
    wk = defaultdict(lambda: {"q": 0, "fixed": []})
    for x in rows:
        iso = utc(int(x["timestamp_ms"])).isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        if x["phase"] == "query":
            wk[key]["q"] += 1
        else:
            wk[key]["fixed"].append(float(x["cost_estimate_usd"]))
    out["weekly_amortised_fixed_cost_per_query_1e-5usd"] = {
        k: {"queries": v["q"], "value": round(1e5 * math.fsum(v["fixed"]) / v["q"], 2)}
        for k, v in sorted(wk.items())}
    out["tokens_src_counts"] = dict(Counter(x["tokens_src"] for x in rows))
    out["failed_calls"] = sum(1 for x in rows if x["success"] == "0")
    out["failed_calls_usd"] = math.fsum(float(x["cost_estimate_usd"]) for x in rows if x["success"] == "0")
    return out


# Each e-mail claim: (label, value-from-recompute, value asserted, rounding digits)
def claims(r):
    P = r["phases"]
    return [
        ("calls", r["n_rows"], 3544, 0),
        ("total USD", r["total_usd"], 0.1352, 4),
        ("construction % ops", P["construction"]["pct_ops"], 3.16, 2),
        ("construction % cost", P["construction"]["pct_usd"], 55.7, 1),
        ("query % ops", P["query"]["pct_ops"], 94.6, 1),
        ("query % cost", P["query"]["pct_usd"], 30.5, 1),
        ("maintenance % ops", P["maintenance"]["pct_ops"], 2.3, 1),
        ("maintenance % cost", P["maintenance"]["pct_usd"], 13.8, 1),
        ("construction USD/1k input tok", P["construction"]["usd_per_1k_input_tokens"], 0.000122, 6),
        ("query USD/1k input tok", P["query"]["usd_per_1k_input_tokens"], 0.000150, 6),
        ("maintenance USD/1k input tok", P["maintenance"]["usd_per_1k_input_tokens"], 0.000157, 6),
        ("mean input tokens per construction call", P["construction"]["mean_tokens_in_per_call"], 5500, -2),
        ("mean input tokens per query call", P["query"]["mean_tokens_in_per_call"], 82, 0),
        ("top-3 calls % ops", r["top3_pct_ops"], 0.08, 2),
        ("top-3 calls % cost", r["top3_pct_usd"], 29.7, 1),
        ("construction % cost without top 3", r["construction_pct_usd_without_top3"], 37.0, 1),
        ("calls holding half the spend", r["calls_for_half_spend"], 31, 0),
        ("calls holding half the spend, % ops", r["calls_for_half_spend_pct_ops"], 0.87, 2),
        ("days with data", r["days_with_data"], 32, 0),
        ("days with construction", P["construction"]["days_with_activity"], 19, 0),
        ("days with maintenance", P["maintenance"]["days_with_activity"], 11, 0),
    ]


CANARY_MINUTES = {16, 22, 46, 52}
AUG10_START_MS = 1786323600000  # 2026-08-10T01:00:00Z
AUG10_END_MS = 1786341600000    # 2026-08-10T06:00:00Z


def annotate(rows):
    """Rule-based annotations. Each rule is a SIGNATURE, not a verified identity;
    README.md states the evidence level of each."""
    ann = {}
    for x in rows:
        i, ts = int(x["id"]), int(x["timestamp_ms"])
        canary = (x["caller"] == "embed.embedQuery" and x["tokens_in"] == "17"
                  and utc(ts).minute in CANARY_MINUTES)
        aug10 = (x["phase"] == "query" and AUG10_START_MS <= ts < AUG10_END_MS and not canary)
        ann[i] = {"smoke_test": int(i in SMOKE_TEST_IDS), "canary_signature": int(canary),
                  "aug10_burst_window": int(aug10)}
    return ann


def gaps(rows, top=5):
    ts = sorted(int(x["timestamp_ms"]) for x in rows)
    g = sorted(((b - a) / 60000, utc(a).isoformat(), utc(b).isoformat())
               for a, b in zip(ts, ts[1:]))[::-1][:top]
    return [{"minutes": round(m, 1), "from": f, "to": t} for m, f, t in g]


def privacy_scan(paths):
    findings = []
    for p in paths:
        text = Path(p).read_text(errors="replace")
        for name, rx in PRIVACY_PATTERNS.items():
            for m in rx.finditer(text):
                findings.append((str(p), name, m.group(0)[:40]))
        low = text.lower()
        for w in DENY_WORDS:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                findings.append((str(p), "deny_word", w))
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deposit", required=True)
    a = ap.parse_args()
    dep = Path(a.deposit)
    pay = dep / "payload"
    src = pay / "provider_telemetry_2026-08-07_2026-09-08.csv"
    header, rows = load(src)
    errs = validate(header, rows)
    r_all = recompute(rows)
    r_prod = recompute([x for x in rows if int(x["id"]) not in SMOKE_TEST_IDS])
    cl = []
    bad_claims = 0
    for label, got, asserted, nd in claims(r_all):
        ok = got is not None and round(got, nd) == round(asserted, nd)
        bad_claims += (not ok)
        cl.append({"claim": label, "asserted_in_email": asserted, "recomputed": got,
                   "compared_at_digits": nd, "match": ok})
    # Derived summaries (data files of the deposit)
    with open(pay / "phase_summary.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["phase", "calls", "pct_calls", "tokens_in", "tokens_out", "cost_estimate_usd",
                    "pct_cost", "usd_per_call", "usd_per_1k_input_tokens", "days_with_activity"])
        for k, p in r_all["phases"].items():
            w.writerow([k, p["ops"], f"{p['pct_ops']:.4f}", p["tokens_in"], p["tokens_out"],
                        repr(p["usd"]), f"{p['pct_usd']:.4f}", repr(p["usd_per_op"]),
                        repr(p["usd_per_1k_input_tokens"]), p["days_with_activity"]])
    daily = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, []]))
    for x in rows:
        d = utc(int(x["timestamp_ms"])).date().isoformat()
        c = daily[d][x["phase"]]
        c[0] += 1; c[1] += int(x["tokens_in"]); c[2] += int(x["tokens_out"])
        c[3].append(float(x["cost_estimate_usd"]))
    with open(pay / "daily_phase_summary.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date_utc", "phase", "calls", "tokens_in", "tokens_out", "cost_estimate_usd"])
        for d in sorted(daily):
            for ph in ("construction", "maintenance", "query"):
                if ph in daily[d]:
                    c = daily[d][ph]
                    w.writerow([d, ph, c[0], c[1], c[2], repr(math.fsum(c[3]))])
    ann = annotate(rows)
    with open(pay / "row_annotations.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "smoke_test", "canary_signature", "aug10_burst_window"])
        for i in sorted(ann):
            a_ = ann[i]
            w.writerow([i, a_["smoke_test"], a_["canary_signature"], a_["aug10_burst_window"]])
    clean = [x for x in rows if not any(ann[int(x["id"])].values())]
    r_clean = recompute(clean)
    ann_counts = {k: sum(v[k] for v in ann.values()) for k in ("smoke_test", "canary_signature", "aug10_burst_window")}
    canary_pre_post = Counter(("before" if int(x["timestamp_ms"]) < 1788220800000 else "from")
                              + "_2026-09-01_minutes_" + ("22_52" if utc(int(x["timestamp_ms"])).minute in (22, 52) else "16_46")
                              for x in rows if ann[int(x["id"])]["canary_signature"])
    hour2 = Counter(utc(int(x["timestamp_ms"])).date().isoformat() for x in rows
                    if x["phase"] == "query" and utc(int(x["timestamp_ms"])).hour == 2
                    and not any(ann[int(x["id"])].values()))
    report = {
        "input": str(src.relative_to(dep)),
        "input_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "schema_window_errors": errs,
        "recomputed_all_rows": r_all,
        "recomputed_excluding_smoke_test_ids_1_4": {
            "n_rows": r_prod["n_rows"], "total_usd": r_prod["total_usd"],
            "phases": {k: {kk: v[kk] for kk in ("ops", "pct_ops", "usd", "pct_usd")}
                       for k, v in r_prod["phases"].items()}},
        "email_claims": cl,
        "annotation_counts": ann_counts,
        "canary_signature_by_period": dict(canary_pre_post),
        "query_rows_hour02utc_unannotated_by_day": dict(sorted(hour2.items())),
        "largest_gaps_between_consecutive_rows": gaps(rows),
        "recomputed_excluding_all_annotated_rows": {
            "n_rows": r_clean["n_rows"], "total_usd": r_clean["total_usd"],
            "days_with_data": r_clean["days_with_data"],
            "queries_per_day": r_clean["queries_per_day"],
            "phases": {k: {kk: v[kk] for kk in ("ops", "pct_ops", "usd", "pct_usd")}
                       for k, v in r_clean["phases"].items()}},
    }
    # Scan exactly what would be uploaded (payload/) plus the metadata draft.
    deposit_files = sorted(p for p in pay.rglob("*") if p.is_file())
    if (dep / "zenodo-metadata.json").exists():
        deposit_files.append(dep / "zenodo-metadata.json")
    pf = privacy_scan(deposit_files)
    report["privacy_scan"] = {"files_scanned": [str(p.relative_to(dep)) for p in deposit_files],
                              "patterns": sorted(PRIVACY_PATTERNS), "deny_words": DENY_WORDS,
                              "findings": pf}
    (dep / "_audit").mkdir(exist_ok=True)
    (dep / "_audit" / "recompute-and-scan.json").write_text(
        json.dumps(report, indent=2, default=sorted, ensure_ascii=False) + "\n")
    print(f"rows={len(rows)} schema/window errors={len(errs)} claim mismatches={bad_claims} "
          f"privacy findings={len(pf)}")
    for c in cl:
        if not c["match"]:
            print("  MISMATCH:", c)
    for f_ in pf:
        print("  PRIVACY:", f_)
    sys.exit(1 if (errs or bad_claims or pf) else 0)


if __name__ == "__main__":
    main()
