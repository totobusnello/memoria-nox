#!/usr/bin/env python3
"""claims_check.py — recompute every band-dependent claim and fail on divergence.

WHY THIS EXISTS
---------------
On 2026-08-17, roughly two hours after the pre-registration was deposited to
Zenodo as an immutable record, planning the implementation found a defect that
five adversarial reviewers and several mechanical censuses had walked past:

    PREREG-DRAFT.md:306 — "No locked dose reaches the main slots — the best case
    falls 0.0214 short. The entire treatment acts through the 2 coverage slots,
    never the 8 primary ones."

The `0.0214` was exact — for `w = 2.0`, S4, age 0: the top of the band as it
stood on 2026-07-29. The band was widened to `{2.0, 4.0, 7.5}` on 2026-08-16,
with the change itself documented carefully. The sentence derived from it was
not recomputed. Under the current band the best case *exceeds* the main cut by
0.2151.

A prose sentence stating a computed result is a CACHE WITH NO INVALIDATION.
Nothing links it to the parameter it depends on. A reviewer — human or model —
reads the sentence and checks whether it is COHERENT, not whether it is still
TRUE, and it was coherent, well written, and had been correct when written. A
mechanical census does not catch it either: `0.0214` is not a retired value that
survived, it is a value CORRECTLY COMPUTED under premises that changed.

So the fix cannot be discipline. It has to be a script.

WHAT IT DOES
------------
Three passes. The first is arithmetic, the second and third are the ones that
earn their keep.

1. RECOMPUTE (`claims`). Every quantity the registration DERIVES about reach --
   `w_min` per severity and age, the age cliffs per dose, the excess over the
   main cut -- is recomputed here from the frozen constants alone and compared
   against a literal typed in this file. Change a constant and the comparison
   breaks. It does NOT read the documents; see the note above `claims()`.

2. SWEEP (`sweep`). Walk every file in the package, recursively, for the literal
   numbers AND the phrase patterns that depend on the band, in both languages
   the package is written in. An occurrence is allowed only in a file that is
   both named in KNOWN_STALE and carries a correction marker -- the name alone
   is not enough, because two different files here are called `README.md`.

3. CROSS-CHECK (`cross_check`, `doc_check`). Parse the band declaration out of
   the other scripts and compare it to BAND, because a stale literal is not a
   stale string and no regex distinguishes a superseded tuple quoted in a
   correction comment from a live one. Then read the MEASURED reach figures out
   of the JSON artifact and require the prose to still state them, so a
   measurement cannot be dropped instead of updated.

Pass 2 is what makes a NEW stale claim impossible rather than improbable. A
document that acquires `0.0214` tomorrow, in a context nobody registered as
historical, stops the check.

WHAT IT DOES NOT DO -- stated because overclaiming here would be the same defect
this file exists to catch, and because an earlier version of this section DID
overclaim, in two ways that an external review found before I did.

The allowlist is per FILE, not per occurrence. A new stale claim written into
`PREREG-DRAFT.md` itself -- the document most likely to acquire one, since every
correction note there quotes the text it corrects -- passes the sweep, provided
it is not one of the quantities pass 1 or 3 covers. Narrowing the allowlist to
line ranges was considered and rejected: line numbers move with every edit, so
the guard would fail open on exactly the edits it is meant to police. Requiring
a correction marker in the file is the weaker but stable substitute.

The phrase list is a LIST. It catches the four claims that went stale on
2026-08-16 and their translations; it does not catch a fifth way of saying the
same thing that nobody has written yet. Every pattern here was added after a
defect, not before one. Read the "ok" as "none of the known failure shapes are
present", never as "the package is consistent".

USAGE
    python3 claims_check.py            # check, exit 1 on any failure
    python3 claims_check.py --show     # print the recomputed table and exit 0

No dependencies: standard library only, like every other canonical script here.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import hashlib
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen constants. These are THE inputs; everything below is derived.
# Each carries the date it was locked and the document that locks it.
# ---------------------------------------------------------------------------

DELTA_CUT = 0.043  # LOCKED 2026-07-29 — PREREG-DRAFT.md §2
CUT_FRESH = 0.7342  # LOCKED 2026-08-17 — the coverage-slot cut
CUT_MAIN = 0.8524  # the 8 primary slots; boost does not reach here by design
BAND = (2.0, 4.0, 7.5)  # LOCKED 2026-08-16, replacing {0.5, 1.0, 2.0}

# Salience v2, additive: 0.55*importance + 0.15*recency + 0.10*pain + 0.20*access
W_IMPORTANCE, W_RECENCY, W_PAIN, W_ACCESS = 0.55, 0.15, 0.10, 0.20
IMPORTANCE_LESSON = 0.90  # IMPORTANCE_BY_TYPE['lesson']
RETENTION_LESSON = 180  # days; recency = 2^(-age/retention)

SEVERITY = {"S1": 0.25, "S2": 0.50, "S3": 0.75, "S4": 1.00}
SEVERITY_SHARE = {"S1": 0.6973, "S2": 0.2962, "S3": 0.0058, "S4": 0.0008}

# A written chunk is born with access_count = 0, so the access term contributes
# nothing; pain carries the severity. This is the `base` the registration uses.
BASE_CONST = W_IMPORTANCE * IMPORTANCE_LESSON  # 0.495


def base(sev: float, age_days: float) -> float:
    """Unboosted salience of a freshly written lesson chunk of the given severity."""
    return BASE_CONST + W_RECENCY * 2 ** (-age_days / RETENTION_LESSON) + W_PAIN * sev


def w_min(sev: float, age_days: float, cut: float = CUT_FRESH) -> float:
    """The dose multiplier that lifts such a chunk to `cut`. Independent of the band."""
    return (cut - base(sev, age_days)) / (DELTA_CUT * sev)


def max_age(sev: float, w: float, cut: float = CUT_FRESH) -> float | None:
    """Oldest age at which dose `w` still clears `cut`.

    None    -> never clears it, at any age (the boost is too small outright)
    math.inf -> clears it at every age (already above the cut before decay matters)
    """
    residual = cut - BASE_CONST - W_PAIN * sev - DELTA_CUT * w * sev
    if residual <= 0:
        return math.inf
    if residual > W_RECENCY:
        return None
    return -RETENTION_LESSON * math.log2(residual / W_RECENCY)


# ---------------------------------------------------------------------------
# The claims.
#
# ⚠️ WHAT THIS COMPARES, precisely — an earlier version of this comment said each
# claim is "asserted against the number the deposited documents actually print",
# which was false and is the exact defect this file exists to catch, committed
# inside the file itself. `claims()` compares a value RECOMPUTED from the frozen
# constants against a literal TYPED HERE. If a document silently changed the
# number it prints, this pass would not notice; what it notices is a constant
# changing underneath a number that was once right. `doc_check()` below closes
# the other half for the measured quantities, by reading them out of the JSON
# artifacts and grepping the documents for disagreement.
# ---------------------------------------------------------------------------


def claims() -> list[tuple[str, float, float, float]]:
    """(label, computed, published, tolerance)."""
    out: list[tuple[str, float, float, float]] = []
    a = out.append

    a(("w_min S1 @ age 0", w_min(0.25, 0), 5.97, 0.005))
    a(("w_min S1 @ 24 h", w_min(0.25, 1), 6.03, 0.005))
    a(("w_min S1 @ 30 d", w_min(0.25, 30), 7.49, 0.005))
    a(("w_min S2 @ age 0", w_min(0.50, 0), 1.82, 0.005))
    a(("w_min S2 @ 24 h", w_min(0.50, 1), 1.85, 0.005))
    a(("w_min S3 @ age 0", w_min(0.75, 0), 0.44, 0.005))

    a(("S2 age cliff at w = 2.0", max_age(0.50, 2.0), 6.66, 0.005))
    a(("S2 window at w = 4.0", max_age(0.50, 4.0), 97.11, 0.01))
    a(("S1 window at w = 7.5", max_age(0.25, 7.5), 30.12, 0.01))
    a(("S2 main-cut window at w = 7.5", max_age(0.50, 7.5, CUT_MAIN), 6.75, 0.01))

    # The claim that went stale, in both its forms.
    old_band_top = 2.0
    a((
        "old band shortfall at main cut (w = 2.0, S4)",
        CUT_MAIN - (base(1.0, 0) + DELTA_CUT * old_band_top * 1.0),
        0.0214,
        0.0001,
    ))
    a((
        "current band excess at main cut (w = 7.5, S4)",
        (base(1.0, 0) + DELTA_CUT * BAND[-1] * 1.0) - CUT_MAIN,
        0.2151,
        0.0001,
    ))

    # The margin that is too thin to be a design property, and is registered as such.
    a(("S1 margin at 30 d (7.5 - w_min)", BAND[-1] - w_min(0.25, 30), 0.0056, 0.0005))
    return out


# ---------------------------------------------------------------------------
# Pass 2: the sweep.
#
# Each entry is (regex, human-readable reason it is band-dependent). Any match
# outside KNOWN_STALE is a failure — the point is that a NEW occurrence, in a
# document nobody has marked as historical, stops the check.
# ---------------------------------------------------------------------------

BAND_DEPENDENT = [
    (r"0\.0214", "the old band's shortfall at the main cut"),
    (r"three times the top", "false: 6.0 is below the current top of 7.5"),
    (r"out of reach at every locked dose", "false at w = 7.5"),
    (r"no locked dose reaches the main slots", "false at w = 7.5"),
    (r"\{0\.5[ ,;·]+1\.0[ ,;·]+2\.0\}", "the superseded band written as a set"),
    # Added 2026-08-17 after `reachable_share.py` was found defaulting to the old
    # band under the comment "the locked band". An earlier review called excluding
    # the tuple form defensible, on the grounds that the sweep targets prose; the
    # script that produces the reach numbers is exactly where it was not.
    (r"\(0\.5,\s*1\.0,\s*2\.0\)", "the superseded band written as a tuple"),
    # These were among the four original stale claims and the first version of
    # this sweep did not look for any of them. That is how the OSF abstract and
    # the repository README kept theirs: the numeric patterns above do not appear
    # in a sentence that says "about 30% of failures" in words.
    #
    # ⚠️ BILINGUAL, and this was not an afterthought — it was a hole. The package
    # is written in two languages: the registration and the deposited documents
    # in English, and the working documents that route the project in Portuguese,
    # including `OSF-SUBMISSION.md`, whose abstract becomes the permanent public
    # OSF registration. The first version of these three patterns was
    # English-only, so the sweep was structurally blind to the half of the corpus
    # where two of the surviving stale claims actually lived. A positive-control
    # run caught it: a synthetic "~30% dos failures" passed cleanly.
    (r"(?:about|~|approximately|cerca de|aproximadamente|em torno de)\s*30\s*%\s*(?:of|dos|das|de)\s+(?:the\s+|os\s+|as\s+)?(?:failures|falhas)",
     "reach is 30% only at w = 2.0; 100% at w = 7.5"),
    (r"(?:only\s+at\s+severity|apenas\s+(?:a\s+)?severidade|s[oó]\s+(?:a\s+)?severidade)\s*S2\s+(?:and above|e acima|ou acima|para cima)",
     "true at w = 2.0 only; S1 is reachable at w = 7.5"),
    (r"S1[^.\n]{0,40}(?:never|nunca)[^.\n]{0,40}(?:locked dose|dose travada)",
     "S1 needs w = 5.97 and the band's top is 7.5"),
]

# Deliberately preserved occurrences: dated records, and the correction notes
# that quote the superseded text in order to correct it. Keyed by filename; a
# match in any OTHER file fails regardless of what it says.
KNOWN_STALE = {
    # The correction itself has to quote what it corrects.
    "PREREG-DRAFT.md": "carries the corrections; quoting the stale text is the point",
    "DEPOSIT-README.md": "same, on the deposit's front page",
    # The same file, under the name it carries INSIDE the deposit. Both keys are
    # needed and the omission was caught by this check on its first real run:
    # the deposit renames DEPOSIT-README.md to README.md, so an allowlist keyed
    # on the repository name fails open in the repository and closed in the
    # deposit — the direction that at least announces itself, but still wrong.
    # ⚠️ Keyed by name, and two DIFFERENT files are called README.md: the
    # deposit's front page (DEPOSIT-README.md renamed) and the repository's own
    # navigation index. Exempting the name exempted both, and the repository
    # README was carrying a stale "~30% of failures" that the sweep therefore
    # never reported. The exemption now requires the file to CARRY a correction
    # marker, so a file that merely shares the name is still swept.
    "README.md": "DEPOSIT-README.md under its in-deposit name",
    # Dated measurements, superseded-header'd rather than rewritten.
    "LINK-FEASIBILITY-2026-08-15.md": "2026-08-15 measurement, header marks it",
    "REACHABILITY-2026-08-16.md": "narrates the reviews that motivated the widening",
    "dose_reach.mjs": "must keep reproducing DOSE-REACH-2026-08-15.json byte for byte",
    "link_feasibility.mjs": "same",
    "DOSE-REACH-2026-08-15.json": "the output itself",
    "DISPLACEMENT-2026-08-16.txt": "raw output of the candidate-band run",
    "claims_check.py": "this file names the patterns in order to search for them",
    # Allowlisted for the REGEX only, and only because `cross_check` below reads
    # its band declaration structurally and compares it to BAND. That is the
    # right layering: the file quotes the superseded tuple inside a correction
    # comment, which no regex can distinguish from a live one, while the thing
    # that actually matters — what the script will USE — is checked by parsing
    # rather than by matching. Removing cross_check would silently downgrade this
    # entry from "checked a better way" to "not checked".
    "reachable_share.py": "correction comment quotes the old tuple; cross_check covers the real value",
    # Same file, one line apart (CUT_FRESH). Same justification, and it holds only
    # because `cross_check` now parses this name too — see the note there.
    "reachable_share_fila.py": "one-line variant of the above; cross_check covers the real value",
}

SCAN_SUFFIXES = {".md", ".py", ".mjs", ".json", ".txt", ".jsonl"}

# An allowlist entry only takes effect if the file actually says, somewhere, that
# it is preserving superseded text on purpose. Without this, exempting a NAME
# exempts every file that happens to carry it.
MARKERS = ("SUPERSEDED", "CORRECTED", "superseded", "corrected 2026", "the old band",
           "band then in force", "LOCKED when this ran", "locked when this ran")


def _is_marked(path: Path) -> bool:
    try:
        return any(m in path.read_text(encoding="utf-8") for m in MARKERS)
    except (UnicodeDecodeError, OSError):
        return True  # binary or unreadable: nothing to sweep anyway


def sweep(root: Path) -> list[str]:
    failures = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        # ⚠️ `receipts/` guarda a SAÍDA das vozes adversariais, preservada byte a byte
        # (só `host:` e o IP da VPS foram redigidos, e isso está declarado lá). Elas
        # CITAM a banda superseded porque leram os documentos históricos. Editá-las
        # para satisfazer o sweep falsificaria o registro da revisão, que é justamente
        # o que elas existem para provar. Limitação declarada, não resolvida: o guarda
        # não policia esse diretório, e um número obsoleto que apareça só ali passa.
        if "receipts" in path.parts:
            continue
        if path.name in KNOWN_STALE and _is_marked(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern, reason in BAND_DEPENDENT:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                line = text.count("\n", 0, m.start()) + 1
                failures.append(
                    f"{path.name}:{line}: band-dependent claim outside the "
                    f"allowlist — {reason!r} (matched {m.group(0)!r})"
                )
    return failures


def doc_check(root: Path) -> list[str]:
    """Check the MEASURED quantities against the artifact, not against a literal.

    `claims()` recomputes from constants, which covers the arithmetic but not the
    measurements: the reachable shares come out of a run over the corpus and
    cannot be derived from `DELTA_CUT` and friends. Those numbers travel through
    the documents as typed percentages, so they can drift from the JSON that
    produced them exactly the way the prose drifted from the band.

    So: read them out of `REACHABILITY-TOP1-2026-08-16.json`, and require that
    each still appears somewhere in the prose. A number that vanishes is as much
    a defect as a number that changes -- it means a document was rewritten and
    the measurement it rested on was dropped rather than updated.
    """
    failures = []
    art = root / "REACHABILITY-TOP1-2026-08-16.json"
    if not art.exists():
        return [f"{art.name}: missing — the measured reach figures cannot be checked"]
    data = json.loads(art.read_text(encoding="utf-8"))

    corpus = {
        p.name: p.read_text(encoding="utf-8", errors="ignore")
        for p in root.rglob("*.md")
        if "__pycache__" not in p.parts
    }

    for key, label in (
        ("fracao_alcancavel_por_dose", "reachable share"),
        ("teto_de_efeito_incondicional_por_dose", "unconditional ceiling"),
    ):
        for dose, frac in sorted(data[key].items()):
            if float(dose) not in BAND:
                continue
            pct = f"{frac * 100:.2f}"
            if not any(pct in text for text in corpus.values()):
                failures.append(
                    f"{art.name}: {label} at w = {dose} is {pct}%, and no document "
                    f"in the package states it — dropped rather than updated?"
                )
    return failures


ANCORAS_DA_EMENDA = ("perde estatuto de parâmetro", "a banda é invalidada",
                     "gap máximo **intragrupo**")


def _alvo_emenda(root: Path) -> Path | None:
    """O documento que carrega a emenda, resolvido por CONTEÚDO e não por nome.

    ⚠️ Duas funções deste script prendiam o nome `AMENDMENT-DRAFT-band-collapse-...md`.
    No dia do depósito o arquivo é renomeado (`AMENDMENT-v1.13.md`, como a v1.12 foi), e
    aí uma delas quebrava por motivo errado e a outra **falhava aberta** — a checagem
    simplesmente não rodava, sem dizer nada. Falhar aberto num guarda é pior que
    falhar: o verde passa a significar "não olhei".

    Cada âncora foi conferida em 2026-08-27 como presente na emenda e ausente de todo
    outro `.md` do pacote. `receipts/` fica fora: são saídas externas que CITAM a
    emenda inteira e casariam com qualquer âncora.
    """
    if (direto := root / "AMENDMENT-DRAFT-band-collapse-2026-08-26.md").exists():
        return direto
    for p in sorted(root.rglob("*.md")):
        if "receipts" in p.parts:
            continue
        texto = p.read_text(encoding="utf-8", errors="ignore").lower()
        if any(a in texto for a in ANCORAS_DA_EMENDA):
            return p
    return None


def janela_check(root: Path) -> list[str]:
    """Recomputa a taxa central da emenda a partir do EXTRATO DEPOSITADO.

    Até 2026-08-27 o `11/350` do §4.1-bis era conferível apenas contra um JSON que eu
    mesmo escrevi: o NDJSON de origem vive no host e não está no pacote. A sexta
    leitura (Fable) cobrou isso — "a janela não é recomputável do pacote" — e a
    resposta foi depositar o extrato da janela fechada. Este guarda fecha o laço: a
    taxa, a exclusão de sondas e a integridade `19/19` saem do arquivo, não da prosa.

    Também confere a lacuna oposta: a emenda **não pode** afirmar mais saídas
    adversariais do que existem em `receipts/`. Essa foi a única classe de defeito que
    sobreviveu a seis leituras — a autodescrição do depósito.
    """
    failures = []
    rem = _remediacao(root)
    jf = rem["janela_fechada"]
    ini, fim = jf["intervalo"]
    nome = "p2-serving-CLOSED-WINDOW-2026-08-26T2028-2026-08-27T0900.ndjson"
    f = root / nome
    if not f.exists():
        return [f"{nome}: ausente — a taxa central da emenda volta a ser inconferível do pacote"]
    linhas = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [json.loads(l) for l in linhas]
    fora = [r["ts"] for r in rows if not (ini <= r["ts"] < fim)]
    if fora:
        failures.append(
            f"{nome}: {len(fora)} linha(s) fora da janela declarada [{ini}, {fim}) "
            f"— a primeira é {fora[0]}"
        )
    sonda = [r for r in rows if not r.get("agent")]
    limpo = [r for r in rows if r.get("agent")]
    k = sum(1 for r in limpo if r.get("churn", 0) > 0)
    esp = jf["regra_nova"]
    if (k, len(limpo)) != (esp["k"], esp["n"]):
        failures.append(
            f"{nome}: recomputa {k}/{len(limpo)}, a emenda publica {esp['k']}/{esp['n']}"
        )
    if len(sonda) != 2:
        failures.append(
            f"{nome}: {len(sonda)} decisões sem `agent`, a emenda declara 2 (as sondas)"
        )
    # `designated_ids` = 19 e `boost_by_id` = 19 em TODAS — a integridade do mecanismo.
    d19 = sum(1 for r in limpo if len(r.get("designated_ids", [])) == 19)
    b19 = sum(1 for r in limpo if len(r.get("boost_by_id", {})) == 19)
    if d19 != len(limpo) or b19 != len(limpo):
        failures.append(
            f"{nome}: designated_ids==19 em {d19}/{len(limpo)} e boost_by_id==19 em "
            f"{b19}/{len(limpo)} — a emenda afirma {len(limpo)} de {len(limpo)} em ambos"
        )

    # --- a autodescrição do depósito: saídas afirmadas vs saídas existentes ---
    rec = root / "receipts"
    saidas = sorted(rec.glob("adversary-output-*")) if rec.exists() else []
    alvo = _alvo_emenda(root)
    if alvo is None:
        failures.append(
            "nenhum .md do pacote carrega a emenda (âncoras: "
            f"{', '.join(ANCORAS_DA_EMENDA)}) — a checagem das saídas não pode rodar"
        )
    else:
        texto = alvo.read_text(encoding="utf-8")
        if len(saidas) < 5 and re.search(r"[Rr]ecibos e saídas das cinco vozes", texto):
            failures.append(
                f"{alvo.name}: afirma 'recibos e saídas das cinco vozes' e existem "
                f"{len(saidas)} saída(s) em receipts/ — autodescrição do depósito falsa "
                f"(retratação 44)"
            )
        if len(saidas) < 5 and "As saídas integrais estão versionadas" in texto:
            failures.append(
                f"{alvo.name}: afirma que as saídas integrais estão versionadas e só "
                f"{len(saidas)} existe(m) (retratação 44)"
            )
    return failures


def blob_check(root: Path) -> list[str]:
    """Confere que os blobs depositados batem com o `sha256` do manifesto.

    Existe porque 2026-08-27 mostrou as duas metades do mesmo defeito. Primeiro, a
    emenda pinava o código em `0087c918`, um objeto que NÃO EXISTE no repositório —
    nem commit, nem ref, nem reflog — porque um merge reescreveu os hashes do lado da
    VPS. Segundo, ao transferir os blobs, a primeira tentativa normalizou o fim de
    arquivo e produziu 44749 bytes onde o original tem 44748: um blob "depositado" que
    não era o arquivo.

    Nenhuma das duas falhas é visível na prosa. Um manifesto cujos hashes não batem lê
    exatamente como um que bate, e a citação `brief.ts:1086` continua parecendo
    precisa apontando para linha nenhuma.
    """
    failures = []
    man = root / "SERVING-CODE-MANIFEST.md"
    if not man.exists():
        return [f"{man.name}: ausente — os blobs de serving ficam sem proveniência"]
    texto = man.read_text(encoding="utf-8")
    # ⚠️ DUAS formas de tabela, e a primeira versão deste guarda só via uma.
    #
    #   (a) `| dep | orig | bytes | sha |`                        — 4 colunas
    #   (b) `| dep | orig | commit | committed | bytes | sha |`    — 6 colunas
    #
    # O regex antigo cobria só (a). As três linhas de (b) — `brief-diversity`,
    # `salience`, `search` — ficavam fora, e ficavam fora JUSTAMENTE porque não tinham
    # sha256: o guarda calava por não ter o dado, não por não haver problema. É a
    # forma canônica do defeito da regra 9 do CLAUDE.md, e ela sobreviveu aqui porque
    # o comentário antigo chamava a lacuna de "declaradamente fora", o que a fazia ler
    # como decisão em vez de omissão.
    linhas = [(d, o, b, s) for d, o, b, s in
              re.findall(r"^\| `([^`]+)` \| `([^`]+)` \| (\d+) \| `([0-9a-f]{64})` \|",
                         texto, re.M)]
    linhas += [(d, o, b, s) for d, o, _c, _t, b, s in
               re.findall(r"^\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \| ([^|]+) \| "
                          r"(\d+) \| `([0-9a-f]{64})` \|", texto, re.M)]
    if not linhas:
        return [f"{man.name}: nenhuma linha com sha256 completo — o manifesto não pina nada"]

    # ── completude: todo blob depositado tem de estar pinado por sha256 ──────
    # Sem isto o guarda só verifica o que já foi declarado, e um arquivo acrescentado
    # ao pacote sem hash entra sem que nada acuse — que foi exatamente o que aconteceu
    # com os três da tabela (b) entre 26/08 e 30/08.
    pinados = {d for d, _o, _b, _s in linhas}
    em_disco = {p.name for p in root.glob("serving-*.ts")}
    sem_pino = sorted(em_disco - pinados)
    if sem_pino:
        failures.append(
            f"{man.name}: {len(sem_pino)} blob(s) de serving no pacote SEM sha256 no "
            f"manifesto: {sem_pino} — o manifesto afirma que toda linha carrega o hash "
            f"dos bytes, e um leitor sem o repositório privado não consegue conferir "
            f"estes contra o depósito"
        )
    for depositado, original, bytes_esperados, sha_esperado in linhas:
        f = root / depositado
        if not f.exists():
            failures.append(
                f"{man.name}: pina `{depositado}` (de `{original}`) e o arquivo não existe "
                f"— artefato REGISTRADO que não está no pacote"
            )
            continue
        b = f.read_bytes()
        if len(b) != int(bytes_esperados):
            failures.append(
                f"{depositado}: {len(b)} bytes, manifesto diz {bytes_esperados} — "
                f"transporte alterou o arquivo (fim de linha? newline final?)"
            )
        got = hashlib.sha256(b).hexdigest()
        if got != sha_esperado:
            failures.append(
                f"{depositado}: sha256 {got[:16]}…, manifesto diz {sha_esperado[:16]}… "
                f"— o blob depositado NÃO é o arquivo que o manifesto declara"
            )
    return failures


def _afirmada(frase: str, texto: str) -> list[int]:
    """Linhas em que `frase` é AFIRMADA — não citada, não numa tabela de retratação.

    ⚠️ Presença simples não distingue asserção de citação, e a primeira versão desta
    checagem acusou três vezes o próprio documento por ele CITAR o texto que retrata.
    É a classe do guarda-decoração invertida: em vez de nunca morder, mordia o
    inocente. Uma emenda é obrigada a citar o que retrata; um guarda que proíbe a
    citação proíbe a auditabilidade.

    Isenta duas formas, e só estas duas:
      - linha que começa com `|` — fila da tabela de retratações;
      - ocorrência encostada em aspas (tipográficas ou ASCII) ou em `*` na mesma linha.

    ⚠️ Custo declarado: aceitar aspas ASCII abre evasão — bastaria envolver uma
    afirmação real em aspas para escapar. É trade-off consciente e o risco é baixo,
    porque texto entre aspas lê como citação para o revisor humano também. O que NÃO
    é aceitável é o oposto: um guarda que proíbe citar o texto retratado força a
    emenda a esconder o que a revisão derrubou.
    """
    fora = []
    for ln, linha in enumerate(texto.splitlines(), 1):
        if frase not in linha:
            continue
        if linha.lstrip().startswith("|"):
            continue
        if any(f'{a}{frase}' in linha or f'{frase}{b}' in linha
               for a, b in (('\u201c', '\u201d'), ('"', '"'), ('*', '*'))):
            continue
        fora.append(ln)
    return fora


def _remediacao(root: Path) -> dict:
    """Artefato da remediação de 2026-08-27.

    Existe separado do `DELTA-CUT-MEASUREMENT-2026-08-26.json` de propósito: aquele
    ficou como registro do que a 2ª redação media, com o script que fazia rollback
    temporal em vez de descontaminação. Sobrescrevê-lo apagaria a evidência do erro.
    """
    art = root / "REMEDIATION-2026-08-27.json"
    if not art.exists():
        raise FileNotFoundError(
            "REMEDIATION-2026-08-27.json ausente — as medições remediadas não podem "
            "ser conferidas, e são elas que a emenda publica"
        )
    return json.loads(art.read_text(encoding="utf-8"))


def delta_cut_check(root: Path) -> list[str]:
    """Guard the `Δ_cut` measurement of 2026-08-26 the way doc_check guards reach.

    The band-collapse amendment rests on quantities that came out of a run over
    the live pool, not out of arithmetic on constants: the gap distribution
    inside `last_served` tie groups, the pool composition, and the per-arm win
    counts against those gaps. `claims()` cannot recompute them and `sweep()`
    does not know them, so before this function existed the amendment's central
    table sat OUTSIDE the guard entirely -- verified on 2026-08-26 by mutating
    `4,1693%` to `9,9999%` and the `w = 7,5` cell to `0,9999`, and watching
    `claims_check.py` print "sweep clean" both times.

    Two things are asserted, and they fail differently:

     1. the measured figures still appear in the prose -- a number that vanishes
        is as much a defect as one that changes (same argument as doc_check);
     2. the win counts are RECOMPUTED from the stored gap list, so a reader does
        not have to trust that `w = 2,0` for S1 really wins 16 of 27. This is why
        the artifact stores every positive gap and not just the quantiles.
    """
    failures = []
    art = root / "DELTA-CUT-MEASUREMENT-2026-08-26.json"
    if not art.exists():
        return [f"{art.name}: missing — the Δ_cut measurement cannot be checked"]
    data = json.loads(art.read_text(encoding="utf-8"))
    # A remediação de 27/08 é a fonte de verdade para tudo que os scripts de 26/08
    # mediram com rollback temporal, janela aberta ou `julianday('now')`. Carregada
    # aqui, no topo, porque metade das âncoras abaixo depende dela.
    rem = _remediacao(root)

    # ⚠️ Presença tem de ser verificada CONTRA O DOCUMENTO e ANCORADA NUM RÓTULO.
    # A primeira versão desta função fazia `str(valor) in "\n".join(todos_os_md)`, e
    # o teste de mutação de 2026-08-26 mostrou que isso é decoração: falsifiquei
    # `4,1693%` na emenda e passou (o número segue em outros dois documentos), e
    # `posição 15` -> `posição 99` também passou (a string "15" casa em qualquer
    # lugar do pacote). Número pequeno buscado por substring em corpus inteiro é um
    # guarda que nunca morde. Cada checagem abaixo amarra o valor a uma palavra
    # vizinha, no arquivo que faz a afirmação.
    alvo = _alvo_emenda(root)
    if alvo is None:
        return failures + [
            "nenhum .md do pacote carrega a emenda (âncoras: "
            f"{', '.join(ANCORAS_DA_EMENDA)}) — a medição de Δ_cut perdeu o documento"
        ]
    texto = alvo.read_text(encoding="utf-8", errors="ignore")

    def ancorado(padrao: str, rotulo: str, valor: str) -> None:
        """Exige `valor` numa vizinhança que o identifica, não em qualquer lugar."""
        if not re.search(padrao, texto):
            failures.append(
                f"{alvo.name}: {rotulo} should read {valor} anchored to its label "
                f"(/{padrao}/ does not match) — measurement dropped or falsified?"
            )

    def ocorrencias(literal: str, esperado: int, rotulo: str) -> None:
        """Exige que TODAS as ocorrências de um valor concordem.

        ⚠️ O teste de mutação de 27/08 mostrou que `ancorado` sozinho é satisfeito por
        UMA ocorrência: quatro falsificações passaram porque o valor aparece 2–3 vezes
        no documento e eu havia mutado só a primeira. Isso não é mutação ruim de
        laboratório — é o buraco real: uma tabela que discorde da citação em bloco
        passa pelo guarda. Prender a contagem faz qualquer divergência interna morder.

        O custo é que edição legítima que mude o número de menções tem de atualizar o
        esperado aqui, DE PROPÓSITO. Num documento a caminho do depósito, isso é
        aceitável; num documento vivo, seria atrito.
        """
        visto = texto.count(literal)
        if visto != esperado:
            failures.append(
                f"{alvo.name}: {rotulo} aparece {visto}× e deveria aparecer {esperado}× "
                f"({literal!r}) — ou uma ocorrência divergiu, ou uma foi removida"
            )

    ancorado(rf"candidatos no pool.*?\*\*{data['pool']}\*\*", "pool size", str(data["pool"]))
    ancorado(rf"grupos de `last_served` distintos.*?{data['grupos_last_served']}",
             "distinct last_served groups", str(data["grupos_last_served"]))
    ancorado(rf"{data['pares_adjacentes_envolvendo_estudo']} pares, \*\*"
             rf"{data['gaps_exatamente_zero']} exatamente zero\*\*",
             "pairs and exactly-zero gaps",
             f"{data['pares_adjacentes_envolvendo_estudo']}/{data['gaps_exatamente_zero']}")
    ancorado(rf"os {data['grupos_mistos_qualificaveis']}/{data['grupos_last_served']} "
             rf"n[ãa]o medem a oportunidade",
             "qualifying mixed groups (now retracted as a measure of opportunity)",
             f"{data['grupos_mistos_qualificaveis']}/{data['grupos_last_served']}")
    # ⚠️ Precisão INTEIRA, não arredondada: `0,031809` é compatível com mais de uma
    # reconstrução (a de definição errada dava 0,0463), então o dígito longo é o que
    # amarra o número à definição. Fonte: o artefato da remediação.
    gmax = str(rem["descontaminacao_correta"]["observado"]["gap_maximo"]).replace(".", ",")
    ancorado(rf"gap máximo \*\*intragrupo\*\* \| \*\*{re.escape(gmax)}\*\*",
             "max within-tie gap (full precision)", gmax)

    # A base de churn foi CORRIGIDA: a pós-gate é a boa, e a antiga tem de aparecer
    # marcada como superseded, não desaparecer.
    b = data["churn_baseline"]
    # ⚠️ `base_correta_pos_gate` do artefato de 26/08 ficou SUPERSEDED: media uma janela
    # mais curta (2.212) e não excluía sondas. A verdade é a janela fechada da remediação.
    ag = rem["janela_fechada"]["regra_velha_pos_gate_agregado"]
    pct = f"{100 * ag['k'] / ag['n']:.4f}".replace(".", ",")
    ancorado(rf"\*\*{ag['k']}/{ag['n'] // 1000}\.{ag['n'] % 1000:03d} = "
             rf"{re.escape(pct)}%\*\*", "post-gate baseline rate (closed window)", pct + "%")
    velho = b["SUPERSEDIDO_todas_as_decisoes"]
    velho_pct = f"{velho['pct']:.4f}".replace(".", ",")
    ancorado(rf"{velho['positivo']}/{velho['total'] // 1000}\.{velho['total'] % 1000:03d} = "
             rf"{re.escape(velho_pct)}%", "superseded diluted rate (must stay, marked)",
             velho_pct + "%")
    # A série tem de estar publicada: taxa não-estacionária citada como constante é
    # o defeito que esta emenda retrata (retratação 34).
    for dia, (k, n) in sorted(rem["janela_fechada"]["regra_velha_serie_diaria"].items()):
        dpct = f"{100 * k / n:.4f}".replace(".", ",")
        if dpct.rstrip("0").rstrip(",") not in texto and dpct not in texto:
            failures.append(
                f"{alvo.name}: daily rate for {dia} is {dpct}% ({k}/{n}) and the document "
                f"does not state it — a non-stationary series cited as one number is "
                f"exactly retraction 34"
            )
    # A contaminação altera a conclusão: as duas colunas têm de estar na mesa.
    # ⚠️ `str(v) not in texto` seria vacuidade — "1" casa em qualquer lugar. As duas
    # colunas têm de aparecer NA MESMA LINHA da tabela de sensibilidade, que é a
    # única forma de a comparação estar de fato publicada.
    # ⚠️ A fonte da sensibilidade mudou em 2026-08-27: o `contaminacao_por_sondas` do
    # artefato de 26/08 foi produzido pelo script que fazia ROLLBACK TEMPORAL, não
    # descontaminação (REMEDIATION-2026-08-27.md §1). A verdade agora é o artefato
    # da remediação, e é ele que este guarda lê.
    dc = rem["descontaminacao_correta"]
    obs, des = dc["observado"], dc["descontaminado"]
    ancorado(rf"posição do 1º chunk do estudo \| \*\*{obs['posicao_primeiro_estudo']}\*\* \| "
             rf"\*\*{des['posicao_primeiro_estudo']}\*\*",
             "contamination sensitivity on position (observed vs decontaminated, same row)",
             f"{obs['posicao_primeiro_estudo']} vs {des['posicao_primeiro_estudo']}")
    # E o que NÃO muda tem de estar afirmado, senão a independência do §3 fica implícita.
    for campo in ("pares_adjacentes_no_grupo", "gaps_exatamente_zero", "gaps_positivos"):
        if obs[campo] != des[campo]:
            failures.append(
                f"REMEDIATION-2026-08-27.json: {campo} muda com a descontaminação "
                f"({obs[campo]} -> {des[campo]}), mas a emenda afirma que nenhuma "
                f"estatística de gap muda"
            )
    if obs["gap_maximo"] != des["gap_maximo"]:
        failures.append("REMEDIATION: gap_maximo muda com a descontaminação")
    # As 5 sondas — a segunda redação contava 3, e o número é o que sustenta a §4.2.
    s = rem["sondas"]
    if len(s["brief_ids"]) != s["quantas"] or s["quantas"] * 5 != s["linhas_em_brief_log"]:
        failures.append(
            f"REMEDIATION: {s['quantas']} sondas, {len(s['brief_ids'])} ids, "
            f"{s['linhas_em_brief_log']} linhas — não fecham em 5 linhas por sonda"
        )
    ancorado(rf"\*\*cinco\*\* sondas, \*\*{s['linhas_em_brief_log']}\*\* linhas",
             "probe count (five probes, 25 rows)", str(s["linhas_em_brief_log"]))

    gaps = data["gaps_positivos"]
    if len(gaps) != 27:
        failures.append(f"{art.name}: expected 27 positive gaps, artifact has {len(gaps)}")
    d = data["delta_cut_herdado"]
    # Recomputa as contagens de vitória. Fonte da verdade: o artefato.
    esperado = {(2.0, "S1"): 16, (2.0, "S2"): 27, (4.0, "S1"): 27,
                (4.0, "S2"): 27, (7.5, "S1"): 27, (7.5, "S2"): 27}
    for (w, sev), quantos in sorted(esperado.items()):
        boost = w * d * (0.25 if sev == "S1" else 0.5)
        vence = sum(1 for g in gaps if g < boost)
        if vence != quantos:
            failures.append(
                f"{art.name}: w={w} {sev} boost {boost:.4f} beats {vence}/{len(gaps)} "
                f"gaps, the amendment claims {quantos}/27"
            )
    # A afirmação estrutural: o braço MAIS BAIXO já satura para S2.
    if not (2.0 * d * 0.5) > data["gap_maximo"]:
        failures.append(
            f"{art.name}: the amendment says w=2.0/S2 saturates, but "
            f"{2.0 * d * 0.5:.6f} <= max gap {data['gap_maximo']:.6f}"
        )
    # E a faixa que discrimina existe: S1 a w=2.0 NÃO vence tudo.
    if (2.0 * d * 0.25) > data["gap_maximo"]:
        failures.append(
            f"{art.name}: the amendment says w=2.0/S1 discriminates, but it also "
            f"saturates ({2.0 * d * 0.25:.6f} > {data['gap_maximo']:.6f})"
        )

    # --- regra nova: janela FECHADA, taxa e IC RECOMPUTADOS de k/n ---
    jf = rem["janela_fechada"]
    rn = jf["regra_nova"]
    pct = 100 * rn["k"] / rn["n"]
    if abs(pct - rn["pct"]) > 5e-5:
        failures.append(f"REMEDIATION: {rn['k']}/{rn['n']} = {pct:.4f}%, artefato diz {rn['pct']}%")
    lo, hi = _wilson(rn["k"], rn["n"])
    for got, want, nome in ((lo, rn["wilson95"][0], "inferior"), (hi, rn["wilson95"][1], "superior")):
        if abs(got - want) > 0.01:
            failures.append(f"REMEDIATION: Wilson {nome} recomputa {got:.2f}, artefato diz {want}")
    ancorado(rf"\*\*{rn['k']}/{rn['n']}\*\* \| \*\*3,1429%\*\*",
             "new-rule activation rate (closed window)", f"{rn['k']}/{rn['n']}")
    ancorado(rf"\*\*{rn['n']} de {rn['n']}\*\* decis",
             "mechanism integrity (19/19 in every decision)", str(rn["n"]))
    # A janela tem de estar FECHADA no texto — foi o defeito que gerou o 11/310.
    ini, fim = jf["intervalo"]
    ancorado(rf"\[{re.escape(ini)} , {re.escape(fim)}\)",
             "closed window declared with both endpoints", fim)

    # Os quatro valores que o teste de mutação mostrou serem satisfeitos por uma
    # ocorrência só. A contagem vem do estado conferido em 2026-08-27T12:20Z.
    ini_j, fim_j = jf["intervalo"]
    ocorrencias(f"{fim_j})", 2, "fim da janela fechada")
    ag_ = jf["regra_velha_pos_gate_agregado"]
    pct_ag = f"{100 * ag_['k'] / ag_['n']:.4f}".replace(".", ",")
    ocorrencias(f"**{ag_['k']}/{ag_['n'] // 1000}.{ag_['n'] % 1000:03d} = {pct_ag}%**", 2,
                "linha de base pós-gate")
    d26 = jf["regra_velha_serie_diaria"]["2026-08-26"]
    ocorrencias(f"{100 * d26[0] / d26[1]:.4f}".replace(".", ",") + "%", 3,
                "taxa diária de 26/08")
    # ⚠️ Os 27 gaps vivem em DOIS artefatos, e só um era lido — o outro podia derivar
    # em silêncio. Mutar a cópia não conferida foi uma das quatro que não morderam.
    if sorted(rem["saturacao"]["gaps_positivos"]) != sorted(data["gaps_positivos"]):
        failures.append(
            "REMEDIATION-2026-08-27.json e DELTA-CUT-MEASUREMENT-2026-08-26.json "
            "discordam na lista dos 27 gaps — a duplicação derivou"
        )

    # A soma da serie diaria da regra velha tem de fechar no agregado.
    serie = jf["regra_velha_serie_diaria"]
    sk = sum(v[0] for v in serie.values()); sn = sum(v[1] for v in serie.values())
    ag = jf["regra_velha_pos_gate_agregado"]
    if (sk, sn) != (ag["k"], ag["n"]):
        failures.append(
            f"REMEDIATION: soma da serie diaria = {sk}/{sn}, agregado diz {ag['k']}/{ag['n']}"
        )

    # ⚠️ CONSERTO CONCEITUAL (2026-08-27). A versao anterior deste guarda exigia que a
    # taxa nova caisse DENTRO do IC da antiga, e chamava isso de "as taxas sao
    # indistinguiveis". Sobreposicao de IC NAO e equivalencia: a assercao codificava um
    # raciocinio invalido como invariante. O que o guarda tem de garantir agora e o
    # oposto — que a emenda NAO afirme equivalencia, e que a comparacao confundida NAO
    # seja usada como efeito.
    proibidas = ["praticamente idêntico", "as taxas são indistinguíveis",
                 "refuta uma suposição", "largamente sobrepostos"]
    # ⚠️ Presença simples NAO distingue asserção de CITAÇÃO. A primeira versão desta
    # checagem acusou três vezes o próprio documento por ele CITAR o texto que retrata
    # — mesma classe do guarda-decoração, invertida: em vez de nunca morder, mordia o
    # inocente. Isenta-se linha de tabela de retratação e ocorrência entre aspas.
    for frase in proibidas:
        for ln in _afirmada(frase, texto):
            failures.append(
                f"{alvo.name}:{ln}: afirma \"{frase}\" fora de citação — equivalência ou "
                f"refutação sem TOST com margem pré-especificada (ver §4.1-bis)"
            )
    ancorado(r"não se estabelece aumento,\s*\n?>?\s*redução nem equivalência",
             "the amendment refuses to claim any direction", "não se estabelece")
    ancorado(r"agregada é \*\*significante e não deve ser usada\*\*",
             "the confounded pooled comparison is marked unusable", "não deve ser usada")

    # --- auto-extincao: NAO TESTADA. A serie e toda anterior ao tratamento. ---
    for ln in _afirmada("testada e NÃO se sustenta", texto):
        failures.append(
            f"{alvo.name}:{ln}: afirma que a auto-extinção foi 'testada e NÃO se sustenta' "
            f"fora de citação. A série é toda anterior ao tratamento (retratação 36)"
        )
    # ⚠️ Terceira vez que uma âncora falha por eu escrever o regex supondo a MINHA
    # pontuação: a prosa põe o negrito em volta da frase inteira, não do trecho.
    ancorado(r"\*\*A hipótese de auto-extinção NÃO foi testada",
             "auto-extinction is declared untested, not refuted", "NÃO foi testada")
    ae = data["autoextincao_testada"]
    for x in ae["serie"]:
        ancorado(rf"{x['est_em_puro']} de 55 — \*\*{str(x['pct']).replace('.', ',')}%\*\*",
                 f"pure-study fraction at {x['corte']}", f"{x['pct']}%")

    return failures


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """IC de Wilson em pontos percentuais. Aqui, e nao no artefato, para que o
    artefato possa estar errado e o guarda notar."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d * 100, (c + m) / d * 100)


