"""Size each pipe-table separator by what the column actually carries.

Pandoc derives LaTeX column widths from the DASH COUNT in the separator row, so
a uniform `|---|---|` gives every column the same share no matter what is in it.
Measured on v1.0: one table gave 33% of the page to a column whose widest cell is
ONE character, while the column beside it wrapped to four lines.

Weight per column = p80 of its cell lengths (header included), which tracks how
many lines the column will wrap to, and is not hijacked by one long outlier the
way max() is. Floors and ceilings keep a narrow column readable and stop a wide
one from eating the table. Alignment markers (:---, ---:) are preserved.
"""
import pathlib, re, sys

TETO = 62                    # percent: no column eats the table
DASHES = 100                 # total dashes to distribute
LINHA_CHARS = 95             # roughly what one 10pt line holds at this textwidth

def p80(vals):
    if not vals: return 1
    v = sorted(vals)
    return v[min(len(v) - 1, int(0.8 * len(v)))]

def larguras(cols_cells, cols_words=None):
    """cols_cells: cell LENGTHS per column. cols_words: longest unbreakable WORD
    per column — the real floor. A share proportional to average content can still
    be narrower than a single word in it ("instrument"), and LaTeX then overflows
    the cell or breaks it absurdly. So the floor is the word, not a flat percent."""
    pesos = [max(p80(c), 3) for c in cols_cells]
    tot = sum(pesos)
    pct = [100 * p / tot for p in pesos]
    if cols_words:
        for i, w in enumerate(cols_words):
            piso = 100 * (w + 2) / LINHA_CHARS
            if pct[i] < piso: pct[i] = piso
    for i, p in enumerate(pct):
        if p > TETO: pct[i] = TETO
    tot = sum(pct)
    return [p / tot for p in pct]

def processa(path, aplicar):
    linhas = pathlib.Path(path).read_text(encoding="utf-8").split("\n")
    dentro, mudadas, out = False, 0, list(linhas)
    i = 0
    while i < len(linhas):
        l = linhas[i]
        if l.startswith("```"): dentro = not dentro; i += 1; continue
        if dentro or not re.match(r'^\s*\|[\s:\-|]+\|\s*$', l): i += 1; continue
        # achou um separador: o bloco da tabela vai do header ate a ultima linha com |
        ini = i - 1
        fim = i + 1
        while fim < len(linhas) and re.match(r'^\s*\|.*\|\s*$', linhas[fim]): fim += 1
        if ini < 0 or not re.match(r'^\s*\|.*\|\s*$', linhas[ini]): i += 1; continue
        partes = [p.strip() for p in l.strip().strip("|").split("|")]
        n = len(partes)
        cols = [[] for _ in range(n)]
        words = [0] * n
        for r in linhas[ini:ini+1] + linhas[i+1:fim]:
            cells = [x.strip() for x in r.strip().strip("|").split("|")]
            for c in range(min(n, len(cells))):
                cols[c].append(len(cells[c]))
                for w in re.split(r"[\s/]+", re.sub(r"[*`_]", "", cells[c])):
                    words[c] = max(words[c], len(w))
        fr = larguras(cols, words)
        novo = []
        for c, p in enumerate(partes):
            d = max(3, round(fr[c] * DASHES))
            esq, dir_ = p.startswith(":"), p.endswith(":")
            novo.append(("" if not esq else ":") + "-" * d + ("" if not dir_ else ":"))
        nova = "|" + "|".join(novo) + "|"
        if nova != l.strip():
            mudadas += 1
            out[i] = nova
        i = fim
    if aplicar:
        pathlib.Path(path).write_text("\n".join(out), encoding="utf-8")
    return mudadas

if __name__ == "__main__":
    aplicar = "--apply" in sys.argv
    n = processa(sys.argv[1], aplicar)
    print(f"{n} separadores {'reescritos' if aplicar else 'a reescrever'}")
