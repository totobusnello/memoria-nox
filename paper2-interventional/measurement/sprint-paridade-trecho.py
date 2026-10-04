#!/usr/bin/env python3
"""Number-parity check for one translated chunk: PT line range vs EN file. Reuses numeros() from paridade-de-traducao.py."""
import importlib.util, pathlib, re, sys
from collections import Counter
here = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p", here / "paridade-de-traducao.py")
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
a, b, en = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
pt = "".join(p.PT.read_text(encoding="utf-8").splitlines(keepends=True)[a-1:b])
en = pathlib.Path(en).read_text(encoding="utf-8")
def nocode(t): return re.sub(r"`[^`]*`", lambda m: m.group(0), t)
for label, f in (("sem codigo (padrao)", lambda t: t), ("com codigo (so espacos de backtick removidos)", lambda t: t.replace("`", " "))):
    # second mode: bypass code-span stripping by removing backticks first
    x, y = p.numeros(f(pt), False), p.numeros(f(en), True)
    print(label, sum(x.values()), sum(y.values()), "so_pt", dict(x - y), "so_en", dict(y - x))