def cross_check(root: Path) -> list[str]:
    """Assert that the OTHER scripts agree with the band declared here.

    A regex sweep catches a stale value written as text. It does not catch a
    stale value that is simply a different literal — `reachable_share.py` held
    `DOSES = (0.5, 1.0, 2.0)` for a day after the band moved, and would have gone
    on holding `(1.0, 3.0, 5.0)` just as quietly. This reads the declaration out
    of each script that carries one and compares it to BAND.
    """
    failures = []
    targets = {
        "reachable_share.py": r"^DOSES\s*=\s*\(([^)]*)\)",
        # ⚠️ Added 2026-08-26. `reachable_share_fila.py` is a one-line variant of
        # the above (it differs only in CUT_FRESH: 0.744495, the occupant reading
        # amended on 2026-08-18, against 0.7342). It carries its own DOSES
        # declaration and nothing was reading it. The sweep DID report it, as an
        # un-allowlisted quote of the superseded tuple inside its correction
        # comment — and the tempting fix, allowlisting the name, is exactly the
        # downgrade the `reachable_share.py` entry warns about: "not checked"
        # dressed as "checked a better way". So it gets the structural check
        # FIRST, and the allowlist entry only afterwards.
        "reachable_share_fila.py": r"^DOSES\s*=\s*\(([^)]*)\)",
    }
    for name, pattern in targets.items():
        path = root / name
        if not path.exists():
            failures.append(f"{name}: expected to be present and carry a band declaration")
            continue
        m = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
        if not m:
            failures.append(f"{name}: no band declaration found — did it move or get renamed?")
            continue
        declared = tuple(float(x) for x in m.group(1).split(",") if x.strip())
        if declared != BAND:
            failures.append(
                f"{name}: declares the band as {declared}, this file locks {BAND}"
            )
    return failures


