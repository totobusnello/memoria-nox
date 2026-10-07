#!/usr/bin/env python3
"""F4 (review of rc8): the Epoch-1 stopping rule of PROSPECTIVE-ESTIMAND §3-bis under the set of
signatures the dose can promote at w = 4, the dose Epoch 1 was served at.

The planning artifact (out/CONCENTRATION-2026-08-30.json) lists seven signatures promotable at
w = 2, and concentracao-de-oportunidades.py takes that list as input (--promovidas). Its
derivation was not saved as a script. This one re-derives it from the dose artifact that the
same script reads for its denominator (out/dose-350-v3.json, the 350-state calibration replay):
a signature is promotable at w iff the designated item of its group (DESIGNATION-2026-08-26.json)
enters the served brief (`would_enter`) in at least one of the 350 states at that w. GUARD: at
w = 2 this must give back the artifact's seven signatures exactly (exit 2 otherwise).

Then, with the definitions of concentracao-de-oportunidades.py (an action is an opportunity if
its sig_primary had an is_error episode EARLIER in the corpus; covered if the signature is
promotable) and of checks-rc8.py block D (Epoch 1 = 2026-09-01 09:00Z + 24 h; the three
readings; the trial's weighted rule through estimador_itt_registrado.por_epoch), it computes:
  - planning-corpus coverage at w = 4 from the artifact's per-signature opportunity totals
    (the 1,843-episode live archive is not available; the per-signature totals are);
  - Epoch-1 coverage at w = 4, with the Wilson 95% interval (descriptive only).
Read-only on every input; writes only --out.
"""
import argparse, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

P2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(P2)); sys.path.insert(0, str(P2 / "measurement"))
import estimador_itt_registrado as R  # noqa: E402
from pilot_replay import carregar_verdicts, carregar_episodios, WASHOUT_H, EPOCH_H, parse_ts  # noqa: E402
import tempfile  # noqa: E402

DOSE = P2 / "out" / "dose-350-v3.json"
CONC = P2 / "out" / "CONCENTRATION-2026-08-30.json"
DESIG = P2 / "DESIGNATION-2026-08-26.json"
LIMIAR = 0.367


