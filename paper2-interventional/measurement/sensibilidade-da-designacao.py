#!/usr/bin/env python3
"""
sensibilidade-da-designacao.py — o teto de 17/350 depende de QUAIS chunks foram designados?

A regra de designação (opção B, `DECISION-designacao-2026-08-25.md`) escolhe **um chunk
por grupo de assinatura** por `argmin SHA256(seed ‖ "|" ‖ chunk_id)`. A escolha dentro do
grupo é, por construção, **arbitrária** — é sorteio. A pergunta que isso levanta e que o
paper ainda não respondeu:

> o teto de alcançabilidade de 17/350 é propriedade do comparador, ou é acidente de
> **qual** dos chunks de cada grupo o sorteio pegou?

Se o teto balança muito entre seeds, o `4,86%` do §5.7 é um ponto amostral disfarçado de
constante, e o paper tem de reportar a dispersão em vez do ponto. Se não balança, o
número é robusto à arbitrariedade e o §5.7 fica mais forte.

⚠️ **Seeds não podem ser escolhidas à mão.** A `randomness` do beacon original já é
pública, então eu poderia computar offline o resultado de vários rótulos e reportar o que
me favorece — é a mesma pescaria que a rota (a) do plano da designação existia para
impedir. Duas defesas aqui, e as duas importam:

1. a família de seeds é **derivada deterministicamente** de uma frase fixa escrita neste
   arquivo (`FRASE`), então um terceiro regenera exatamente as mesmas;
2. **todas** as seeds da família são reportadas. Nenhuma é descartada. Um resultado
   omitido reintroduz a pescaria por trás da porta.

⚠️ Esta é uma análise de sensibilidade sobre a arbitrariedade **dentro do grupo**. Ela
mantém fixa a população do estudo (os 55 chunks em 19 grupos, definidos pelo painel) e
varia só quem, dentro de cada grupo, recebe o bônus. Ela **não** responde se o teto
depende do painel ter definido essa população — essa é outra pergunta, e exige mexer em
`p2_verdict`, não na seed.

Uso:
  sensibilidade-da-designacao.py --verdicts verdicts.csv --k 8 --saida-dir designacoes/
onde verdicts.csv é `sig_primary,severity,chunk_id` sem cabeçalho, como sai de
  SELECT DISTINCT sig_primary, severity, chunk_id FROM p2_verdict;
"""
import argparse
import csv
import hashlib
import json
import os
import sys

# Frase fixa, escrita antes de qualquer rodada. Trocar isto invalida a análise:
# um terceiro que regenere com outra frase obtém outras seeds e outro resultado.
FRASE = "paper2|sensibilidade-da-designacao|2026-08-28"


def seed_da_familia(i: int) -> str:
    return hashlib.sha256(f"{FRASE}|{i}".encode("ascii")).hexdigest()


def chave(seed_hex: str, chunk_id: int) -> str:
    """Idêntica a `designation_verify.py:chave` — seed em hex ASCII, separador `|`,
    `sig_primary` FORA da chave (ver o cabeçalho daquele arquivo: há assinatura que
    contém o próprio separador, e incluí-la tornaria a chave ambígua)."""
    return hashlib.sha256(f"{seed_hex}|{chunk_id}".encode("ascii")).hexdigest()


def designados(seed_hex: str, linhas):
    por_grupo = {}
    for sig, cid in linhas:
        por_grupo.setdefault(sig, set()).add(cid)
    return {sig: min(cids, key=lambda c: chave(seed_hex, c))
            for sig, cids in sorted(por_grupo.items())}