# --- sizing, locked 2026-08-17 (amendment v1.11) ---------------------------
# These are not band-dependent, so they are checked by a separate pass. They are
# here because the defect that produced them is the same one this file exists to
# catch: `N` = 174 was a computed result quoted in prose across the package, and
# it stayed quoted after the formula that produced it was found to be wrong.
SIZING_INPUTS = dict(
    r_hat=29.838403, p0_hat=0.111813, icc=0.18141, mde=0.30,
    hours_per_epoch=5.1867, session_hours_per_epoch=50.4667, cv2=0.3833,
)
N_EPOCHS_LOCKED = 234
DESIGN_EFFECT_LOCKED = 13.482928
CV2_LOCKED = 0.3833
ALLOCATION_LOCKED = {"control": 117, "w2": 39, "w4": 39, "w7.5": 39}


def terceiro_eixo_check(root: Path) -> list[str]:
    """Trava o §5.7.2 aos dois artefatos que estiveram órfãos por três dias.

    A alegação é sobre uma ausência — "existe um terceiro eixo e não o medimos" — e
    ausência declarada precisa de teste que a proteja, senão fica indistinguível de
    esquecimento. É a mesma lição que o `top_chunk_ids` custou 3,3 meses.
    """
    a1 = root / "out" / "ancora-sem-exclusao.json"
    a2 = root / "out" / "ancora-sondas.json"
    if not a1.exists() or not a2.exists():
        return [f"{a1.name} / {a2.name}: um dos artefatos do terceiro eixo sumiu — a "
                f"tabela do §5.7.2 perdeu o lastro"]
    d1 = json.loads(a1.read_text(encoding="utf-8"))["ancora"]["publicada"]
    d2 = json.loads(a2.read_text(encoding="utf-8"))["ancora"]["publicada"]
    texto = (root / "MANUSCRIPT.md").read_text(encoding="utf-8")
    fails = []
    if d1 == d2:
        fails.append(
            "§5.7.2 afirma que a exclusão de sondas MOVE a âncora, mas os dois "
            "artefatos agora coincidem — o achado inverteu e o texto não acompanhou"
        )
    for pat, rot in (
        (rf"grupos de `last_served` distintos \| {d1['grupos_last_served']} \| "
         rf"\*\*{d2['grupos_last_served']}\*\*", "linha dos grupos"),
        (rf"posição do primeiro chunk do estudo \| {d1['posicao_primeiro_estudo']} \| "
         rf"\*\*{d2['posicao_primeiro_estudo']}\*\*", "linha da posição"),
    ):
        if not re.search(pat, texto):
            fails.append(f"§5.7.2: {rot} não casa com os artefatos (/{pat}/)")
    # o replay do teto TEM de continuar declarando que não excluiu sondas — se um dia
    # excluir, o §5.7.2 passa a mentir na direção oposta.
    porque = root / "out" / "porque-350-v3.json"
    if porque.exists():
        se = json.loads(porque.read_text(encoding="utf-8"))["procedencia"].get(
            "sondas_excluidas")
        if se:
            fails.append(
                f"§5.7.2 diz que o teto correu SEM excluir sondas, mas o artefato "
                f"declara {len(se)} excluída(s) — o eixo deixou de ser não-medido"
            )

    # ── o par pareado que mediu o eixo no teto (30/08) ──────────────────────
    # ⚠️ O que este bloco protege NÃO é só o número: é o PAREAMENTO. Um par cujos
    # braços diferem em mais de uma coisa produz uma diferença inatribuível com
    # aparência de achado — e havia um exemplo vivo neste repositório. O par
    # `campo-churn` sugeria "fidelidade cai de 0,909 a 0" e é inutilizável: os dois
    # braços saíram de VERSÕES DIFERENTES do script, 98 segundos de intervalo, e o
    # único sinal foi um campo de procedência AUSENTE de um lado. Por isso o guarda
    # exige que a procedência difira em exatamente dois campos, nomeados.
    n1 = root / "out" / "CEILING-PROBE-EXCLUSION-none-2026-08-30.json"
    n2 = root / "out" / "CEILING-PROBE-EXCLUSION-probes-2026-08-30.json"
    if not n1.exists() or not n2.exists():
        fails.append(
            "§5.7.2: o par pareado da exclusão de sondas sumiu — a tabela 17/13 e a "
            "afirmação de que o teto cai voltam a ser prosa sem artefato")
        return fails
    A = json.loads(n1.read_text(encoding="utf-8"))
    B = json.loads(n2.read_text(encoding="utf-8"))
    pa, pb = A["procedencia"], B["procedencia"]
    difs = sorted(k for k in set(pa) | set(pb) if str(pa.get(k)) != str(pb.get(k)))
    if difs != ["gerado_em", "sondas_excluidas"]:
        fails.append(
            f"§5.7.2: os dois braços diferem em {difs} — o pareamento exige que só "
            f"`gerado_em` e `sondas_excluidas` difiram; qualquer outro campo torna a "
            f"diferença inatribuível, como no par `campo-churn`")
    # o braço de controle TEM de reproduzir o valor publicado; sem isso a comparação
    # com os 4,86% é entre corpora, não entre convenções.
    ta, tb = A["dose"]["tabela"][0], B["dose"]["tabela"][0]
    if ta["mexeu"] != 17 or ta["estados"] != 350:
        fails.append(
            f"§5.7.2: o braço SEM exclusão dá {ta['mexeu']}/{ta['estados']}, e o "
            f"publicado é 17/350 — o controle de reprodução falhou, então a diferença "
            f"volta a ser atribuível ao corpus tanto quanto às sondas")
    if tb["mexeu"] != 13:
        fails.append(f"§5.7.2: braço COM exclusão dá {tb['mexeu']}/350, texto afirma 13")
    for alvo, rot in (("3,71", "teto sob exclusão"), ("4,86", "teto publicado")):
        if alvo not in texto:
            fails.append(f"§5.7.2: {rot} ({alvo}%) ausente do texto")
    # ⚠️ O achado mais forte é a NÃO-ANINHAÇÃO: de 17 e 13 estados sensíveis, só 1 é
    # comum. Quem comparasse apenas os totais leria "quatro a menos" e concluiria que a
    # convenção quase não importa. Se um dia os conjuntos passarem a se aninhar, o
    # parágrafo que diz "reorganiza quase inteiramente" fica falso e nada acusaria.
    ma = {r["ts"] for r in A["dose"]["detalhe"] if r.get("churn", 0) > 0}
    mb = {r["ts"] for r in B["dose"]["detalhe"] if r.get("churn", 0) > 0}
    if len(ma & mb) > 3:
        fails.append(
            f"§5.7.2 afirma que os conjuntos sensíveis quase não se sobrepõem, mas "
            f"agora {len(ma & mb)} dos {len(ma)}/{len(mb)} são comuns — o achado da "
            f"não-aninhação enfraqueceu e o texto não acompanhou")
    # os 350 estados TÊM de ser os mesmos, ou não há pareamento nenhum
    if [r["ts"] for r in A["dose"]["detalhe"]] != [r["ts"] for r in B["dose"]["detalhe"]]:
        fails.append("§5.7.2: os 350 estados diferem entre os braços — não é um par")
    return fails