def wilson(c, n, z=1.959964):
    if not n:
        return None
    ph = c / n; den = 1 + z * z / n
    mid = (ph + z * z / (2 * n)) / den
    half = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(mid - half, 4), round(mid + half, 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    dose = json.loads(DOSE.read_text()); conc = json.loads(CONC.read_text())
    inv = {v: k for k, v in json.loads(DESIG.read_text())["designados"].items()}
    por_w = {}
    for r in dose["dose"]["detalhe"]:
        for i in r["would_enter"]:
            if i not in inv:
                sys.exit(f"ABORT would_enter id {i} is not a designated item")
            por_w.setdefault(r["w"], set()).add(inv[i])
    w2, w4 = por_w.get(2, set()), por_w.get(4, set())
    if sorted(w2) != sorted(conc["assinaturas_promovidas_sob_w2"]):
        print("ABORT derivation does not reproduce the artifact's w = 2 set", file=sys.stderr); return 2
    if not w2 <= w4:
        print("ABORT w = 2 set is not contained in the w = 4 set", file=sys.stderr); return 2
    # planning corpus, from the artifact's per-signature opportunity totals
    tot = conc["oportunidades"]
    cob = {w: sum(v["total"] for s, v in conc["por_assinatura"].items() if s in S) for w, S in (("2", w2), ("4", w4))}
    if cob["2"] != conc["oportunidades_cobertas"]:
        print("ABORT per-signature totals do not give back 611 at w = 2", file=sys.stderr); return 2
    # Epoch 1 under the planning rule
    P = {k: Path(v) for k, v in R.DEFAULTS.items()}
    eps = sorted((json.loads(l) for l in P["episodes"].read_text().splitlines() if l.strip()),
                 key=lambda e: e.get("ts", ""))
    ja, ops = set(), []
    for e in eps:
        if e.get("sig_primary") in ja:
            ops.append(e)
        if e.get("is_error"):
            ja.add(e.get("sig_primary"))
    jan = R.janelas_de_exposicao(P["serving"])
    ini = datetime(2026, 9, 1, 9, tzinfo=timezone.utc); fim = ini + timedelta(hours=EPOCH_H)
    active = jan["2026-09-01"][0]

    def em(e, t0, t1):
        t = parse_ts(e["ts"]); return t0 <= t < t1

    def cobertura(lista, S):
        n = len(lista); c = sum(1 for e in lista if e["sig_primary"] in S)
        return dict(oportunidades=n, cobertas=c, cobertura=round(c / n, 4) if n else None,
                    wilson95=wilson(c, n), abaixo_do_limiar=(c / n < LIMIAR) if n else None)
    leituras = {}
    for w, S in (("2", w2), ("4", w4)):
        leituras[w] = {
            "epoch_1_inteiro": cobertura([e for e in ops if em(e, ini, fim)], S),
            "epoch_1_pos_washout": cobertura([e for e in ops if em(e, ini + timedelta(hours=WASHOUT_H), fim)], S),
            "epoch_1_fase_active": cobertura([e for e in ops if em(e, active, fim)], S),
        }
    # the trial's weighted rule (registered window and panel), as checks-rc8 block D (b)
    with tempfile.TemporaryDirectory() as td:
        vs, _ = R.verdicts_substituicao(P["verdicts"], P["verdicts_ds"], Path(td))
    eps_s = carregar_episodios(P["episodes"], vs)
    b_ids = {l.strip() for l in P["estrato_b"].read_text().splitlines() if l.strip()}
    base = R.predicado_janela("exposicao", jan)
    Qall = R.por_epoch(eps_s, b_ids, base)
    ep1 = [x for x in Qall["dentro"] if x.strftime("%Y-%m-%d") == "2026-09-01"][0]
    for w, S in (("2", w2), ("4", w4)):
        Qc = R.por_epoch(eps_s, b_ids, lambda e, S=S: base(e) and e.sig in S)
        o, c = Qall["oport"][ep1], Qc["oport"][ep1]
        leituras[w]["ponderada_regra_do_ensaio"] = dict(oportunidades_ponderadas=round(o, 3),
                                                       cobertas_ponderadas=round(c, 3),
                                                       cobertura=round(c / o, 4) if o else None,
                                                       abaixo_do_limiar=(c / o < LIMIAR) if o else None)
    if leituras["2"]["epoch_1_inteiro"]["cobertura"] != 0.3237:
        print("ABORT w = 2 Epoch-1 reading does not reproduce checks-rc8 block D (0.3237)", file=sys.stderr); return 2
    saida = dict(
        objeto="F4: Epoch-1 stopping rule (PROSPECTIVE-ESTIMAND §3-bis, threshold 36.7%) under the w = 4 promotable set",
        derivacao="signature promotable at w iff its designated item is in would_enter in >= 1 of the 350 states "
                  "of out/dose-350-v3.json at that w; reproduces the CONCENTRATION w = 2 list exactly",
        limiar=LIMIAR,
        promoviveis={k: sorted(v) for k, v in sorted(por_w.items(), key=lambda kv: float(kv[0]))},
        n_promoviveis={str(k): len(v) for k, v in sorted(por_w.items(), key=lambda kv: float(kv[0]))},
        acrescentadas_em_w4=sorted(w4 - w2),
        corpus_de_planejamento=dict(oportunidades=tot, cobertas_w2=cob["2"], cobertas_w4=cob["4"],
                                    cobertura_w2=round(cob["2"] / tot, 4), cobertura_w4=round(cob["4"] / tot, 4),
                                    por_assinatura_acrescentada={s: conc["por_assinatura"].get(s, {}).get("total", 0)
                                                                 for s in sorted(w4 - w2)}),
        epoch_1=leituras,
    )
    Path(a.out).write_text(json.dumps(saida, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(dict(n=saida["n_promoviveis"], add=saida["acrescentadas_em_w4"],
                          plan=saida["corpus_de_planejamento"], ep1=leituras), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