def analisar(a):
    """Modo análise. Não gera nada — lê o que foi gerado e medido."""
    import glob
    if not a.publicado:
        raise SystemExit("--resultados exige --publicado (o run da designação real)")
    # ⚠️ O MANIFESTO tem de estar NO diretório dos resultados. A primeira versão deste
    # bloco caía num irmão (`../desig/MANIFESTO.json`) quando o local faltava — e num
    # teste de mutação isso fez o guarda da frase ler o manifesto CERTO e não morder.
    # Guarda que resolve para outro arquivo que não o fornecido é pior que guarda nenhum.
    mp = os.path.join(a.resultados, "MANIFESTO.json")
    if not os.path.exists(mp):
        raise SystemExit(f"falta {mp} — o manifesto tem de estar junto dos resultados, "
                         f"para que a frase conferida seja a que os gerou.")
    man = json.load(open(mp))
    if man["frase"] != FRASE:
        raise SystemExit(
            f"MANIFESTO gerado com outra frase ({man['frase']!r}) — as seeds não são as "
            f"desta versão do script e a distribuição não é reprodutível.")
    porsha = {m["sha256"]: m for m in man["designacoes"]}

    pub = json.load(open(a.publicado))
    t = pub["dose"]["tabela"][0]
    base = {"rotulo": "publicada", "mexeu": t["mexeu"], "churn": t["churn_total"],
            "estados": pub["dose"]["estados"],
            "designacao_sha256": pub["procedencia"]["designacao_sha256"]}
    estados_pub = {x["ts"] for x in pub["dose"]["detalhe"]
                   if not x.get("erro") and (x.get("churn") or 0) > 0}

    linhas, invar = [base], []
    for p in sorted(glob.glob(os.path.join(a.resultados, "sens-*.json"))):
        d = json.load(open(p))
        pr, tt = d["procedencia"], d["dose"]["tabela"][0]
        # ── guarda: cada rodada tem de ter usado a designação que diz ter usado ──
        m = porsha.get(pr["designacao_sha256"])
        if m is None:
            raise SystemExit(
                f"{os.path.basename(p)}: designacao_sha256 {pr['designacao_sha256'][:12]}… "
                f"não está no MANIFESTO. A rodada usou uma designação que este script não "
                f"gerou — a distribuição seria sobre outra coisa.")
        # ── guarda: nada além da designação pode ter mudado ──
        for k in ("corpus_sha256_primeiros_1MB", "corte_serve_state",
                  "fonte_brief_ts_sha256", "granularidade_last_served"):
            if pr.get(k) != pub["procedencia"].get(k):
                raise SystemExit(
                    f"{os.path.basename(p)}: {k} difere do run publicado "
                    f"({pr.get(k)} vs {pub['procedencia'].get(k)}). Mais de uma coisa mudou.")
        if d["dose"]["estados"] != base["estados"]:
            raise SystemExit(f"{os.path.basename(p)}: {d['dose']['estados']} estados, "
                             f"publicado tem {base['estados']}")
        est = {x["ts"] for x in d["dose"]["detalhe"]
               if not x.get("erro") and (x.get("churn") or 0) > 0}
        linhas.append({"rotulo": f"sens-{m['i']:02d}", "seed": m["seed"],
                       "mexeu": tt["mexeu"], "churn": tt["churn_total"],
                       "estados": d["dose"]["estados"],
                       "designacao_sha256": pr["designacao_sha256"],
                       "estados_em_comum_com_a_publicada": len(est & estados_pub)})

    # ── guarda: a simetria que faltava ─────────────────────────────────────
    # A checagem acima é resultado→manifesto: toda rodada tem de vir de uma designação
    # declarada. Ela NÃO impedia o inverso — gerar k=20, rodar replay só nas 8
    # convenientes e omitir as outras 12 passava ileso, e "todas as oito são
    # reportadas" seria verdade sobre as oito sem dizer que só oito existiram.
    # Apontado por revisão adversarial em 2026-08-29. O guarda agora exige
    # manifesto→resultado também: toda designação declarada precisa ter rodado.
    vistos = {l["designacao_sha256"] for l in linhas[1:]}
    faltando = [m for m in man["designacoes"] if m["sha256"] not in vistos]
    if faltando:
        raise SystemExit(
            "MANIFESTO declara %d designação(ões) sem resultado correspondente: %s. "
            "Reportar só as que rodaram é seleção pós-hoc com aparência de censo — ou "
            "rode todas, ou regenere o manifesto com o k que de fato foi usado."
            % (len(faltando), ", ".join(m["arquivo"] for m in faltando)))

    vs = [l["mexeu"] for l in linhas[1:]]
    vs_ord = sorted(vs)
    n = len(vs)
    med = (vs_ord[n // 2] if n % 2 else (vs_ord[n // 2 - 1] + vs_ord[n // 2]) / 2)
    todos = sorted(vs + [base["mexeu"]])
    saida = {
        "gerado_por": "measurement/sensibilidade-da-designacao.py --resultados",
        "frase_da_familia": FRASE,
        "pergunta": "o teto depende de QUAL chunk de cada grupo o sorteio pegou?",
        "estados_por_rodada": base["estados"],
        "publicada": base["mexeu"],
        "alternativas": vs,
        "min": min(todos), "max": max(todos), "mediana_das_alternativas": med,
        "media_das_alternativas": round(sum(vs) / n, 2),
        "posto_da_publicada": todos.index(base["mexeu"]) + 1,
        "de_quantas": len(todos),
        "publicada_e_o_minimo": base["mexeu"] == min(todos),
        # ⚠️ empatar no mínimo não é ser "a menor". Escrever "a menor das nove" quando
        # uma alternativa dá o mesmo valor é afirmar unicidade que o dado não tem.
        "alternativas_que_empatam_no_minimo": sum(1 for v in vs if v == min(todos)),
        "publicada_e_o_UNICO_minimo": base["mexeu"] == min(todos)
                                      and sum(1 for v in vs if v == min(todos)) == 0,
        "teto_pct": {l["rotulo"]: round(100 * l["mexeu"] / l["estados"], 2) for l in linhas},
        "linhas": linhas,
    }
    print(f"{'designação':<12}{'mexeu':>7}{'teto':>9}{'churn':>7}{'∩ pub':>7}")
    for l in linhas:
        print(f"{l['rotulo']:<12}{l['mexeu']:>7}{100*l['mexeu']/l['estados']:>8.2f}%"
              f"{l['churn']:>7}{l.get('estados_em_comum_com_a_publicada','—'):>7}")
    print(f"\n{n} alternativas: min={min(vs)} max={max(vs)} mediana={med} "
          f"média={saida['media_das_alternativas']}  |  publicada={base['mexeu']} "
          f"(posto {saida['posto_da_publicada']} de {saida['de_quantas']})")
    if saida["publicada_e_o_minimo"]:
        emp = saida["alternativas_que_empatam_no_minimo"]
        print(f"⚠️ a designação publicada está no MÍNIMO das {saida['de_quantas']}"
              + (f" (empatada com {emp} alternativa(s))" if emp else " (única)")
              + " — reportar o teto dela como 'o teto' descreve o extremo, não a regra.")
        print(f"   ⚠️ com {n} alternativas, P(posto 1) ≈ {1/(n+1):.0%} sob permutação: "
              f"isto NÃO estabelece que a publicada seja atípica.")
    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--saida-dir", required=True)
    ap.add_argument("--referencia", help="DESIGNATION real, para conferir que a "
                                         "derivação local reproduz a publicada")
    ap.add_argument("--resultados", metavar="DIR",
                    help="modo análise: lê sens-NN.json + o run da designação publicada "
                         "e emite a distribuição do teto. Exige --publicado.")
    ap.add_argument("--publicado", metavar="JSON",
                    help="artefato de dose da designação REAL (out/gran-seg.json)")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.resultados:
        return analisar(a)

    linhas = []
    with open(a.verdicts) as f:
        for r in csv.reader(f):
            if len(r) < 3 or not r[2].strip():
                continue
            linhas.append((r[0], int(r[2])))

    grupos = len({s for s, _ in linhas})
    chunks = len({c for _, c in linhas})
    print(f"população: {chunks} chunks em {grupos} grupos")

    # ── âncora: a derivação local tem de reproduzir a designação PUBLICADA ──
    # Sem isto, as designações alternativas poderiam vir de uma regra diferente da que
    # produziu o 17/350, e a comparação seria entre coisas incomparáveis.
    if a.referencia:
        ref = json.load(open(a.referencia))
        meu = designados(ref["seed"], linhas)
        if meu != ref["designados"]:
            dif = {k: (v, ref["designados"].get(k)) for k, v in meu.items()
                   if ref["designados"].get(k) != v}
            print(f"⛔ derivação local NÃO reproduz a publicada em {len(dif)} grupo(s):",
                  file=sys.stderr)
            for k, (x, y) in list(dif.items())[:5]:
                print(f"     {k}: local={x} publicado={y}", file=sys.stderr)
            return 1
        print(f"âncora: derivação local reproduz a designação publicada "
              f"({len(meu)} grupos) ✓")

    os.makedirs(a.saida_dir, exist_ok=True)
    manifesto = {"frase": FRASE, "k": a.k, "grupos": grupos, "chunks": chunks,
                 "designacoes": []}
    for i in range(1, a.k + 1):
        s = seed_da_familia(i)
        d = designados(s, linhas)
        doc = {"seed": s, "designados": d,
               "origem": f"sensibilidade: SHA256({FRASE}|{i})",
               "regra": "argmin SHA256(seed || '|' || chunk_id) por sig_primary"}
        p = os.path.join(a.saida_dir, f"DESIGNATION-sens-{i:02d}.json")
        cru = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True).encode()
        open(p, "wb").write(cru)
        manifesto["designacoes"].append({
            "i": i, "arquivo": os.path.basename(p),
            "sha256": hashlib.sha256(cru).hexdigest(),
            "seed": s, "n_designados": len(set(d.values())),
        })
        print(f"  {i:02d}  {os.path.basename(p)}  sha256={hashlib.sha256(cru).hexdigest()[:12]}…"
              f"  designados={len(set(d.values()))}")

    # nenhuma designação pode ter menos de um por grupo
    ruins = [m for m in manifesto["designacoes"] if m["n_designados"] != grupos]
    if ruins:
        print(f"⛔ {len(ruins)} designação(ões) com contagem != {grupos}", file=sys.stderr)
        return 1

    mp = os.path.join(a.saida_dir, "MANIFESTO.json")
    json.dump(manifesto, open(mp, "w"), indent=2, ensure_ascii=False)
    print(f"→ {mp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