def censos_check(root: Path) -> list[str]:
    """Roda os censos mecânicos e propaga a falha deles.

    ⚠️ Estes existem porque revisão adversarial e censo mecânico pegam classes
    **disjuntas**, e seis rodadas do primeiro tinham sido feitas contra quase nada do
    segundo. As duas classes que reincidiram — verbo de entrega aplicado à intervenção,
    e rótulo que nomeia população maior do que mede — são exatamente as que revisão não
    pega de forma confiável: elas vivem no que o arco *sugere*, não no que a frase
    afirma, e sobreviveram a cinco leituras cada.

    O `registro_check` garante que um guarda definido está sendo chamado; este garante
    que os censos, que vivem fora do `claims_check`, entram no mesmo veredito.
    """
    fails = []
    for script, o_que in (
        ("censo-vocabulario-de-serving.py",
         "verbo de entrega aplicado à intervenção (o paper corre em shadow)"),
        ("censo-de-rotulos-de-populacao.py",
         "rótulo que nomeia população maior do que a que mede"),
        # ⚠️ Terceiro censo, e o que motivou os outros dois a existirem: artefato
        # medido, gravado e NUNCA LIDO. Nenhuma revisão pega isto — para notar a
        # ausência de uma leitura seria preciso lembrar de algo que não está no texto.
        # Foi assim que um TERCEIRO eixo de sensibilidade do teto ficou três dias
        # invisível dentro de `ancora-sondas.json` (§5.7.2).
        ("auditoria-da-cadeia.py",
         "artefato medido e nunca lido, ou citado e ausente do disco"),
        # ⚠️ Quarto censo (30/08), no eixo que os três anteriores não cobrem: a
        # ADJACÊNCIA. Os outros julgam uma frase de cada vez — rótulo contra
        # predicado, verbo contra objeto, artefato contra leitura. Este julga o
        # PARÁGRAFO, porque há um defeito que só existe entre duas frases ambas
        # corretas: `2,66%` (só o brief) encostado em `83,78%` (brief ∪ busca).
        # Nenhuma das duas mente, e a diferença entre elas não significa nada.
        # Sobreviveu a cinco revisões adversariais porque revisor lê frase a frase.
        ("censo-de-universos-no-paragrafo.py",
         "dois percentuais de superfícies diferentes sem fronteira declarada"),
    ):
        p = root / "measurement" / script
        if not p.exists():
            fails.append(f"{script} ausente — o censo que vigia «{o_que}» não roda")
            continue
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True)
        if r.returncode != 0:
            primeira = (r.stderr.strip().splitlines() or ["(sem diagnóstico)"])[0]
            fails.append(f"{script} saiu {r.returncode}: {primeira[:180]}")
    return fails


def contrafactual_check(root: Path) -> list[str]:
    """Trava a tabela do contrafactual do topo (§5) ao artefato.

    A alegação que ela sustenta é a mais causal do paper — "o topo do brief é
    DETERMINADO pelo tráfego de busca de meses atrás" — e ela só se sustenta porque as
    posições mudam de 2/3/5 para 131/129/128 quando o componente de acesso é zerado.
    Se o artefato mudar e as posições convergirem, a palavra "determinado" deixa de
    valer e o texto tem de acusar.
    """
    art = root / "out" / "TOP-COUNTERFACTUAL-2026-08-29.json"
    if not art.exists():
        return [f"{art.name} ausente — a alegação causal do §5 perdeu o contrafactual"]
    d = json.loads(art.read_text(encoding="utf-8"))
    texto = (root / "MANUSCRIPT.md").read_text(encoding="utf-8")
    fails = []
    if d.get("veredito") != "DETERMINA":
        fails.append(
            f"§5: o contrafactual devolve veredito {d.get('veredito')!r} e o texto diz "
            f"'determinado' — a alegação causal deixou de estar sustentada"
        )
    for l in d["detalhe"]:
        alvo = (rf"\| {l['chunk_id']} \|[^|]*\|[^|]*\|[^|]*{l['access_count']}[^|]*\| "
                rf"\*\*{l['posicao_com_acesso']}\*\* \| \*\*"
                rf"{l['posicao_sem_acesso']}\*\* \|")
        if not re.search(alvo, texto):
            fails.append(
                f"§5: a linha do chunk {l['chunk_id']} deveria ler acessos="
                f"{l['access_count']}, posição {l['posicao_com_acesso']} → "
                f"{l['posicao_sem_acesso']} — não casa ancorada ao id"
            )
    # o número de comparação que dá força ao argumento
    if f"{d['candidatos_servidos_na_janela']} chunks servidos na janela" not in texto:
        fails.append(
            f"§5: a população do contrafactual ({d['candidatos_servidos_na_janela']} "
            f"chunks servidos na janela) não está declarada — sem ela as posições não "
            f"têm denominador"
        )
    return fails


def catalogo_check(root: Path) -> list[str]:
    """Conta as duas tabelas do catálogo de defeitos e trava as menções ao total.

    ⚠️ Achado de revisão adversarial (Grok, 29/08): o texto dizia "16 defeitos, sete
    deles alterando um número" em cinco lugares, enquanto a tabela do §6 já tinha
    **oito** linhas e o Apêndice E, nove — 17 no total. Uma entrada foi acrescentada
    sem que os contadores acompanhassem, que é o destino de toda contagem escrita à
    mão num documento vivo.

    Este guarda conta as linhas e exige que o texto concorde. É o tipo de verificação
    que não precisa de artefato: a fonte da verdade é o próprio documento.
    """
    doc = (root / "MANUSCRIPT.md").read_text(encoding="utf-8")

    def linhas_de(inicio: str, fim: str) -> int:
        # ⚠️ `fim` procurado A PARTIR de `inicio`: buscá-lo do começo do documento
        # devolve a primeira ocorrência do delimitador, que está ANTES da seção, e o
        # guarda passa a reportar contagem negativa como se fosse divergência do
        # texto. Foi o que aconteceu na primeira versão, e o diagnóstico apontava
        # para o lugar errado.
        i = doc.find(inicio)
        j = doc.find(fim, i + len(inicio)) if i >= 0 else -1
        if i < 0 or j <= i:
            return -1
        return len([l for l in doc[i:j].splitlines()
                    if l.startswith("|") and not l.startswith("|---")
                    and "| número que ele mudou" not in l])

    n6 = linhas_de("## 6. Defeitos", "### 6.1")
    nE = linhas_de("As oito do §6 mais as nove abaixo", "\n## ") - 1  # menos o cabeçalho
    if n6 < 0:
        return ["§6: não encontrei os limites da tabela de defeitos"]
    total = n6 + nE
    por_extenso = {7: "sete", 8: "oito", 9: "nove", 10: "dez"}
    e6, eE = por_extenso.get(n6, str(n6)), por_extenso.get(nE, str(nE))
    fails = []
    for padrao, rotulo in (
        (rf"\*\*{total} defeitos que nós cometemos\*\*, {e6} deles", "§1: total e subtotal"),
        (rf"catálogo integral tem \*\*{total}\*\* entradas", "§6: catálogo integral"),
        (rf"as \*\*{e6} que mudaram um número", "§6: subtotal na abertura"),
        # ⚠️ o `**` fecha DEPOIS da frase, não depois do numeral — o padrão anterior
        # exigia `as **oito** que`, e o texto escreve `as **oito que mudaram ...**`.
        # Guarda com âncora errada não morde e não avisa: some do relatório.
        (rf"O padrão que atravessa as {e6},", "§6: 'atravessa as N'"),
        (rf"As {e6} do §6 mais as {eE} abaixo", "Apêndice E: a soma"),
    ):
        if not re.search(padrao, doc):
            fails.append(
                f"{rotulo} — a tabela do §6 tem {n6} entradas e o Apêndice E tem {nE} "
                f"({total} no total), e /{padrao}/ não casa. Contagem escrita à mão "
                f"desincronizou da tabela."
            )
    return fails


def registro_check(root: Path) -> list[str]:
    """Toda função `*_check` do arquivo tem de estar registrada no `main()`.

    ⚠️ Limite real do censo de cobertura, achado por mutação em 29/08: ele mede se o
    número aparece no **fonte** do verificador ou nos artefatos que ele lê, e não
    consegue ver a diferença entre um guarda que **existe** e um guarda que é
    **chamado**. Remover `failures.extend(eixo_check(...))` do `main()` deixa o censo
    inalterado e a proteção em zero — guarda órfão é indistinguível de guarda ativo
    para quem conta ocorrências de texto.

    Este guarda fecha exatamente esse buraco, e nada além dele: não afirma que as
    checagens são boas, só que nenhuma está desligada em silêncio.
    """
    fonte = (root / "claims_check.py").read_text(encoding="utf-8")
    definidas = set(re.findall(r"^def (\w+_check)\(", fonte, re.M))
    corpo_main = fonte.split("def main(")[-1]
    chamadas = set(re.findall(r"(\w+_check)\(Path\(args\.root\)\)", corpo_main))
    orfas = sorted(definidas - chamadas - {"registro_check"})
    if orfas:
        return [
            f"claims_check.py: {len(orfas)} guarda(s) definido(s) e NUNCA chamado(s) "
            f"no main: {orfas} — guarda órfão protege zero e não aparece em censo algum"
        ]
    return []


