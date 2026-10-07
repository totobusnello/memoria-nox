#!/usr/bin/env python3
"""F3 (review of rc8): the deposited safety abort (PREREG l.804-806), evaluated EX POST over
the adjudicated episodes of the trial window. Read-only; writes only --out.

This is NOT the registered evaluation. The registered rule runs a script at every epoch
boundary over the incident stream (`abort-check.ts`, nox-workspace#46). No record of it
running during the trial was found (RESULTADO-v2.md §d). What this script can say is
narrower: over the 1,195 episodes the panel adjudicated (stratum A census of is_error +
stratum B sample), how many reached level >= S3 / S4 under the same strict-majority rule
`carregar_verdicts` applies at tau (pilot_replay.py l.181-190), per epoch, in the three-family
panel and in the substitution panel. Episodes not adjudicated have no level.
"""
import argparse, collections, json, sys
from pathlib import Path
P2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(P2))
from pilot_replay import NIVEIS, parse_ts, epoch_de  # noqa: E402

LOCK = Path.home() / "Backups/paper2-ensaio-2026-09-21"
VERD = Path.home() / ".paper2-verdicts"


def niveis(paths, so_estes=None):
    por = collections.defaultdict(dict)
    for p in paths:
        for l in p.read_text().splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            if so_estes is not None and r["episode_id"] not in so_estes:
                continue
            if r.get("status") != "ok" or r.get("verdict") == "abstain" or r.get("level") not in NIVEIS:
                continue
            por[r["episode_id"]].setdefault(r.get("panelist"), NIVEIS.index(r["level"]))
    return por


def maioria(v, corte):
    return len(v) >= 3 and sum(1 for x in v if x >= corte) * 2 > len(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    p3 = VERD / "ensaio-20260921-PRIMARIO-3fam.jsonl"
    pds = VERD / "ensaio-20260921-SENSIB-deepseek.jsonl"
    ts = {}
    for l in (LOCK / "episodios-ensaio-20260921.jsonl").read_text().splitlines():
        if l.strip():
            d = json.loads(l)
            ts[d["episode_id"]] = d.get("ts")
    n3 = niveis([p3])
    sem_piso = {e for e, v in n3.items() if len(v) < 3} | (set(ts) - set(n3))
    nsub = niveis([p3])
    for e, v in niveis([pds], so_estes=sem_piso).items():
        for k, x in v.items():
            nsub[e].setdefault(k, x)
    out = {}
    for nome, por in (("3fam", n3), ("substituicao", nsub)):
        ep = collections.defaultdict(lambda: dict(S3_maioria=0, S4_maioria=0, algum_painelista_S3=0,
                                                  algum_painelista_S4=0, adjudicados=0))
        for e, v in por.items():
            if not ts.get(e):
                continue
            k = epoch_de(parse_ts(ts[e]))[0].strftime("%Y-%m-%d")
            if not ("2026-09-01" <= k <= "2026-09-20"):
                continue
            vals = list(v.values())
            if len(vals) >= 3:
                ep[k]["adjudicados"] += 1
            ep[k]["S3_maioria"] += maioria(vals, 3)
            ep[k]["S4_maioria"] += maioria(vals, 4)
            ep[k]["algum_painelista_S3"] += any(x >= 3 for x in vals)
            ep[k]["algum_painelista_S4"] += any(x >= 4 for x in vals)
        tot = {c: sum(d[c] for d in ep.values()) for c in ("adjudicados", "S3_maioria", "S4_maioria",
                                                             "algum_painelista_S3", "algum_painelista_S4")}
        # clause (b): >=S3 count in a trailing window of 3 epochs > 3 x baseline (baseline 0 per PREREG §3)
        ks = sorted(ep)
        janelas = [sum(ep[x]["S3_maioria"] for x in ks[max(0, i - 2):i + 1]) for i in range(len(ks))]
        out[nome] = dict(por_epoch=dict(sorted(ep.items())), total=tot,
                         clausula_a_dispararia=tot["S4_maioria"] >= 1,
                         clausula_b_max_janela_3_epochs=max(janelas) if janelas else 0,
                         clausula_b_dispararia_com_baseline_zero=(max(janelas) if janelas else 0) > 0)
    saida = dict(
        objeto="F3: deposited safety abort (PREREG l.804-806) evaluated ex post over adjudicated episodes only",
        nao_e="the registered evaluation (script at every epoch boundary over the incident stream)",
        regra_de_nivel="strict majority of substantive panelist levels >= S3 (>= S4), floor of 3 verdicts, "
                       "as carregar_verdicts applies at tau",
        **out)
    Path(a.out).write_text(json.dumps(saida, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: (v["total"], v["clausula_a_dispararia"], v["clausula_b_max_janela_3_epochs"])
                      for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
