#!/usr/bin/env python3
"""
validate-tex.py — Validação estrutural dos arquivos .tex para submissão arXiv.
Verifica: citations vs refs.bib, referências cruzadas pendentes, contagem de seções,
ambientes não-balanceados.

Uso: python3 validate-tex.py
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuração de caminhos (absolutos)
# ---------------------------------------------------------------------------
LATEX_DIR = Path("/Users/lab/Claude/Projetos/memoria-nox/paper/publication/latex")
REFS_BIB  = LATEX_DIR.parent / "refs.bib"
SEC_FILES = [
    LATEX_DIR / "sec_abstract.tex",
    LATEX_DIR / "sec_1_3.tex",
    LATEX_DIR / "sec_4_7.tex",
]

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def read_file(path: Path) -> str:
    """Lê arquivo e retorna conteúdo; retorna string vazia se não encontrado."""
    if not path.exists():
        print(f"  [ERRO] Arquivo não encontrado: {path}")
        return ""
    return path.read_text(encoding="utf-8")

def extract_bib_keys(bib_content: str) -> set[str]:
    """Extrai todas as chaves do .bib (ex: @article{key, ...})."""
    return set(re.findall(r"@\w+\{([^,\s]+),", bib_content))

def extract_cite_keys(tex_content: str) -> list[str]:
    """Extrai todas as chaves de \\cite{} e \\cite[]{} de um tex."""
    raw = re.findall(r"\\cite(?:\[[^\]]*\])?\{([^}]+)\}", tex_content)
    keys = []
    for group in raw:
        for key in group.split(","):
            keys.append(key.strip())
    return keys

def extract_labels(tex_content: str) -> set[str]:
    """Extrai todos os \\label{...}."""
    return set(re.findall(r"\\label\{([^}]+)\}", tex_content))

def extract_refs(tex_content: str) -> list[str]:
    """Extrai todos os \\ref{...} e \\eqref{...}."""
    return re.findall(r"\\(?:eq)?ref\{([^}]+)\}", tex_content)

def count_sections(tex_content: str) -> dict[str, int]:
    """Conta \\section, \\subsection, \\subsubsection."""
    return {
        "section":       len(re.findall(r"\\section\{", tex_content)),
        "subsection":    len(re.findall(r"\\subsection\{", tex_content)),
        "subsubsection": len(re.findall(r"\\subsubsection\{", tex_content)),
    }

def check_balance(tex_content: str) -> list[str]:
    """Verifica se \\begin{env} tem \\end{env} correspondente."""
    begins = re.findall(r"\\begin\{([^}]+)\}", tex_content)
    ends   = re.findall(r"\\end\{([^}]+)\}", tex_content)
    issues = []
    from collections import Counter
    b_count = Counter(begins)
    e_count = Counter(ends)
    all_envs = set(b_count) | set(e_count)
    for env in sorted(all_envs):
        b = b_count.get(env, 0)
        e = e_count.get(env, 0)
        if b != e:
            issues.append(f"  [DESBALANCEADO] \\begin{{{env}}} x{b} vs \\end{{{env}}} x{e}")
    return issues

# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("validate-tex.py — Validação estrutural para arXiv")
    print("=" * 70)

    # Leitura
    bib_content = read_file(REFS_BIB)
    bib_keys    = extract_bib_keys(bib_content)
    print(f"\n[BIB] refs.bib: {len(bib_keys)} entradas encontradas")

    all_tex     = ""
    all_cites   = []
    all_labels  = set()
    all_refs    = []
    total_warn  = 0
    total_ok    = 0

    for sec_file in SEC_FILES:
        content = read_file(sec_file)
        if not content:
            continue
        all_tex    += "\n" + content
        all_cites  += extract_cite_keys(content)
        all_labels |= extract_labels(content)
        all_refs   += extract_refs(content)

        # Contagem de seções por arquivo
        counts = count_sections(content)
        lines  = content.count("\n")
        chars  = len(content)
        print(f"\n[FILE] {sec_file.name}")
        print(f"  Linhas: {lines} | Caracteres: {chars}")
        print(f"  \\section: {counts['section']}  "
              f"\\subsection: {counts['subsection']}  "
              f"\\subsubsection: {counts['subsubsection']}")

        # Ambientes
        issues = check_balance(content)
        if issues:
            print("  Ambientes desbalanceados:")
            for iss in issues:
                print(f"  {iss}")
            total_warn += len(issues)
        else:
            print("  Ambientes: OK (todos balanceados)")
            total_ok += 1

    # ---------------------------------------------------------------------------
    # Validação de citations
    # ---------------------------------------------------------------------------
    print("\n[CITATIONS]")
    cite_keys_used = sorted(set(all_cites))
    orphans = [k for k in cite_keys_used if k not in bib_keys]
    print(f"  Chaves \\cite{{}} usadas (únicas): {len(cite_keys_used)}")
    if orphans:
        print(f"  [AVISO] {len(orphans)} chave(s) não encontrada(s) em refs.bib:")
        for k in orphans:
            print(f"    - {k}")
        total_warn += len(orphans)
    else:
        print("  Todas as chaves \\cite{} existem em refs.bib — OK")
        total_ok += 1

    # ---------------------------------------------------------------------------
    # Validação de referências cruzadas
    # ---------------------------------------------------------------------------
    print("\n[CROSS-REFERENCES]")
    all_refs_used = sorted(set(all_refs))
    dangling = [r for r in all_refs_used if r not in all_labels]
    print(f"  \\label{{}} definidos: {len(all_labels)}")
    print(f"  \\ref{{}} / \\eqref{{}} usados (únicos): {len(all_refs_used)}")
    if dangling:
        print(f"  [AVISO] {len(dangling)} referência(s) pendente(s) (sem \\label correspondente):")
        for r in dangling:
            print(f"    - \\ref{{{r}}}")
        total_warn += len(dangling)
    else:
        print("  Todas as \\ref{} têm \\label correspondente — OK")
        total_ok += 1

    # ---------------------------------------------------------------------------
    # Contagem total de seções
    # ---------------------------------------------------------------------------
    print("\n[SECTION TOTALS across all sec_*.tex]")
    totals = count_sections(all_tex)
    print(f"  \\section      : {totals['section']}")
    print(f"  \\subsection   : {totals['subsection']}")
    print(f"  \\subsubsection: {totals['subsubsection']}")

    # ---------------------------------------------------------------------------
    # Resumo final
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"RESULTADO: {total_ok} verificação(ões) OK | {total_warn} aviso(s)")
    if total_warn == 0:
        print("STATUS: PASS — pronto para compilar")
    else:
        print("STATUS: PASS COM AVISOS — revisar itens acima antes de submeter")
    print("=" * 70)

    return 0 if total_warn == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
