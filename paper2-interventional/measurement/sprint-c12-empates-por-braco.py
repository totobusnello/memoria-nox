#!/usr/bin/env python3
"""C12 (Paper B rc4): exact ties per arm in the four-vote sensitivity set.

Paper B §4 and §7 say the exact-tie rule (n/2 failures -> `not_failure`) binds in the
four-vote set and that "its effect on the treatment-control contrast depends on the arms
the ties fall in, which we have not counted". This script counts them.

COMPOSITION, NOT REIMPLEMENTATION. Every rule is imported:
  carregar_verdicts (dedupe per panelist, floor of 3 substantive, strict majority,
  tie -> not_failure), carregar_episodios, epoch_de, TAU, NIVEIS  <- pilot_replay.py
  arm per epoch                                                <- ASSIGNMENT-SERVING.json
  opportunity / HT weight / washout / window                   <- estimador_itt.py, run as is
The only new code is the tie census (which episodes have an even number of substantive
verdicts with exactly half at level >= TAU) and the tally per arm.

The four-vote set is the primary three-family file followed by the DeepSeek file
(DEVIATIONS-FOR-PAPER.md §10.31: "o conjunto de 4 votos fica publicado como
sensibilidade declarada"). DeepSeek is a different panelist, so the per-panelist dedupe
of carregar_verdicts makes the order irrelevant.

Controls, each of which aborts the script if it fails:
  1. sha256 of every input against MANIFESTO-LASTRO-P2.json (estrato-b-ids is not in the
     manifest; control 2 covers it);
  2. estimador_itt.py on the primary file reproduces ITT-2026-09-21.json per arm
     (opportunities, repeats, unknown) exactly;
  3. DEVIATIONS §10.31(6) "gains 20, losses 28" is reproduced: 20 episodes the fourth
     family brings to the floor of three substantive verdicts, 28 it brings to an exact
     tie; every failure -> not_failure change is one of the ties;
  4. reported, gating only when condition (i) is unchanged: the change in `repeats` per
     arm between estimador_itt.py on the two files equals rescued failures minus
     label-changing ties among opportunities (HT-weighted);
  5. reported: whether resolving the label-changing ties as failure would move any
     signature's first failure (condition (i)).

Usage:
  python3 sprint-c12-empates-por-braco.py \
      --lastro <dir with MANIFESTO-LASTRO-P2.json, episodios, estrato-b-ids, ITT json> \
      --verdicts-dir <dir with the two ensaio-20260921-*.jsonl> \
      --out ../out/C12-EMPATES-POR-BRACO-2026-10-05.json
Writes only --out (and a temp dir that it deletes). No absolute path is written to --out.

Option added 2026-10-05 (CHECK-A-rc4-B-rc4.md, D-B1):
  --empates-como-failure-out PATH  also resolve every exact tie of the four-vote set the
      OPPOSITE way (tie -> failure) and run estimador_itt.py on that, so the H1c point is
      measured with the condition-(i) feedback, not approximated. The opposite rule is
      obtained through the imported carregar_verdicts, not reimplemented: one synthetic
      `failure` vote at level TAU from a synthetic panelist is appended to each tied
      episode, which turns n/2 of n into n/2+1 of n+1 (a strict majority) and touches no
      other episode (checked). The whole --out object plus that block goes to PATH, a NEW
      file; --out itself stays byte-identical to the run without the option.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from pilot_replay import (  # noqa: E402
    carregar_verdicts, carregar_episodios, NIVEIS, TAU, EPOCH_H, WASHOUT_H,
)

PRIM = "ensaio-20260921-PRIMARIO-3fam.jsonl"
SENS = "ensaio-20260921-SENSIB-deepseek.jsonl"
EPIS = "episodios-ensaio-20260921.jsonl"
BIDS = "estrato-b-ids-20260921.txt"
ITT = "ITT-2026-09-21.json"
JANELA_INI, JANELA_FIM = "2026-09-01", "2026-09-20"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def votos_substantivos(paths: list[Path]) -> dict[str, dict[str, int]]:
    """Same filter and dedupe as carregar_verdicts (first record per (episode, panelist))."""
    por_ep: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for p in paths:
        for linha in p.read_text().splitlines():
            if not linha.strip():
                continue
            r = json.loads(linha)
            if r.get("status") != "ok" or r.get("verdict") == "abstain":
                continue
            nivel = r.get("level")
            if nivel in NIVEIS:
                por_ep[r["episode_id"]].setdefault(r.get("panelist"), NIVEIS.index(nivel))
    return por_ep


def roda_estimador(eps: Path, verd: Path, bids: Path, out: Path) -> dict:
    subprocess.run(
        [sys.executable, str(RAIZ / "estimador_itt.py"), "--episodes", str(eps),
         "--verdicts", str(verd), "--estrato-b-ids", str(bids), "--boot", "1",
         "--seed", "20260921", "--out", str(out)],
        check=True, stdout=subprocess.DEVNULL)
    return json.loads(out.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lastro", required=True, type=Path)
    ap.add_argument("--verdicts-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--empates-como-failure-out", type=Path, default=None)
    a = ap.parse_args()

    # ---- control 1: hashes against the manifest
    man = json.loads((a.lastro / "MANIFESTO-LASTRO-P2.json").read_text())
    esperado = {x["nome"]: x["sha256"] for x in man["artefatos"]}
    entradas = {
        PRIM: a.verdicts_dir / PRIM, SENS: a.verdicts_dir / SENS, EPIS: a.lastro / EPIS,
        ITT: a.lastro / ITT, "ASSIGNMENT-SERVING.json": RAIZ / "ASSIGNMENT-SERVING.json",
        "estimador_itt.py": RAIZ / "estimador_itt.py", "pilot_replay.py": RAIZ / "pilot_replay.py",
    }
    hashes = {}
    for nome, p in entradas.items():
        h = sha(p)
        if h != esperado[nome]:
            sys.exit(f"ABORT control 1: {nome} sha256 {h[:12]} != manifest {esperado[nome][:12]}")
        hashes[nome] = h
    hashes[BIDS] = sha(a.lastro / BIDS)

    arm = {e["epoch_inicio"]: e["arm"] for e in
           json.loads(entradas["ASSIGNMENT-SERVING.json"].read_text())["epochs"]}
    corte = NIVEIS.index(TAU)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        quatro = td / "quatro-votos.jsonl"
        quatro.write_text(entradas[PRIM].read_text() + entradas[SENS].read_text())

        # ---- control 2: the primary ITT is reproduced
        itt3 = roda_estimador(entradas[EPIS], entradas[PRIM], a.lastro / BIDS, td / "itt3.json")
        itt_art = json.loads(entradas[ITT].read_text())
        for b in ("treatment", "control"):
            for k in ("oportunidades", "repeats", "unknown_no_denominador", "n_epochs"):
                x, y = itt3["primario"]["por_braco"][b][k], itt_art["primario"]["por_braco"][b][k]
                if x != y:
                    sys.exit(f"ABORT control 2: {b}.{k} {x} != artifact {y}")
        itt4 = roda_estimador(entradas[EPIS], quatro, a.lastro / BIDS, td / "itt4.json")

    v3 = carregar_verdicts(entradas[PRIM])
    votos4 = votos_substantivos([entradas[PRIM], entradas[SENS]])
    # the imported rule on the same concatenation the estimator read
    with tempfile.TemporaryDirectory() as td:
        q = Path(td) / "q.jsonl"
        q.write_text(entradas[PRIM].read_text() + entradas[SENS].read_text())
        v4 = carregar_verdicts(q)

    # tie census in the four-vote set (only adjudicated episodes, >= 3 substantive)
    empate = {ep for ep, pp in votos4.items()
              if len(pp) >= 3 and len(pp) % 2 == 0
              and 2 * sum(1 for x in pp.values() if x >= corte) == len(pp)}
    for ep in empate:
        assert v4.get(ep) == "not_failure", ep  # the imported rule must resolve ties so

    # ---- control 3: DEVIATIONS §10.31(6), "ganhos 20 · perdas 28 · saldo −8".
    # Measured here: "ganhos" are the episodes the fourth family brings to the floor of
    # three substantive verdicts (unknown -> adjudicated), "perdas" are the episodes it
    # brings to an exact tie. Neither is a change of label; the label changes are counted
    # separately (failure -> not_failure among the ties; gains to failure among rescues).
    resgates = {ep for ep in v4 if ep not in v3}
    empates_em_ambos = {ep for ep in empate if ep in v3}
    if (len(resgates), len(empate)) != (20, 28) or empate != empates_em_ambos:
        sys.exit(f"ABORT control 3: rescues/ties {len(resgates)}/{len(empate)} != 20/28")
    perdas = {ep for ep in empate if v3[ep] == "failure"}          # tie flips the label
    ganhos = {ep for ep in resgates if v4[ep] == "failure"}       # rescue adds a failure
    if {ep for ep, s in v3.items() if s == "failure" and v4[ep] != "failure"} != perdas:
        sys.exit("ABORT control 3: a failure -> not_failure change that is not a tie")

    # ---- per-arm census, with the estimator's own opportunity rule
    eps = carregar_episodios(entradas[EPIS], v4)
    b_ids = {l.strip() for l in (a.lastro / BIDS).read_text().splitlines() if l.strip()}
    peso_b = len([e for e in eps if not e.err]) / len(b_ids)
    eps3 = carregar_episodios(entradas[EPIS], v3)
    primeiro3: dict[str, object] = {}
    for e in eps3:
        if e.estado == "failure" and e.sig not in primeiro3:
            primeiro3[e.sig] = e.epoch
    primeiro4: dict[str, object] = {}
    for e in eps:
        if e.estado == "failure" and e.sig not in primeiro4:
            primeiro4[e.sig] = e.epoch
    limiar = timedelta(hours=EPOCH_H)
    # the tie rule's reach into condition (i): resolve the label-changing ties as failure
    # instead and compare the first-failure epoch per signature
    v4_sem_regra = dict(v4)
    for ep in perdas:
        v4_sem_regra[ep] = "failure"
    primeiro_sem_regra: dict[str, object] = {}
    for e in carregar_episodios(entradas[EPIS], v4_sem_regra):
        if e.estado == "failure" and e.sig not in primeiro_sem_regra:
            primeiro_sem_regra[e.sig] = e.epoch
    sigs_cond_i_pela_regra = sorted(s for s in set(primeiro4) | set(primeiro_sem_regra)
                                    if primeiro4.get(s) != primeiro_sem_regra.get(s))

    def oportunidade(e, primeiro) -> float:
        if e.offset_h < WASHOUT_H:
            return 0.0
        t0 = primeiro.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            return 0.0
        if e.err:
            return 1.0
        return peso_b if e.id in b_ids else 0.0

    zero = lambda: dict(empates=0, empates_que_mudam_rotulo=0, resgates=0,  # noqa: E731
                        empates_oportunidade=0, empates_oportunidade_peso=0.0,
                        perdas_oportunidade=0, perdas_oportunidade_peso=0.0,
                        ganhos_oportunidade=0, ganhos_oportunidade_peso=0.0,
                        episodios_adjudicados_4v=0)
    por_braco = {"treatment": zero(), "control": zero()}
    fora_da_janela = collections.Counter()
    for e in eps:
        k = e.epoch.strftime("%Y-%m-%d")
        if not (JANELA_INI <= k <= JANELA_FIM) or k not in arm:
            if e.id in empate:
                fora_da_janela["empates"] += 1
            continue
        d = por_braco[arm[k]]
        if e.id in v4:
            d["episodios_adjudicados_4v"] += 1
        w4 = oportunidade(e, primeiro4)
        if e.id in empate:
            d["empates"] += 1
            d["empates_que_mudam_rotulo"] += e.id in perdas
            if w4:
                d["empates_oportunidade"] += 1
                d["empates_oportunidade_peso"] += w4
        d["resgates"] += e.id in resgates
        if e.id in perdas and w4:
            d["perdas_oportunidade"] += 1
            d["perdas_oportunidade_peso"] += w4
        if e.id in ganhos and w4:
            d["ganhos_oportunidade"] += 1
            d["ganhos_oportunidade_peso"] += w4
    for d in por_braco.values():
        for k in list(d):
            if isinstance(d[k], float):
                d[k] = round(d[k], 3)

    # ---- control 4: tie losses and gains account for the change in repeats, per arm,
    # where condition (i) did not move (checked: same first-failure epoch per signature)
    mesma_cond_i = all(primeiro3.get(s) == primeiro4.get(s) for s in set(primeiro3) | set(primeiro4))
    c4 = {}
    for b in ("treatment", "control"):
        r3 = itt3["primario"]["por_braco"][b]["repeats"]
        r4 = itt4["primario"]["por_braco"][b]["repeats"]
        prev = por_braco[b]["ganhos_oportunidade_peso"] - por_braco[b]["perdas_oportunidade_peso"]
        c4[b] = dict(repeats_3fam=r3, repeats_4votos=r4, delta=round(r4 - r3, 2),
                     ganhos_menos_perdas_peso=round(prev, 2))
        if mesma_cond_i and abs((r4 - r3) - prev) > 0.02:
            sys.exit(f"ABORT control 4: {b} delta repeats {r4 - r3:.2f} != gains-losses {prev:.2f}")

    def h1c(itt, b):
        return itt["primario"]["por_braco"][b]["H1c_prop"]

    saida = dict(
        gerado_em="2026-10-05",
        objeto="C12 do Paper B rc4: empates exatos por braco no conjunto de quatro votos",
        regra="carregar_verdicts (pilot_replay.py): piso 3 substantivos; maioria estrita; "
              "empate (n/2 falhas, n par) -> not_failure; falha = nivel >= TAU",
        tau=TAU,
        conjunto_quatro_votos=f"{PRIM} + {SENS} (DEVIATIONS §10.31)",
        entradas_sha256=hashes,
        controles=dict(
            c1_manifesto="ok (estrato-b-ids fora do manifesto; coberto por c2)",
            c2_itt_primario_reproduzido="ok: oportunidades, repeats, unknown, n_epochs por braco",
            c3_deviations_10_31=dict(
                resgates_ganhos=len(resgates), empates_perdas=len(empate),
                nota="reproduz 'ganhos 20 · perdas 28' de DEVIATIONS §10.31(6): resgates ao piso "
                     "de 3 e empates exatos; nenhum dos dois e mudanca de rotulo",
                empates_que_mudam_rotulo_failure_para_not_failure=len(perdas),
                empates_ja_not_failure_com_3_familias=len(empate) - len(perdas),
                resgates_que_entram_como_failure=len(ganhos)),
            c4_repeats=dict(condicao_i_inalterada=mesma_cond_i, por_braco=c4),
            c5_regra_de_empate_na_condicao_i=dict(
                assinaturas_cujo_primeiro_failure_muda=len(sigs_cond_i_pela_regra),
                nota="resolver os empates que mudam rotulo como failure nao altera a condicao (i)"
                     if not sigs_cond_i_pela_regra else "a regra altera a condicao (i)"),
        ),
        empates_total_conjunto_4v=len(empate),
        empates_fora_da_janela=fora_da_janela["empates"],
        peso_estrato_b=round(peso_b, 4),
        por_braco=por_braco,
        h1c_ponto=dict(
            tres_familias={b: h1c(itt3, b) for b in ("treatment", "control")},
            quatro_votos={b: h1c(itt4, b) for b in ("treatment", "control")},
            diferenca_3fam=round(h1c(itt3, "treatment") - h1c(itt3, "control"), 6),
            diferenca_4votos=round(h1c(itt4, "treatment") - h1c(itt4, "control"), 6),
            nota="ponto apenas (estimador_itt.py com --boot 1); sem intervalo; nao e resultado do paper",
        ),
    )
    a.out.write_text(json.dumps(saida, indent=2, ensure_ascii=False, sort_keys=False) + "\n")
    print(json.dumps(saida, indent=2, ensure_ascii=False))

    if a.empates_como_failure_out is not None:
        # opposite tie resolution, through the imported rule (see the docstring)
        sint = "".join(json.dumps({"episode_id": ep, "panelist": "__empate_como_failure__",
                                   "status": "ok", "verdict": "failure", "level": TAU}) + "\n"
                       for ep in sorted(empate))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            qf = td / "quatro-votos-empate-failure.jsonl"
            qf.write_text(entradas[PRIM].read_text() + entradas[SENS].read_text() + sint)
            v4f = carregar_verdicts(qf)
            if any(v4f.get(ep) != "failure" for ep in empate):
                sys.exit("ABORT D-B1: a tie did not resolve to failure")
            if {ep: s for ep, s in v4f.items() if ep not in empate} != \
                    {ep: s for ep, s in v4.items() if ep not in empate}:
                sys.exit("ABORT D-B1: a non-tied label changed")
            itt4f = roda_estimador(entradas[EPIS], qf, a.lastro / BIDS, td / "itt4f.json")
        # first order: add each arm's tied-opportunity HT weight to its repeats, same denominator
        ordem1 = {}
        for b in ("treatment", "control"):
            pb = itt4["primario"]["por_braco"][b]
            opp, rep = pb["oportunidades"], pb["repeats"]
            ordem1[b] = round((rep + por_braco[b]["empates_oportunidade_peso"]) / opp, 6)
        def pb(itt, b, k):
            return itt["primario"]["por_braco"][b][k]
        saida["contrafactual_empate_como_failure"] = dict(
            regra="empate exato (n/2 de n) -> failure, so neste bloco; o resto do arquivo usa a regra do paper",
            empates_resolvidos=len(empate),
            por_braco={b: dict(oportunidades=pb(itt4f, b, "oportunidades"),
                               repeats=pb(itt4f, b, "repeats"),
                               H1c_prop=pb(itt4f, b, "H1c_prop"))
                       for b in ("treatment", "control")},
            diferenca_4votos_regra_do_paper=round(h1c(itt4, "treatment") - h1c(itt4, "control"), 6),
            diferenca_4votos_empate_como_failure=round(h1c(itt4f, "treatment") - h1c(itt4f, "control"), 6),
            primeira_ordem=dict(por_braco=ordem1,
                                diferenca=round(ordem1["treatment"] - ordem1["control"], 6),
                                nota="repeats + peso HT dos empates-oportunidade, oportunidades fixas; "
                                     "ignora a realimentacao da condicao (i)"),
            nota="ponto apenas (estimador_itt.py com --boot 1); sem intervalo; nao e resultado do paper",
        )
        a.empates_como_failure_out.write_text(
            json.dumps(saida, indent=2, ensure_ascii=False, sort_keys=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