def cobertura_check(root: Path) -> list[str]:
    """Roda o censo de cobertura e exige que o paper declare a taxa que ele tem.

    Um paper que se apresenta como verificável precisa dizer **quanto** verifica. Sem
    isto, "cada alegação tem guarda" é afirmação sobre a intenção, não sobre o estado —
    e o estado, quando medido pela primeira vez (revisão adversarial do Codex, 29/08),
    era 59,4% das alegações numéricas sem guarda nenhuma.

    O guarda trava a taxa nos dois sentidos: se ela **piorar**, o texto passa a mentir;
    se **melhorar**, o texto está desatualizado para menos e a declaração tem de subir.
    """
    script = root / "measurement" / "censo-de-alegacoes-sem-guarda.py"
    if not script.exists():
        return [f"{script.name} ausente — a taxa de cobertura declarada não é medida"]
    proc = subprocess.run([sys.executable, str(script), "--json"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return [f"censo de cobertura saiu {proc.returncode}: {proc.stderr.strip()[:200]}"]
    c = json.loads(proc.stdout)
    texto = (root / "MANUSCRIPT.md").read_text(encoding="utf-8")
    pct = f"{c['pct_sem_guarda']:.1f}".replace(".", ",")
    n = c["contagem"].get("SEM_GUARDA", 0)
    if not re.search(rf"\*\*{n} das {c['alegacoes_curadas']}[^*.]*(?:\*\*)?[^.]*?"
                     rf"{re.escape(pct)}%", texto):
        return [
            f"§ metodologia: o censo mede {n}/{c['alegacoes_curadas']} sem guarda "
            f"({pct}%) e o texto não declara esse par — uma taxa de cobertura não "
            f"declarada é a alegação mais fácil de deixar envelhecer"
        ]
    return []


def superficie_check(root: Path) -> list[str]:
    """Ancora os números do §1/§4.1 ao artefato da superfície, e RECOMPUTA os derivados.

    ⚠️ Este guarda existe porque a sua ausência custou um erro publicável. O manuscrito
    afirmava **583.973** slots em cinco lugares; o artefato diz **583.763**. Um dígito,
    nenhum artefato com o valor do texto, e nada que acusasse — o número mais citado do
    paper (é a base da tese de capacidade) era o menos protegido.

    ⚠️ E o campo se chama `slots_historicos_ATE_AGORA_serie_viva`: a grandeza **cresce**
    ~7.500/dia. Hoje a série viva vale 591.323. Citar a série sem fixar o instante é
    escrever um número que envelhece para falso sozinho — por isso o `T_REF` do artefato
    é parte da alegação, e o texto tem de dizer os 84,7 dias.

    Os derivados (8,7× e 2,66%) são **recomputados**, não ancorados: ancorar confere que
    o texto não mudou, recomputar confere que ele é aritmeticamente consistente com o
    resto. Foi a segunda que faltou.
    """
    art = root / "out" / "superficie.json"
    doc = root / "MANUSCRIPT.md"
    if not art.exists():
        return [f"{art.name} ausente — os números do §1 não têm artefato"]
    d = json.loads(art.read_text(encoding="utf-8"))
    texto = doc.read_text(encoding="utf-8")
    fails = []
    cum, conc = d["cumulativo_exato"], d["concentracao_do_brief"]
    corpus = d["corpus"]

    def mil(n: int) -> str:
        return f"{n:,}".replace(",", ".")

    # (1) valores diretos, ancorados ao rótulo que os identifica
    for padrao, rotulo, valor in (
        (rf"\*\*{mil(conc['slots_historicos_ATE_AGORA_serie_viva'])} slots\*\*",
         "slots acumulados", conc["slots_historicos_ATE_AGORA_serie_viva"]),
        (rf"Serviu \*\*{mil(cum['brief'])}\s*\n?distintos", "distintos no brief", cum["brief"]),
        (rf"exposto na busca \(histórico\) \| {mil(cum['busca'])}", "expostos na busca", cum["busca"]),
        (rf"\*\*apagados depois\*\* \| {cum['servidos_no_brief_e_depois_apagados']}",
         "servidos e apagados", cum["servidos_no_brief_e_depois_apagados"]),
        (rf"top-10 leva \*\*{str(conc['pct_top10']).replace('.', ',')}%\*\*",
         "fração do top-10", conc["pct_top10"]),
        (rf"{mil(conc['briefs_7d'])} briefs da semana", "briefs na janela", conc["briefs_7d"]),
    ):
        if not re.search(padrao, texto):
            fails.append(
                f"§1/§4.1: {rotulo} deveria ler {valor} ancorado ao rótulo "
                f"(/{padrao}/ não casa) — texto e artefato divergiram"
            )

    # (2) derivados: RECOMPUTAR, e travar a CONTAGEM de ocorrências.
    # ⚠️ `re.search` e `in texto` são satisfeitos por UMA ocorrência: três mutações
    # de 29/08 passaram porque o valor aparece 2–6 vezes e eu havia mutado só a
    # primeira. É o mesmo defeito que `ocorrencias()` documenta no `delta_cut_check`,
    # e ele reapareceu aqui porque a classe não fica consertada onde foi achada.
    # Custo assumido: edição legítima que mude o número de menções atualiza a
    # contagem aqui, de propósito.
    # ⚠️ Atualizado DE PROPÓSITO em 29/08: a §6.1 nova cita `583.763` e `2,66%` mais
    # uma vez cada, ao explicar o erro que a falta de guarda produziu.
    # ⚠️ "8,7 vezes" subiu para 3 em 30/08 (achado Codex): o §9 dizia "capacidade para
    # mostrar tudo NOVE vezes", e 583.763/67.187 = 8,69 — nove passagens exigiriam
    # 604.683 slots. Três lugares diziam nove; agora dizem o que a divisão dá.
    OCORRENCIAS = {"8,7 vezes": 3, "47,16%": 3, "2,66%": 5, "583.763": 7,
                   # ⚠️ +1 em 30/08: o §4.3.1 passou a citar 10.899 para OUTRA
                   # grandeza (chunks de `sessions/%` que passam o piso), cujo
                   # tamanho coincide com o da união viva neste instante. A
                   # colisão está declarada no texto; a contagem sobe de propósito.
                   # ⚠️ −1 em 30/08 (item B3): a ressalva "a busca é iniciada pelo
                   # agente" aparecia 5× no corpo; duas repetições viraram ponteiro
                   # ao §4.1.1, que é onde ela é o argumento e não a lembrança. A
                   # do §2 levava consigo a única menção a 10.899 daquele parágrafo.
                   # ⚠️ +2 em 30/08 (achado GLM): a remissão `↩ H-3.2` ficara vazia no
                   # ponto de uso — "a linha dos 152 é o que faz a ponte" sem dizer
                   # ponte entre o quê. A reconciliação `11.051 − 152 = 10.899` e
                   # `67.187 − 10.899 = 56.288` voltou para o corpo.
                   "10.899": 12}

    def conta(literal: str, rotulo: str) -> None:
        esperado = OCORRENCIAS.get(literal)
        visto = texto.count(literal)
        if esperado is None:
            fails.append(f"{rotulo}: {literal!r} sem contagem declarada neste guarda")
        elif visto != esperado:
            fails.append(
                f"§1/§4.1: {rotulo} — {literal!r} aparece {visto}× e deveria aparecer "
                f"{esperado}×; ou uma ocorrência divergiu, ou foi removida"
            )

    mult = conc["slots_historicos_ATE_AGORA_serie_viva"] / corpus
    conta(f"{mult:.1f}".replace(".", ",") + " vezes", "slots/corpus recomputado")
    pct = 100 * cum["brief"] / corpus
    conta(f"{pct:.2f}".replace(".", ",") + "%", "cobertura do brief recomputada")
    conta(mil(conc["slots_historicos_ATE_AGORA_serie_viva"]), "slots acumulados")
    conta(str(conc["pct_top10"]).replace(".", ",") + "%", "fração do top-10")

    # (3) a união viva, que é a linha que fecha a tabela do §4.1 em um universo
    viva = cum["uniao"] - cum["servidos_no_brief_e_depois_apagados"]
    if viva + cum["nenhuma_superficie"] != corpus:
        fails.append(
            f"§4.1: {viva} + {cum['nenhuma_superficie']} != {corpus} — a tabela deixou "
            f"de fechar num universo só"
        )
    conta(mil(viva), "união viva recomputada")
    return fails


def eixo_check(root: Path) -> list[str]:
    """Trava a tabela do vazio no eixo de tamanho (§4.2) contra o artefato.

    A conclusão que ela sustenta — "×0,38 por década interpola numa faixa sem
    observação" — depende de UM fato: a faixa 100–1.000 estar vazia. O script de
    medição já aborta se ela deixar de estar; aqui o que se trava é que o documento
    não continue afirmando o vazio depois disso.
    """
    art = root / "out" / "SIZE-AXIS-GAP-2026-08-29.json"
    doc = root / "MANUSCRIPT.md"
    if not art.exists():
        return [f"{art.name} ausente — a tabela do vazio no §4.2 não tem artefato"]
    d = json.loads(art.read_text(encoding="utf-8"))
    texto = doc.read_text(encoding="utf-8")
    fails = []
    if d["tipos_na_faixa_intermediaria"] != 0:
        fails.append(
            f"§4.2: o artefato tem {d['tipos_na_faixa_intermediaria']} tipo(s) na faixa "
            f"intermediária — 'duas nuvens' deixou de valer e o texto ainda afirma"
        )
    dec = str(d["maior_lacuna"]["decadas"]).replace(".", ",")
    pct = str(d["pct_da_amplitude_sem_ponto"]).replace(".", ",")
    for padrao, rotulo in (
        (rf"maior lacuna no eixo[^|]*\|[^|]*\*\*{re.escape(dec)} décadas\*\*, entre "
         rf"`{d['maior_lacuna']['de']['tipo']}` \({d['maior_lacuna']['de']['n']}\)",
         f"maior lacuna ({dec} décadas)"),
        (rf"\*\*{re.escape(pct)}%, sem um único ponto\*\*",
         f"fração da amplitude ({pct}%)"),
        (rf"100 ≤ n < 1\.000 \| \*\*{d['tipos_na_faixa_intermediaria']}\*\*",
         "faixa intermediária vazia"),
        (rf"tipos com n < 100 \| \*\*{d['nuvem_pequenos']['tipos']}\*\* "
         rf"\(de {d['nuvem_pequenos']['n_min']} a {d['nuvem_pequenos']['n_max']}\)",
         "nuvem dos pequenos"),
        (rf"tipos com n ≥ 1\.000 \| \*\*{d['nuvem_grandes']['tipos']}\*\* "
         rf"\(de 1\.046 a 32\.920\)", "nuvem dos grandes"),
    ):
        if not re.search(padrao, texto):
            fails.append(
                f"§4.2: {rotulo} não casa ancorado ao seu rótulo (/{padrao}/) — "
                f"a tabela do vazio divergiu do artefato"
            )
    return fails


def estimando_check(root: Path) -> list[str]:
    """Trava o registro prospectivo do estimando aos artefatos que o sustentam.

    O documento é escrito **antes** do Epoch 1 e a sua função é ser conferível depois.
    Duas classes de defeito o tornariam inútil, e as duas já ocorreram neste projeto:

    1. **transcrição que envelhece** — o §1 copia desfecho, τ, `N` e estimador do
       pré-registro. Cópia sem guarda é cache sem invalidação, e foi assim que o
       `583.973` viveu cinco lugares;
    2. **a aritmética da condição de detectabilidade** — o §2 afirma que a dose que
       testa H1 altera 3,14% dos briefs e que isso exige ~10× de concentração contra um
       MDE de 30%. Os dois números são **derivados**, não citados: se a tabela de dose
       mudar, a condição inteira muda e o texto seguiria afirmando a antiga.

    ⚠️ O §2 é a parte do documento que pode reprovar o desenho antes de ele começar. É
    justamente a que não pode depender da minha memória da tabela.
    """
    doc = root / "PROSPECTIVE-ESTIMAND-2026-08-30.md"
    if not doc.exists():
        return ["PROSPECTIVE-ESTIMAND-2026-08-30.md ausente — o Paper B perde o "
                "documento que declara o estimando antes do primeiro epoch"]
    texto = doc.read_text(encoding="utf-8")
    fails = []

    art = root / "out" / "dose-350-v3.json"
    if not art.exists():
        return [f"{art.name} ausente — a condição de detectabilidade do §2 fica sem lastro"]
    tab = {str(r["w"]): r for r in json.loads(art.read_text(encoding="utf-8"))["dose"]["tabela"]}

    # (1) a dose primária e o teto, recomputados da tabela
    if "2" not in tab or "7.5" not in tab:
        return [f"{art.name}: doses 2 e 7.5 ausentes da tabela — o §2 as cita"]
    d2, d75 = tab["2"], tab["7.5"]
    pct2 = 100 * d2["mexeu"] / d2["estados"]
    pct75 = 100 * d75["mexeu"] / d75["estados"]
    if f"{d2['mexeu']}/{d2['estados']}" not in texto:
        fails.append(f"§2: a dose w=2 altera {d2['mexeu']}/{d2['estados']} briefs e o "
                     f"registro não afirma essa fração")
    if f"{pct2:.2f}".replace(".", ",") not in texto:
        fails.append(f"§2: {pct2:.2f}% (dose primária) ausente do registro")
    if f"{pct75:.2f}".replace(".", ",") not in texto:
        fails.append(f"§2: {pct75:.2f}% (teto do canal) ausente do registro")

    # (2) ⚠️ o argumento SÓ vale enquanto a dose máxima do estudo estiver NO teto. Se
    #     uma dose do estudo passasse a mover mais que o teto medido, a frase "a revisão
    #     teria de mudar o canal, não a dose" ficaria falsa — e é dela que sai a
    #     consequência 3, a única que pode barrar o Epoch 1.
    teto = max(r["mexeu"] for r in tab.values())
    if d75["mexeu"] != teto:
        fails.append(
            f"§2: a dose máxima do estudo (w=7,5) move {d75['mexeu']}, e o teto da "
            f"tabela é {teto} — o registro afirma que nenhuma dose ultrapassa o teto, "
            f"e essa frase sustenta a consequência que pode barrar o Epoch 1")

    # (3) a concentração exigida é MDE ÷ fração alterada, recomputada
    conc = 30.0 / pct2
    if f"{conc:.0f}×" not in texto and f"{conc:.1f}" not in texto:
        fails.append(f"§2: a concentração exigida é {conc:.2f}× (MDE 30% ÷ {pct2:.2f}%) "
                     f"e o registro não a afirma")

    # (4) transcrições que o §1 declara serem cópia — divergir delas é defeito do
    #     documento, e ele diz isso de si mesmo
    pre = root / "PREREG-DRAFT.md"
    if pre.exists():
        p = pre.read_text(encoding="utf-8")
        for valor, rot in (("234", "N_epochs"), ("117/39/39/39", "alocação"),
                           ("323 days", "cap de calendário")):
            if valor in p and valor.replace(" days", " dias") not in texto and valor not in texto:
                fails.append(f"§1/§4: {rot} = «{valor}» está no PREREG e não no registro")
    # (5) 🔴 a concentração medida, e o que a torna frágil. O §2-bis afirma que o
    #     agregado passa a faixa mas repousa numa assinatura; se a decomposição mudar,
    #     a leitura inteira muda e o texto seguiria afirmando a antiga. Este é o guarda
    #     que impede a leitura conveniente de sobreviver a um corpus novo.
    conc = root / "out" / "CONCENTRATION-2026-08-30.json"
    if conc.exists():
        c = json.loads(conc.read_text(encoding="utf-8"))
        lou = c.get("leave_one_signature_out") or {}
        for got, alvo, rot in (
                (c.get("concentracao_LIMITE_SUPERIOR"), 12.74, "concentração nominal"),
                (lou.get("concentracao_sem_ela"), 0.79, "concentração sem a maior"),
                (round(100 * c.get("cobertura", 0), 1), 40.0, "cobertura")):
            if got is None or abs(got - alvo) > 0.051:
                fails.append(f"§2-bis: {rot} = {got}, o registro afirma {alvo}")
        share = lou.get("share_das_cobertas")
        if share is None or share < 0.80:
            fails.append(
                f"§2-bis afirma que a concentração repousa numa assinatura "
                f"({share} do total), e essa é a base para ler o resultado como "
                f"reprovado na substância — se a dependência caiu, a leitura muda")
        if "0,79" not in texto or "12,74" not in texto:
            fails.append("§2-bis: a concentração nominal e a do leave-one-out têm de "
                         "aparecer JUNTAS no texto — citar só uma é a leitura seletiva "
                         "que o parágrafo existe para impedir")
    elif "12,74" in texto:
        fails.append("§2-bis cita a concentração e out/CONCENTRATION-2026-08-30.json "
                     "não existe — a pré-condição do Epoch 1 ficou sem lastro")

    # (6) 🔴 a decisão C e a potência de H1c. O que este bloco protege é a
    #     TRIPLA de números que torna a decisão legível: o MDE que o N sustenta, o
    #     efeito necessário no cenário otimista, e o do pessimista. Citar só o
    #     otimista seria exatamente a leitura seletiva que a decisão evita.
    pw = root / "out" / "H1C-POWER-2026-08-30.json"
    rev = root / "DESIGN-REVISION-2026-08-30.md"
    if pw.exists() and rev.exists():
        h = json.loads(pw.read_text(encoding="utf-8"))
        r = rev.read_text(encoding="utf-8")
        cen = h.get("cenarios", {})
        otim = cen.get("todas as cobertas", {})
        pess = cen.get("só as informativas", {})
        # o argumento inteiro é "H1 impossível, H1c possível" — se isso inverter, o
        # documento passa a recomendar uma opção que a própria medição derrubou.
        if not otim.get("possivel"):
            fails.append("§3-ter: H1c deixou de ser alcançável no cenário otimista — a "
                         "opção C perdeu a sua única justificativa")
        if pess.get("possivel"):
            fails.append("§3-ter: o cenário pessimista virou possível — o par de "
                         "cenários deixou de discriminar e a ressalva perdeu sentido")
        if h.get("comparacao_com_h1_incondicional", {}).get("possivel"):
            fails.append("§3-ter: H1 incondicional consta como possível — a revisão "
                         "inteira parte de ela não ser")
        for val, rot in ((f"{100*h.get('mde_relativo_h1c', 0):.1f}", "MDE de H1c"),
                         (f"{100*otim.get('efeito_necessario_nas_cobertas', 0):.0f}",
                          "efeito no cenário otimista")):
            if val.replace(".", ",") not in r:
                fails.append(f"§3-ter: {rot} = {val}% não aparece na revisão")

    # (6-bis) o §3-bis promove H1c a PRIMÁRIA, e a tabela dele tem sete números que
    #     vêm de dois artefatos. Transcritos à mão, eles são exatamente a classe do
    #     §4.2 — três coeficientes que viveram no stdout por quatro dias. Aqui cada um
    #     é RECOMPUTADO e ancorado ao seu rótulo, e a decisão de parada (~20% de
    #     cobertura) é recomputada da aritmética, não lida do texto.
    for nome, chaves in (
        ("out/H1C-BASE-RATE-2026-08-30.json",
         (("p0", "{:.4f}", r"\*\*0,0782\*\*"),
          ("oportunidades_por_dia.mediana", "{:.0f}", r"\*\*213\*\*"))),
        ("out/H1C-POWER-2026-08-30.json",
         (("design_effect", "{:.2f}", r"\*\*21,87\*\*"),
          ("n_efetivo_por_braco", "{:,.0f}", r"\*\*1\.139\*\*"),
          ("mde_relativo_h1c", "{:.3f}", r"\*\*36,7%\*\*"),
          ("cenarios.todas as cobertas.efeito_necessario_nas_cobertas",
           "{:.3f}", r"\*\*91,7%\*\*"))),
    ):
        art = root / nome
        if not art.exists():
            fails.append(f"{art.name} ausente — o §3-bis promove H1c sem artefato")
            continue
        a = json.loads(art.read_text(encoding="utf-8"))
        for caminho, _fmt, padrao in chaves:
            v = a
            for parte in caminho.split("."):
                v = v[parte] if isinstance(v, dict) else None
                if v is None:
                    break
            if v is None:
                fails.append(f"{art.name}: chave {caminho!r} sumiu — o §3-bis cita um "
                             f"número que o artefato não tem mais")
                continue
            if not re.search(padrao, texto):
                fails.append(
                    f"§3-bis: {caminho} = {v} não aparece ancorado (/{padrao}/ não "
                    f"casa) — o registro prospectivo divergiu do artefato"
                )
    # a folga de 8,3 pontos e o limiar de parada são DERIVADOS: recomputá-los é o que
    # impede que uma reedição do texto mude a conclusão sem mudar a medição.
    hp = root / "out" / "H1C-POWER-2026-08-30.json"
    if hp.exists():
        h = json.loads(hp.read_text(encoding="utf-8"))
        cen = h.get("cenarios", {}).get("todas as cobertas", {})
        exigido = cen.get("efeito_necessario_nas_cobertas")
        cob = cen.get("cobertura")
        if exigido is not None:
            folga = f"{100 * (1 - exigido):.1f}".replace(".", ",")
            if not re.search(rf"\*\*{re.escape(folga)} pontos\*\*", texto):
                fails.append(
                    f"§3-bis: a folga recomputa {folga} pontos e o texto não diz isso "
                    f"ancorado — a conclusão 'apertada' perdeu o seu número"
                )
        # limiar de parada: o exigido é `MDE / cobertura`, logo cruza 100% quando a
        # cobertura cai ao próprio MDE. ⚠️ A primeira redação do §3-bis dizia "~20%",
        # escrito sem derivar; este guarda o derrubou na primeira execução. Não afrouxar
        # para uma faixa — é o valor exato que decide encerrar o braço.
        if exigido and cob:
            limiar = f"{100 * cob * exigido:.1f}".replace(".", ",")
            if not re.search(rf"abaixo de \*\*{re.escape(limiar)}%\*\*", texto):
                fails.append(
                    f"§3-bis: o limiar de parada recomputa {limiar}% e o texto não o diz "
                    f"ancorado — a regra de parada divergiu da aritmética que a gera"
                )
            margem = f"{100 * (cob - cob * exigido):.1f}".replace(".", ",")
            if not re.search(rf"\*\*{re.escape(margem)} pontos de\s*\n?cobertura\*\*",
                             texto):
                fails.append(
                    f"§3-bis: a margem até o limiar recomputa {margem} pontos de "
                    f"cobertura e o texto não diz isso ancorado"
                )

    # (6-ter) o §4 afirmava que o churn do shadow era ZERO, "porque sem seed no ambiente
    #     o mapa de boost sai vazio". Medido em 30/08: 151/4.037 = 3,74% na janela
    #     fechada, e `designated_ids` não-vazio em 1.344 de 1.344 decisões. A afirmação
    #     envelheceu quando a seed entrou no ambiente e ninguém a revisitou. Aqui ela é
    #     ancorada ao artefato — e o guarda proíbe que a versão "é zero" volte.
    art = root / "out" / "SHADOW-CHURN-2026-08-30.json"
    if not art.exists():
        fails.append(f"{art.name} ausente — o §4 volta a afirmar o churn sem artefato")
    else:
        s = json.loads(art.read_text(encoding="utf-8"))
        taxa = f"{100 * s['taxa_churn']:.2f}".replace(".", ",")
        alvo = (rf"\*\*{s['com_churn']:,}".replace(",", r"\.") +
                rf" de {s['decisoes']:,}".replace(",", r"\.") +
                rf" = {re.escape(taxa)}%\*\*")
        if not re.search(alvo, texto):
            fails.append(
                f"§4: o churn do shadow recomputa {s['com_churn']} de {s['decisoes']} "
                f"= {taxa}% e o texto não diz isso ancorado (/{alvo}/ não casa)"
            )
        if re.search(r"`churn` do \*shadow\* é \*\*zero\*\*", texto):
            fails.append(
                "§4: a afirmação 'o churn do shadow é zero' voltou ao texto — ela é "
                "falsa desde que a designação entrou no ambiente (out/SHADOW-CHURN)"
            )

    # (7) precedência: o documento afirma zero epochs randomizados. Se o ASSIGNMENT
    #     passar a existir, a afirmação de precedência envelheceu e o documento deixa
    #     de ser prospectivo — que é a única propriedade que o torna valioso.
    if (root / "ASSIGNMENT.json").exists() and "zero epochs randomizados" in texto:
        fails.append(
            "PROSPECTIVE-ESTIMAND: afirma 'zero epochs randomizados existentes' e "
            "ASSIGNMENT.json já existe — a alegação de precedência envelheceu")
    return fails


def sem_guarda_check(root: Path) -> list[str]:
    """Fecha as dez alegações que o censo de 30/08 achou circulando sem verificação.

    O censo `censo-de-alegacoes-sem-guarda.py` mediu **31,2%** das alegações numéricas
    do manuscrito sem nenhum guarda. Não é hipótese: duas alegações já envelheceram
    para falsas exatamente por isso (`583.973`, que nunca existiu em artefato nenhum, e
    os `205` caracteres atribuídos à população errada). Um número sem guarda é uma
    aposta em que ninguém vai reeditar o script que o produziu.

    Três origens distintas, e a distinção importa porque o remédio difere:

    | origem | alegações | como se verifica |
    |---|---|---|
    | derivável de números já travados | 99,98% · 8,7 · 2,66% · 46.280 · 82,2% | recomputar aqui |
    | artefato existente e nunca lido | 0,161% · 12,4 · 4,86% · 36% · 80% · 32,1% · 232 | abrir e comparar |
    | artefato que NÃO EXISTIA | −0,961 · −0,728 · 0,471 | o script não gravava nada |

    🔴 A terceira linha é a mais séria e foi descoberta ao escrever este guarda.
    `robustez-tamanho-exposicao.py` rodou de 27/08 a 30/08 **sem gravar artefato**: os
    coeficientes que sustentam o §4.2 inteiro — inclusive o `β` que é o resultado que
    SOBREVIVE aos 15 tipos — existiam só no `stdout`, foram lidos por um humano e
    transcritos à mão. Trocar o CSV de entrada mudaria os três, e o texto seguiria
    afirmando os antigos sem que nada acusasse. O `--out` foi acrescentado em 30/08 e
    `out/SIZE-ROBUSTNESS-2026-08-30.json` é o primeiro artefato que eles têm.
    """
    doc = root / "MANUSCRIPT.md"
    if not doc.exists():
        return ["MANUSCRIPT.md ausente"]
    texto = doc.read_text(encoding="utf-8")
    fails = []

    def afirma(s: str) -> bool:
        return s in texto

    # ── (a) deriváveis: recomputadas, não copiadas ──────────────────────────
    SLOTS, CORPUS, DISTINTOS = 583_763, 67_187, 1_787
    NUNCA, PISO_NUNCA = 56_288, 10_008

    cap = SLOTS / CORPUS                                   # 8,688…
    if not afirma(f"{cap:.1f}".replace(".", ",")):
        fails.append(f"capacidade: {SLOTS}/{CORPUS} = {cap:.1f}× e o texto não afirma")
    cob = 100 * DISTINTOS / CORPUS                          # 2,659…
    if not afirma(f"{cob:.2f}".replace(".", ",")):
        fails.append(f"cobertura do brief: {cob:.2f}% ausente do texto")
    # cobertura esperada se os mesmos slots fossem sorteados uniformemente
    unif = 100 * (1 - (1 - 1 / CORPUS) ** SLOTS)             # 99,983…
    if not afirma(f"{unif:.2f}".replace(".", ",")):
        fails.append(
            f"contrafactual uniforme: 1−(1−1/{CORPUS})^{SLOTS} = {unif:.2f}% e o texto "
            f"não afirma — é o limite superior que dá sentido ao 2,66%")
    abaixo = NUNCA - PISO_NUNCA                             # 46.280
    if not afirma(f"{abaixo:,}".replace(",", ".")):
        fails.append(f"nunca expostos abaixo do piso: {NUNCA}−{PISO_NUNCA} = {abaixo}")
    frac = 100 * abaixo / NUNCA                             # 82,22…
    if not afirma(f"{frac:.1f}".replace(".", ",")):
        fails.append(f"fração abaixo do piso: {frac:.1f}% ausente do texto")

    # ── (b) artefatos que existiam e ninguém abria ──────────────────────────
    def art(rel: str):
        p = root / rel
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    pool = art("POOL-ELEGIVEL-2026-08-28.json")
    if pool is None:
        fails.append("POOL-ELEGIVEL-2026-08-28.json ausente — o pool de 108 fica sem lastro")
    else:
        for campo, esperado, rot in (("pool_elegivel", 108, "pool elegível"),
                                     ("pct_do_corpus", 0.161, "pool como % do corpus"),
                                     ("slots_por_candidato", 12.4, "slots por candidato")):
            if pool.get(campo) != esperado:
                fails.append(f"pool: artefato diz {campo}={pool.get(campo)}, "
                             f"manuscrito afirma {esperado} ({rot})")

    gran = art("CEILING-GRANULARITY-2026-08-28.json")
    if gran is None:
        fails.append("CEILING-GRANULARITY-2026-08-28.json ausente — os tetos ficam sem lastro")
    else:
        tetos = {l["granularidade"]: l["teto_pct"] for l in gran["tabela"]}
        # ⚠️ O texto arredonda: 36,29→36%, 80,29→80%. O guarda compara o VALOR do
        # artefato com o arredondamento que o texto usa, não a string — comparar
        # string faria o guarda morder o arredondamento honesto.
        for g, alvo in (("seg", "4,86"), ("min", "36"), ("hora", "80")):
            if g not in tetos:
                fails.append(f"teto: granularidade '{g}' ausente do artefato")
            elif not afirma(alvo):
                fails.append(f"teto {g}: artefato diz {tetos[g]}%, texto não afirma {alvo}")
        if not (tetos.get("seg", 0) < tetos.get("min", 0) < tetos.get("hora", 0)):
            fails.append(f"teto: monotonia quebrada no artefato — {tetos}")

    lac = art("out/SIZE-AXIS-GAP-2026-08-29.json")
    if lac and lac.get("pct_da_amplitude_sem_ponto") != 32.1:
        fails.append(f"lacuna do eixo: artefato diz "
                     f"{lac.get('pct_da_amplitude_sem_ponto')}%, manuscrito afirma 32,1%")

    piso = art("out/FLOOR-COMPOSITION-2026-08-29.json")
    if piso:
        c = piso["tipo_dominante"]["comprimento_medio"]
        if round(c) != 232:
            fails.append(f"comprimento do subconjunto: artefato diz {c}, texto afirma 232")
        # ⚠️ o par que já produziu a atribuição à população errada em 29/08
        inteiro = piso["contraste_de_populacao"]["no_corpus_inteiro"]["comprimento_medio"]
        if abs(inteiro - 205.1) > 0.05:
            fails.append(f"contraste: média do tipo inteiro mudou para {inteiro} — o "
                         f"§4.1 contrasta 232 contra 205,1 e o contraste envelheceu")

    # ── (c) o artefato que não existia até 30/08 ────────────────────────────
    rob = art("out/SIZE-ROBUSTNESS-2026-08-30.json")
    if rob is None:
        fails.append(
            "out/SIZE-ROBUSTNESS-2026-08-30.json ausente — β, r e o EP jackknife do "
            "§4.2 voltam a ser prosa sem artefato, que é como estiveram de 27 a 30/08")
    else:
        b15 = rob["binomial"]["todos_15"]
        for got, alvo, rot in ((b15["beta_log10n"], -0.961, "β binomial, 15 tipos"),
                               (b15["ep_jackknife_sobre_tipos"], 0.471, "EP jackknife"),
                               (rob["correlacoes"]["pearson_13_publicados"], -0.728,
                                "Pearson, 13 publicados")):
            if abs(got - alvo) > 0.0005:
                fails.append(f"{rot}: artefato diz {got}, manuscrito afirma {alvo}")
        # o argumento do §4.2 é que o β sobrevive ao filtro e o r não; se isso
        # inverter, a seção inteira muda de conclusão e o número sozinho não acusa.
        if abs(rob["correlacoes"]["spearman_15_todos"]) > 0.15:
            fails.append(
                f"ρ Spearman subiu para {rob['correlacoes']['spearman_15_todos']} — o "
                f"§4.2 se apoia em ele ser desprezível (−0,098) para demover a "
                f"correlação em favor do β")
    return fails


def coorte_check(root: Path) -> list[str]:
    """Amarra a tabela de coortes do §4.1 ao artefato, e o §4.1 ao §5 pelo agregado.

    A tabela é prosa afirmando resultado calculado — sem guarda, é cache sem
    invalidação. Cada linha é ancorada ao RÓTULO da coorte, não solta no texto: o
    teste de mutação de 27/08 mostrou que valor sem âncora é satisfeito por qualquer
    ocorrência coincidente.

    ⚠️ O guarda que importa mais não é nenhuma linha da tabela: é a igualdade
    `nunca_expostos == 56.288`. O artefato usa a definição de exposição da UNIÃO das
    duas superfícies (brief ∪ `access_count > 0`); uma primeira versão do script
    contou só o brief e devolveu 97,57%, número correto para OUTRA grandeza. Travar o
    agregado contra a tabela do §4.1 faz o universo errado morder aqui, e não no
    parágrafo.
    """
    art = root / "out" / "EXPOSURE-BY-COHORT-2026-08-29.json"
    doc = root / "MANUSCRIPT.md"
    if not art.exists():
        return [f"{art.name} ausente — a tabela de coortes do §4.1 não tem artefato"]
    if not doc.exists():
        return ["MANUSCRIPT.md ausente"]
    d = json.loads(art.read_text(encoding="utf-8"))
    texto = doc.read_text(encoding="utf-8")
    fails = []

    # (1) o agregado do artefato TEM de ser o da tabela do §4.1 — universos comensuráveis
    if d["nunca_expostos"] != 56288 or d["pct_agregado"] != 83.78:
        fails.append(
            f"coorte: artefato agrega {d['nunca_expostos']} ({d['pct_agregado']}%) contra "
            f"os 56.288/83,78% do §4.1 — definição de 'exposto' divergiu entre os dois"
        )

    # (2) cada linha, ancorada ao rótulo da coorte
    rot = {"a) < 1 semana": r"\| < 1 semana \|", "b) 1-4 semanas": r"\| 1–4 semanas \|",
           "c) 4-12 semanas": r"\| 4–12 semanas \|",
           "d) > 12 semanas": r"\| \*\*> 12 semanas\*\* \|"}
    for l in d["por_coorte"]:
        pref = rot.get(l["coorte"])
        if pref is None:
            fails.append(f"coorte {l['coorte']!r} sem âncora declarada neste guarda")
            continue
        n, k = l["chunks"], l["nunca_expostos"]
        pct = f"{l['pct_nunca_exposto']:.2f}".replace(".", ",")
        # milhar com ponto, como o documento escreve
        fn, fk = f"{n:,}".replace(",", "."), f"{k:,}".replace(",", ".")
        if not re.search(pref + rf"[^|]*{re.escape(fn)}[^|]*\|[^|]*{re.escape(fk)}"
                         rf"[^|]*\|[^|]*{re.escape(pct)}%", texto):
            fails.append(
                f"§4.1: linha {l['coorte']!r} deveria ler {fn}/{fk}/{pct}% ancorada ao "
                f"rótulo — não casa; medição caiu ou a tabela divergiu do artefato"
            )

    # (3) a AFIRMAÇÃO de direção do viés, que é o que o §4.1 conclui
    mad = d["coorte_madura_pct_nunca_exposto"]
    if mad <= d["pct_agregado"]:
        fails.append(
            f"§4.1 afirma que a coorte madura é MAIS não-exposta que o agregado, mas o "
            f"artefato dá {mad}% <= {d['pct_agregado']}% — a conclusão inverteu"
        )

    # (4b) a qualificação que impede a leitura "dez mil lições invisíveis". Ela só
    #      protege se viajar COM a manchete e se os números forem os do subconjunto —
    #      a versão de 27/08 citava a média do tipo inteiro (205) como se fosse a do
    #      subconjunto (232), e ficava a duas seções de distância do número que
    #      qualificava.
    fart = root / "out" / "FLOOR-COMPOSITION-2026-08-29.json"
    if not fart.exists():
        fails.append(f"{fart.name} ausente — a qualificação dos 10.008 não tem artefato")
    else:
        f = json.loads(fart.read_text(encoding="utf-8"))
        dom, cc = f["tipo_dominante"], f["contraste_de_populacao"]
        # o artefato guarda o dominante em DOIS lugares (`por_tipo[0]` e
        # `tipo_dominante`). Se divergirem, o guarda abaixo lê um e o leitor humano
        # lê o outro — foi o que uma mutação de 29/08 explorou sem querer.
        if f["por_tipo"] and f["por_tipo"][0] != dom:
            fails.append(
                f"{fart.name}: `por_tipo[0]` e `tipo_dominante` divergem — "
                f"{f['por_tipo'][0]} vs {dom}"
            )
        # ⚠️ `d[...]` e não `p`: `p` só é ligado no bloco (4), abaixo. Escrever `p`
        # aqui deu UnboundLocalError — o mesmo defeito de ordenação que este mesmo
        # dia expôs em `lacuna-no-eixo-de-tamanho.py`, e pelo mesmo motivo.
        piso = d["condicionado_ao_piso"]
        if f["elegiveis_nunca_expostos"] != piso["nunca_expostos"]:
            fails.append(
                f"§4.1: a composição mede {f['elegiveis_nunca_expostos']} elegíveis e a "
                f"coorte mede {piso['nunca_expostos']} — populações divergiram"
            )
        cm = f"{dom['comprimento_medio']:.0f}"
        pc = str(dom["pct_do_piso"]).replace(".", ",")
        alvo = (rf"\*\*{dom['chunks']:,}".replace(",", r"\.") +
                rf" \({re.escape(pc)}%\) são `{dom['tipo']}`\*\*: fragmentos de sessão "
                rf"de \*\*{cm} caracteres\*\*")
        if not re.search(alvo, texto):
            fails.append(
                f"§4.1: a qualificação deveria ler {dom['chunks']} ({pc}%) `{dom['tipo']}` "
                f"de {cm} caracteres, ancorada — /{alvo}/ não casa"
            )
        # a média do tipo inteiro só pode aparecer marcada COMO a do tipo inteiro
        mc = f"{cc['no_corpus_inteiro']['comprimento_medio']:.0f}"
        if mc in texto and not re.search(
                rf"\*\*{mc}\*\* caracteres,? que é a média de\s*\n?\*\*todos os", texto):
            fails.append(
                f"§4.1: {mc} aparece sem estar marcado como a média do tipo INTEIRO — "
                f"é exatamente a confusão de população de 27/08"
            )

    # (4c) o COMPLEMENTAR, que o §4.1 passou a declarar: dos nunca-expostos, quantos
    #      ficam ABAIXO do piso. Recomputado, não ancorado — é derivado de dois
    #      números que este mesmo guarda já trava.
    abaixo = d["nunca_expostos"] - d["condicionado_ao_piso"]["nunca_expostos"]
    fabaixo = f"{abaixo:,}".replace(",", ".")
    pabaixo = f"{100 * abaixo / d['nunca_expostos']:.1f}".replace(".", ",")
    if not re.search(rf"\*\*{re.escape(fabaixo)} — {re.escape(pabaixo)}% — não passam nem "
                     rf"esse piso", texto):
        fails.append(
            f"§4.1: o complementar recomputa {fabaixo} ({pabaixo}%) — não casa ancorado "
            f"ao seu rótulo; texto e artefato divergiram"
        )

    # (4d) a fração do CORPUS que os elegíveis-invisíveis representam. Recomputada:
    #      uma versão do texto escrevia "um décimo", e são 14,9% — arredondamento
    #      para baixo que fazia o achado parecer menor do que é.
    # ⚠️ `fk` NÃO serve aqui: ele está ligado ao laço da tabela de coortes acima e
    # vale 52.432. Terceira vez em um dia que escrevo um guarda sobre variável
    # ligada noutro escopo — o diagnóstico saiu com o número errado e apontou para
    # o lugar errado. Expressão direta.
    nfk = f"{d['condicionado_ao_piso']['nunca_expostos']:,}".replace(",", ".")
    frac = f"{100 * d['condicionado_ao_piso']['nunca_expostos'] / d['corpus']:.1f}"
    frac = frac.replace(".", ",")
    if not re.search(rf"\*\*sobram {nfk} chunks — {re.escape(frac)}% do\s*\n?corpus\*\*",
                     texto):
        fails.append(
            f"§4.1: a fração do corpus recomputa {frac}% de {nfk} chunks — não casa "
            f"ancorada ao rótulo; 'um décimo' foi a forma errada desse número"
        )

    # (4) o número condicionado ao piso, que virou co-manchete do título
    # ⚠️ O número aparece DUAS vezes — no título do §4.1 e no parágrafo que o deriva —
    # e `f"{pf}%" in texto` foi satisfeito pela outra quando a mutação alterou só uma
    # (M4, 29/08, não mordeu). Cada ocorrência tem de ser ancorada ao SEU contexto.
    p = d["condicionado_ao_piso"]
    pf = f"{p['pct']:.2f}".replace(".", ",")
    fk = f"{p['nunca_expostos']:,}".replace(",", ".")
    fn = f"{p['chunks']:,}".replace(",", ".")
    for padrao, onde in (
        # ⚠️ "considera elegível" foi para "passa o piso de importância" em 30/08:
        # passar o piso é UMA das três condições do canal (piso + padrão de caminho +
        # janela), e o pool elegível de fato é 108, não 13.388. Terceira redação deste
        # rótulo, e as duas anteriores eram falsas em graus diferentes.
        (rf"### 4\.1 [^\n]*{re.escape(pf)}% do que passa o piso de importância",
         "título do §4.1"),
        (rf"{re.escape(fn)} chunks que passam o piso de\s*\n?elegibilidade do "
         rf"\*\*canal de cobertura\*\*", "denominador, com o canal nomeado"),
        (rf"\*\*{re.escape(fk)} = {re.escape(pf)}% nunca foram expostos\*\*",
         "co-manchete no parágrafo"),
    ):
        if not re.search(padrao, texto):
            fails.append(
                f"§4.1: {onde} deveria ler {fk} de {fn} = {pf}% ancorado ao seu contexto "
                f"(/{padrao}/ não casa) — divergiu do artefato"
            )
    return fails


def remissao_check(root: Path) -> list[str]:
    """Trava a migração de retratações para o Apêndice H (item B2, 30/08).

    Sete retratações moravam DENTRO do §4.1/§4.2/§5.7.2, interrompendo a frase que
    carrega o achado para relatar o que uma versão anterior daquela frase dizia. Foram
    para o Apêndice H, e no corpo ficou uma remissão `↩ H-n`.

    ⚠️ A migração cria uma classe de defeito nova, e é ela que este guarda cobre:
    **remissão que aponta para entrada inexistente**. Um `↩ H-3.7` que ninguém escreveu
    é pior que o parágrafo original — o leitor procura a explicação e não acha, e nada
    no documento denuncia. `grep` no texto concatenado não serve (a própria remissão
    contém a string procurada), então casa-se contra o cabeçalho da entrada.

    ⚠️ E a densidade é **série viva**: o Apêndice H afirmava "78 de 264 (29,5%)", número
    que envelheceu no mesmo dia em que uma seção nova foi escrita. Aqui ela é
    RECOMPUTADA do artefato, nunca lida do texto — a lição de que instante citado como
    se fosse constante vira falsidade por decurso de prazo.
    """
    fails: list[str] = []
    texto = (root / "MANUSCRIPT.md").read_text(encoding="utf-8")

    # (1) toda remissão acha a sua entrada
    # ⚠️ A primeira versão usava `(H-[\d.]+?)(?=[\s).,])` — lazy, com o PONTO dentro da
    # classe do lookahead. Em `↩ H-3.9` ela casava `H-3` e parava, e `### H-3 —` existe:
    # a perna nunca podia falhar. Foi achada exigindo a MENSAGEM da mutação e não a
    # contagem de falhas — a mutação disparava, mas pela perna (2), e o placar dizia
    # "3/3 mordem". Guarda cujo predicado não alcança o defeito é decoração.
    for alvo in sorted(set(re.findall(r"↩ (H-\d+(?:\.\d+)*)", texto))):
        # entrada de nível 1 é `### H-2 —`; de nível 2 é `**H-3.4 · `
        if not re.search(rf"^### {re.escape(alvo)} —", texto, re.M) and \
           not re.search(rf"^\*\*{re.escape(alvo)} · ", texto, re.M):
            fails.append(
                f"Apêndice H: a remissão `↩ {alvo}` não tem entrada — o leitor que a "
                f"seguir não acha a explicação, e nada no documento denuncia"
            )

    # (2) e nenhuma entrada H-3.x fica órfã: se ninguém remete a ela, ela virou
    #     material solto no apêndice em vez de correção de um ponto do texto.
    for entrada in sorted(set(re.findall(r"^\*\*(H-3\.\d+) · ", texto, re.M))):
        if f"↩ {entrada}" not in texto:
            fails.append(
                f"Apêndice H: {entrada} existe e ninguém remete a ela — retratação sem "
                f"o ponto do corpo que ela corrige"
            )

    # (3) a densidade: recomputada do artefato, e o Apêndice H tem de citá-la
    art = root / "out" / "WARNING-DENSITY-2026-08-30.json"
    if not art.exists():
        fails.append(f"{art.name} ausente — a densidade do Apêndice H volta a ser prosa")
        return fails
    d = json.loads(art.read_text(encoding="utf-8"))
    pct = str(d["pct_corpo_marcado"]).replace(".", ",")
    padrao = (rf"\*\*{d['corpo_marcados']} de {d['paragrafos_do_corpo']}\s*\n?"
              rf"par[áa]grafos marcados \({re.escape(pct)}%\)\*\*")
    if not re.search(padrao, texto):
        fails.append(
            f"Apêndice H: a densidade recomputa {d['corpo_marcados']} de "
            f"{d['paragrafos_do_corpo']} ({pct}%) e o texto não diz isso ancorado "
            f"(/{padrao}/ não casa) — o número do apêndice envelheceu"
        )
    return fails


def deposito_check(root: Path) -> list[str]:
    """Trava a `description` do depósito do Paper A contra o paper e o pacote.

    🔴 Este guarda existe porque a primeira redação da description dizia "21 defeitos,
    doze deles alterando números" e "17 guardas". O paper diz **oito** no §6 e **nove**
    no Apêndice E — 17 no total, oito alterando números — e os guardas são **18**. Três
    números errados escritos de memória, na véspera de irem para um registro
    **imutável**. Um depósito não tem errata: o que for publicado fica.

    ⚠️ A description NÃO pode citar um número que o manuscrito não contenha, e as
    contagens do pacote são recomputadas do disco, nunca lidas do texto.
    """
    fails: list[str] = []
    desc = root / "deposit" / "paperA" / "description.html"
    if not desc.exists():
        return []  # pacote ainda não montado — não é defeito
    d = desc.read_text(encoding="utf-8")
    texto = (root / "MANUSCRIPT.md").read_text(encoding="utf-8")

    # (1) todo número da description existe no manuscrito
    for n in sorted({m for m in re.findall(
            r"\b\d{1,3}(?:\.\d{3})+\b|\b\d+,\d+%|\b\d+,\d+\b|\b\d{2,3}%", d)}):
        if n not in texto:
            fails.append(
                f"depósito: a description cita {n!r} e o manuscrito não — número que "
                f"iria para um registro imutável sem estar no paper"
            )

    # (2) a contagem de defeitos: recomputada do §6 e do Apêndice E via o texto que o
    #     `catalogo_check` já trava, não recontada aqui (contador ad-hoc ao lado do
    #     instrumento validado é a classe de 2026-08-30).
    m6 = re.search(r"as \*\*(\w+) que mudaram um número", texto)
    mE = re.search(r"As (\w+) do §6 mais as (\w+) abaixo", texto)
    if m6 and mE:
        if not re.search(rf"<strong>17 defeitos de instrumento</strong>", d):
            fails.append("depósito: a description não diz 17 defeitos ancorado")
        # ⚠️ Ancorado ao CONTEXTO, não à presença da palavra. A primeira versão fazia
        # `if m6.group(1) not in d`, e a mutação oito→doze passou ileso porque "oito"
        # também aparece em "oito estão acima de 32,5%". Presença de substring no
        # documento concatenado é decoração — a mesma lição de 2026-08-26/27.
        if not re.search(rf"\b{re.escape(m6.group(1))} deles alterando números", d):
            fails.append(
                f"depósito: o §6 diz {m6.group(1)!r} defeitos que mudaram números e a "
                f"description não diz isso ancorado — as duas contagens divergiram"
            )

    # (3) contagens do pacote: recomputadas do disco
    man = root / "deposit" / "paperA" / "MANIFEST.json"
    if man.exists():
        itens = [i["path"] for i in json.loads(man.read_text(encoding="utf-8"))["itens"]]
        for pref, rot in (("out/", "artefatos"), ("measurement/", "scripts")):
            n = sum(1 for p in itens if p.startswith(pref))
            if not re.search(rf"\b{n}\b", d):
                fails.append(
                    f"depósito: o pacote tem {n} {rot} em {pref} e a description não "
                    f"diz esse número — recomputado do manifesto"
                )
    guardas = len(re.findall(r"^def (\w+_check)\(",
                             (root / "claims_check.py").read_text(encoding="utf-8"), re.M))
    if not re.search(rf"<code>claims_check\.py</code>,\s*\n?{guardas}\s*\n?guardas", d):
        fails.append(
            f"depósito: são {guardas} guardas e a description não diz isso ancorado — "
            f"o número muda toda vez que um guarda entra"
        )
    return fails


def escolha_check(root: Path) -> list[str]:
    """A escolha de análise do Epoch 1 está FECHADA; nenhum documento pode reabri-la.

    Fechada em 2026-09-04, sem que desfecho algum fosse consultado — e é justamente
    isso que lhe dá valor. Uma escolha de análise reaberta depois de dados existirem
    vale zero, mesmo que se chegue à mesma conclusão, porque o leitor não pode
    distinguir "decidiu antes" de "decidiu e diz que decidiu antes".

    Duas direções, porque lista de um lado só apodrece em falso verde:

      1. o texto da decisão tem de CONTINUAR no `DEVIATIONS-FOR-PAPER.md`. Se
         desaparecer numa reescrita, o guarda falha — a decisão é o artefato, não a
         lembrança dela;
      2. nenhum documento pode voltar a chamá-la de aberta. Ancorado ao FATO (a
         decisão existe) e não a uma frase literal — foi a lição do `comecou_check`,
         cujo antecessor cobria 1 de 8 documentos por casar frase em vez de fato.

    ⚠️ Isenção por arquivo NOMEADO, nunca por heurística: num documento datado a frase
    "a escolha fica aberta" é registro histórico verdadeiro do que se sabia então, e
    apagá-la destruiria a cronologia. Num documento vivo, a mesma frase é estado, e
    estado que envelheceu é mentira.
    """
    dev = root / "DEVIATIONS-FOR-PAPER.md"
    if not dev.exists():
        return [f"{dev.name}: ausente — a decisão de análise do Epoch 1 vive nele"]

    fails: list[str] = []
    texto = dev.read_text()

    # (1) a decisão tem de continuar escrita
    for marca, oque in [
        ("FECHADA em 2026-09-04", "a data e o fato do fechamento"),
        ("não é excluído", "a decisão de inclusão do Epoch 1"),
        ("Mandatory ITT co-estimate", "a citação da estrutura registrada"),
        ("pré-especificada aqui", "a terceira análise, de sensibilidade"),
    ]:
        if marca not in texto:
            fails.append(
                f"{dev.name}: perdeu `{marca}` — {oque}. A decisão é o artefato; "
                f"se o texto sai, a precedência não é mais verificável"
            )

    # (2) nenhum documento VIVO pode reabri-la
    DATADOS = {
        "DEVIATIONS-FOR-PAPER.md": "contém a decisão e a retratação da 1ª redação",
    }
    REABRE = re.compile(
        r"(escolha de an[áa]lise|an[áa]lise do Epoch 1)[^.]{0,80}"
        r"(fica|permanece|segue|continua)[^.]{0,20}abert",
        re.I,
    )
    for md in sorted(root.glob("*.md")):
        if md.name in DATADOS:
            continue
        for i, linha in enumerate(md.read_text().split("\n"), 1):
            if REABRE.search(linha):
                fails.append(
                    f"{md.name}:{i}: volta a chamar a escolha de análise do Epoch 1 "
                    f"de aberta, e ela foi fechada em 2026-09-04 — `{linha.strip()[:70]}`"
                )
    return fails


def comecou_check(root: Path) -> list[str]:
    """Se o ensaio começou, nenhum documento VIVO pode dizer que não começou.

    Em 2026-09-01 o Epoch 1 entrou no ar e **oito** documentos ainda afirmavam que o
    estudo não havia começado. O guarda que existia — perna (7) de `estimando_check` —
    cobria **um** deles, e pela frase literal `"zero epochs randomizados"`, que os
    outros sete não usam. Guarda ancorado à frase cobre a frase; ancorado ao fato cobre
    a classe.

    A distinção que este guarda precisa fazer, e que um `grep` cego não faz:

      * documento DATADO (`PROSPECTIVE-ESTIMAND`, `ASSIGN-SEED`, `DESIGN-REVISION`) —
        a afirmação "nenhum epoch existe" é a **prova de precedência** e tem de ficar.
        Reescrevê-la destruiria o valor do registro prospectivo.
      * documento VIVO (`README`, `NEXT-STEPS`, `PAPER-SPLIT`, a description do
        depósito) — a mesma frase é estado, e estado que envelheceu é mentira.

    Por isso a isenção é por **arquivo nomeado com razão**, não por heurística de data
    no texto: um arquivo vivo pode conter uma data e continuar sendo estado.

    ⚠️ `NEXT-STEPS.md` já tinha sido reescrito em 2026-08-15 exatamente por afirmar o
    oposto do estado real — e o próprio documento chama isso de "a pior coisa que um
    documento de estado pode fazer". Reincidiu em 17 dias. É o argumento de que a
    disciplina não basta e o guarda é necessário.
    """
    if not (root / "ASSIGNMENT.json").exists():
        return []                      # o ensaio não começou: a afirmação é verdadeira

    # isentos, com a razão pela qual a afirmação PERTENCE ao documento
    DATADOS = {
        "PROSPECTIVE-ESTIMAND-2026-08-30.md": "registro prospectivo — a afirmação é a precedência",
        "ASSIGN-SEED-2026-08-30.md": "declaração time-gated — idem",
        "DESIGN-REVISION-2026-08-30.md": "revisão datada — idem",
        "PLANO-2026-08-30.md": "plano datado",
        "PAPER-SPLIT-2026-08-28.md": "o título foi corrigido; o corpo é histórico datado",
    }
    PADROES = (
        r"[Oo] estudo \*\*não começou\*\*(?! *—? *⚠️)",
        r"[Oo] estudo não começou",
        r"nenhum epoch randomizado existe",
        r"nenhum braço foi atribuído",
        r"zero epochs randomizados",
    )
    fails: list[str] = []
    for p in sorted(list(root.rglob("*.md")) + list(root.rglob("*.html"))):
        rel = p.relative_to(root).as_posix()
        if "_archive" in rel or "/_archive/" in rel:
            continue
        if p.name in DATADOS:
            continue
        texto = p.read_text(encoding="utf-8", errors="replace")
        for pat in PADROES:
            for m in re.finditer(pat, texto):
                # tachado ou marcado como superado não conta
                ctx = texto[max(0, m.start() - 120): m.end() + 200]
                if "~~" in ctx or "superad" in ctx.lower() or "COMEÇOU" in ctx:
                    continue
                ln = texto[: m.start()].count("\n") + 1
                fails.append(
                    f"{rel}:{ln}: afirma que o ensaio não começou, e ASSIGNMENT.json "
                    f"existe (Epoch 1 no ar desde 2026-09-01) — /{pat}/")
                break
    return fails


def estrutura_check(root: Path) -> list[str]:
    """Toda subseção `N.M[.K]` tem de morar dentro da seção `## N.`.

    Achado em 2026-09-01, DEPOIS do depósito: a `#### 5.7.2` estava encravada no meio
    do Abstract — 100 linhas entre a primeira metade do resumo e o seu fecho — e a §5
    terminava na 5.7.1, sem ela. Quem lia o Abstract caía numa tabela de âncora de
    replay; quem ia à §5 procurar o terceiro eixo não o encontrava.

    ⚠️ Nenhum guarda pegou, e `terceiro_eixo_check` passava verde: ele confere que o
    CONTEÚDO da 5.7.2 existe e casa com os artefatos, não ONDE ele está. Presença sem
    posição — a mesma família do guarda que busca substring no corpus concatenado.

    Este é genérico de propósito. Travar "a 5.7.2 fica entre a 5.7.1 e a §6" resolveria
    o caso e deixaria a classe viva; a classe é *subseção fora da sua seção*.
    """
    texto = (root / "MANUSCRIPT.md").read_text(encoding="utf-8")
    linhas = texto.splitlines()
    fails: list[str] = []

    # limites de cada seção de topo: "## N. titulo"
    secoes: list[tuple[int, int]] = []          # (numero, linha)
    for i, l in enumerate(linhas):
        if m := re.match(r"^## (\d+)\. ", l):
            secoes.append((int(m.group(1)), i))
    if not secoes:
        return ["MANUSCRIPT: nenhuma seção `## N.` encontrada — a varredura de estrutura "
                "não pode afirmar nada, e silêncio aqui não é aprovação"]

    def dona(linha: int) -> int | None:
        """Número da seção de topo que contém esta linha."""
        atual = None
        for num, ini in secoes:
            if ini < linha:
                atual = num
            else:
                break
        return atual

    for i, l in enumerate(linhas):
        m = re.match(r"^#{3,4} (\d+)\.(\d+)", l)
        if not m:
            continue
        pertence, hospeda = int(m.group(1)), dona(i)
        if hospeda != pertence:
            onde = f"§{hospeda}" if hospeda else "ANTES da §1 (Abstract ou frontmatter)"
            fails.append(
                f"MANUSCRIPT:{i + 1}: `{l.strip()[:52]}` é subseção da §{pertence} "
                f"mas está dentro de {onde} — subseção fora da sua seção")
    return fails


def inicio_check(root: Path) -> list[str]:
    """TRIAL-START: every derived number in it recomputed from the live artefact.

    The file records the instant the trial left `shadow`. Three of its numbers are
    NOT observations — they are read off files that can change underneath it:

      * the `sha256` of ASSIGNMENT-SERVING.json — regenerate the assignment and the
        document silently points at a hash the serving no longer loads;
      * `w = 4.0` for 2026-09-01 — a fact about the assignment, not about the log;
      * the shadow churn 151/4.037 = 3,74%, whose artefact this repo already owns.

    A number copied out of a file is a cache, and this is its invalidation. The
    burst rate (672/day, 4x7) and the boost count (19) stay as prose: they are
    observations of a log, reproducible only by re-reading production.
    """
    doc = root / "TRIAL-START-2026-09-01.md"
    if not doc.exists():
        return []                      # optional file; absent is not a failure
    texto = doc.read_text(encoding="utf-8")
    fails: list[str] = []

    serv = root / "ASSIGNMENT-SERVING.json"
    if not serv.exists():
        fails.append("TRIAL-START cita ASSIGNMENT-SERVING.json e o arquivo não existe")
    else:
        cru = serv.read_bytes()
        sha = hashlib.sha256(cru).hexdigest()
        if sha not in texto:
            fails.append(
                f"TRIAL-START: o sha256 de ASSIGNMENT-SERVING.json é {sha[:16]}… e o "
                f"documento não o contém — foi regenerado sem atualizar o registro")
        eps = {e["epoch_inicio"]: e for e in json.loads(cru)["epochs"]}
        e1 = eps.get("2026-09-01")
        if e1 is None:
            fails.append("TRIAL-START: 2026-09-01 ausente da atribuição servida")
        else:
            # o texto tem de nomear a dose que a atribuição de fato manda servir
            if not re.search(rf"`w = {re.escape(str(e1['w']))}`", texto):
                fails.append(
                    f"TRIAL-START: a atribuição dá w = {e1['w']} para 2026-09-01 e o "
                    f"documento não diz isso ancorado (`w = {e1['w']}`)")
            if e1["arm"] != "treatment" and "servido=tratado" in texto:
                fails.append(
                    f"TRIAL-START: mostra `servido=tratado` mas a atribuição diz "
                    f"{e1['arm']} para 2026-09-01")

    art = root / "out" / "SHADOW-CHURN-2026-08-30.json"
    if art.exists():
        s = json.loads(art.read_text(encoding="utf-8"))
        # TRIAL-START é escrito em inglês (decimal com ponto); os documentos PT-BR
        # do repo usam vírgula. Aceitar as duas formas é o certo aqui — exigir a
        # vírgula faria o guarda morder o documento por ser inglês, não por mentir.
        taxa = f"{100 * s['taxa_churn']:.2f}"
        if not re.search(rf"{re.escape(taxa[:-3])}[.,]{taxa[-2:]}%", texto):
            fails.append(
                f"TRIAL-START: o churn do shadow recomputa {taxa}% e o documento "
                f"não diz isso — o número foi copiado e envelheceu")
        esperado = s["taxa_churn"] * 7
        if not re.search(rf"expected count in 7 briefs is {esperado:.2f}"
                         .replace(".", r"\."), texto):
            fails.append(
                f"TRIAL-START: a contagem esperada em 7 briefs recomputa "
                f"{esperado:.2f} e o documento não diz isso ancorado")
    return fails


def sizing_check(root: Path) -> list[str]:
    """Re-run `sizing.py` and `assign_arms.py` and assert the locked outputs.

    This is a RUN, not a regex: the point of the 2026-08-17 amendment is that a
    formula was wrong while every number derived from it reproduced perfectly.
    Only executing the current code can catch the next instance of that.

    Limit, stated because it is real: this asserts that the deposited scripts
    still produce the locked values. It does NOT assert that the formula inside
    them is the right one for the design — that is a question about applicability,
    which no self-check can answer, and which is exactly how the 174 survived
    eleven versions and five adversarial voices.
    """
    failures = []
    sizing = root / "sizing.py"
    if not sizing.exists():
        return [f"sizing.py not found under {root}"]

    argv = [sys.executable, str(sizing)]
    for key, val in SIZING_INPUTS.items():
        argv += [f"--{key.replace('_', '-')}", str(val)]
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        return [f"sizing.py exited {proc.returncode}: {proc.stderr.strip()[:200]}"]
    out = json.loads(proc.stdout)

    got_n = out["N_epochs_total"]
    if got_n != N_EPOCHS_LOCKED:
        failures.append(f"N_epochs: sizing.py returns {got_n}, this file locks {N_EPOCHS_LOCKED}")
    got_de = out["intermediarios"]["design_effect"]
    if abs(got_de - DESIGN_EFFECT_LOCKED) > 1e-6:
        failures.append(f"design effect: sizing.py returns {got_de}, locked {DESIGN_EFFECT_LOCKED}")
    got_cv2 = out["inputs"].get("cv2")
    if got_cv2 != CV2_LOCKED:
        failures.append(f"cv2: sizing.py echoes {got_cv2}, locked {CV2_LOCKED}")

    # The equal-cluster formula is the defect itself; assert it is gone by
    # checking that cv2 actually changes the answer. If a future edit dropped the
    # term, every number above would still reproduce at cv2=0 and the check would
    # pass while the design effect was wrong again.
    argv_zero = [a for a in argv]
    argv_zero[argv_zero.index("--cv2") + 1] = "0.0"
    zero = json.loads(subprocess.run(argv_zero, capture_output=True, text=True).stdout)
    if zero["intermediarios"]["design_effect"] >= got_de:
        failures.append(
            "design effect does not increase with cv2 — the unequal-cluster term "
            "is not being applied, which is the 2026-08-17 defect returning"
        )

    assign = root / "assign_arms.py"
    if not assign.exists():
        failures.append(f"assign_arms.py not found under {root}")
        return failures
    src = assign.read_text(encoding="utf-8")
    m = re.search(r"^N_EPOCHS\s*=\s*(\d+)", src, re.MULTILINE)
    if not m:
        failures.append("assign_arms.py: no N_EPOCHS declaration found")
    elif int(m.group(1)) != N_EPOCHS_LOCKED:
        failures.append(
            f"assign_arms.py declares N_EPOCHS = {m.group(1)}, sizing locks {N_EPOCHS_LOCKED}"
        )
    else:
        seed = hashlib.sha256(b"claims_check").hexdigest()
        proc = subprocess.run(
            [sys.executable, str(assign), "assign", "--seed", seed, "--start", "2026-09-01"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            failures.append(f"assign_arms.py exited {proc.returncode}")
        else:
            bal = json.loads(proc.stdout)["balanceamento"]
            if bal["grupos"] != ALLOCATION_LOCKED:
                failures.append(
                    f"allocation: assign_arms.py gives {bal['grupos']}, locked {ALLOCATION_LOCKED}"
                )
            if not bal["dentro_da_tolerancia"]:
                failures.append("assign_arms.py: balance outside the registered tolerance")
    return failures


def show() -> None:
    print(f"band            w in {{{', '.join(str(w) for w in BAND)}}}")
    print(f"Delta_cut       {DELTA_CUT}")
    print(f"CUT_FRESH       {CUT_FRESH}   CUT_MAIN  {CUT_MAIN}")
    print()
    print("w_min against the coverage cut (independent of the band):")
    print(f"  {'sev':4}  {'age 0':>8}  {'24 h':>8}  {'30 d':>8}")
    for name, sev in SEVERITY.items():
        print(
            f"  {name:4}  {w_min(sev, 0):8.4f}  {w_min(sev, 1):8.4f}  {w_min(sev, 30):8.4f}"
        )
    print()
    for cut, label in ((CUT_FRESH, "coverage slots"), (CUT_MAIN, "primary slots")):
        print(f"oldest age still reached, {label} (cut {cut}):")
        for w in BAND:
            cells = []
            for name, sev in SEVERITY.items():
                age = max_age(sev, w, cut)
                if age is None:
                    cells.append(f"{name}=never")
                elif age == math.inf:
                    cells.append(f"{name}=always")
                else:
                    cells.append(f"{name}={age:.2f}d")
            print(f"  w={w:<4} " + "  ".join(cells))
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--show", action="store_true", help="print the recomputed table")
    ap.add_argument("--root", default=str(Path(__file__).parent))
    args = ap.parse_args()

    if args.show:
        show()
        return 0

    failures: list[str] = []
    failures += sizing_check(Path(args.root))

    for label, computed, published, tol in claims():
        if computed is None or computed == math.inf:
            failures.append(f"{label}: computed {computed}, expected a finite {published}")
        elif abs(computed - published) > tol:
            failures.append(
                f"{label}: computed {computed:.6f}, document says {published} "
                f"(tolerance {tol})"
            )

    failures.extend(sweep(Path(args.root)))
    failures.extend(cross_check(Path(args.root)))
    failures.extend(doc_check(Path(args.root)))
    failures.extend(delta_cut_check(Path(args.root)))
    failures.extend(blob_check(Path(args.root)))
    failures.extend(janela_check(Path(args.root)))
    failures.extend(coorte_check(Path(args.root)))
    failures.extend(sem_guarda_check(Path(args.root)))
    failures.extend(estimando_check(Path(args.root)))
    failures.extend(eixo_check(Path(args.root)))
    failures.extend(superficie_check(Path(args.root)))
    failures.extend(cobertura_check(Path(args.root)))
    failures.extend(registro_check(Path(args.root)))
    failures.extend(catalogo_check(Path(args.root)))
    failures.extend(contrafactual_check(Path(args.root)))
    failures.extend(censos_check(Path(args.root)))
    failures.extend(terceiro_eixo_check(Path(args.root)))
    failures.extend(remissao_check(Path(args.root)))
    failures.extend(deposito_check(Path(args.root)))
    failures.extend(inicio_check(Path(args.root)))
    failures.extend(estrutura_check(Path(args.root)))
    failures.extend(comecou_check(Path(args.root)))
    failures.extend(escolha_check(Path(args.root)))

    if failures:
        print(f"FAIL — {len(failures)} divergence(s):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1

    n = len(claims())
    print(f"ok — {n} band-dependent claims recomputed and matched; sweep clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
