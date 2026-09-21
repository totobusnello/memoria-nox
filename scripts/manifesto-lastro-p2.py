#!/usr/bin/env python3
"""Manifesto do lastro do ENSAIO P2 (janela 2026-09-01 .. 2026-09-20).

Irmão de `manifesto-lastro.py` (que cobre o lastro do rc4, Paper 1), e existe
separado porque cobre outro objeto: os artefatos que `MANUSCRIPT-B.md` cita.

O CONTRATO, herdado da regra §13 do CLAUDE.md e repetido aqui porque um
manifesto que não o declara vira decoração:

  🔑 Um manifesto prova que os bytes são os bytes. NÃO prova que existe cópia.
     É detector de perda, não remédio. A cópia é do `backup-lastro-p2.sh`, e
     quem a verifica recalcula o hash NO DESTINO.

  ⚠️ A corrida não se repete. Pod efémero, provider não-determinista, e os
     vereditos custaram chamadas pagas. `rc4/nox_mem.json` já mostrou o que
     custa um placeholder de versão não resolvido: a versão do sistema medido
     ficou por registar para sempre.

O censo dos caminhos NÃO é lista de mão: sai do Apêndice B do manuscrito, que
é o que o paper cita. Uma lista à mão é amostra vendida como censo — defeito
já pago neste repo.
"""
from __future__ import annotations
import hashlib, json, os, re, sys
from pathlib import Path

RAIZ_ART = Path.home() / "Backups" / "paper2-ensaio-2026-09-21"
RAIZ_VER = Path.home() / ".paper2-verdicts"
MANUSCRITO = Path(__file__).resolve().parents[1] / "paper2-interventional" / "MANUSCRIPT-B.md"
REPO = Path(__file__).resolve().parents[1] / "paper2-interventional"

# Onde procurar cada nome citado. Um nome pode viver em mais de uma raiz; o
# manifesto regista ONDE encontrou, nunca assume.
RAIZES = [RAIZ_ART, RAIZ_VER, REPO]


def sha256(p: Path) -> tuple[str, int]:
    h = hashlib.sha256(); n = 0
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b); n += len(b)
    return h.hexdigest(), n


def sha256_dir(d: Path) -> tuple[str, int, int]:
    """Hash de diretório = hash dos (caminho relativo, hash) ordenados.

    Ordenado para ser determinista, e inclui o CAMINHO para que mover um
    ficheiro dentro da árvore mude o hash — mover é uma perda de contexto
    tanto quanto apagar (a citação quebra do mesmo jeito)."""
    itens = []; total = 0
    for f in sorted(d.rglob("*")):
        if f.is_file():
            hx, n = sha256(f)
            itens.append(f"{f.relative_to(d).as_posix()}  {hx}")
            total += n
    agg = hashlib.sha256("\n".join(itens).encode()).hexdigest()
    return agg, total, len(itens)


def citados() -> list[str]:
    """Os nomes que o Apêndice B do manuscrito cita, extraídos DELE."""
    txt = MANUSCRITO.read_text()
    i = txt.index("## Appendix B")
    j = txt.index("\n## ", i + 10) if "\n## " in txt[i + 10:] else len(txt)
    bloco = txt[i:j]
    # nomes em crase com extensão conhecida, ou diretórios terminados em /
    nomes = re.findall(r"`([A-Za-z0-9_.\-]+\.(?:json|jsonl|ndjson|py|txt|db))`", bloco)
    return sorted(set(nomes))


def localizar(nome: str) -> Path | None:
    for r in RAIZES:
        p = r / nome
        if p.exists():
            return p
    return None


def main() -> int:
    # ── modo verificador: UMA implementação do hash de diretório ────────────
    # O `backup-lastro-p2.sh` chama ISTO em vez de reimplementar o agregado em
    # shell. A primeira versão reimplementou-o, e as duas divergiram por uma
    # newline final — «\n».join sem terminador contra um pipeline que o põe.
    # Duas cópias de uma regra divergem em silêncio; é a razão de
    # `estimador_itt.py` ser composição, e a regra vale para shell também.
    if len(sys.argv) > 2 and sys.argv[1] == "--hash-dir":
        d = Path(sys.argv[2])
        if not d.is_dir():
            print("", end=""); return 2
        print(sha256_dir(d)[0]); return 0

    nomes = citados()
    if not nomes:
        print("ABORTA: o Apêndice B não citou artefato nenhum — o censo leu 0 bytes,",
              "o que é indistinguível de 'nada a proteger'.", file=sys.stderr)
        return 2

    entradas, ausentes = [], []
    for nome in nomes:
        p = localizar(nome)
        if p is None:
            ausentes.append(nome); continue
        hx, n = sha256(p)
        entradas.append(dict(nome=nome, caminho=str(p), sha256=hx, bytes=n,
                             tipo="ficheiro"))

    # diretórios inteiros: citados no manuscrito em prosa, não como `nome.ext`
    for d in ("action-archive", "lotes"):
        p = RAIZ_ART / d
        if p.exists():
            hx, n, k = sha256_dir(p)
            entradas.append(dict(nome=d, caminho=str(p), sha256=hx, bytes=n,
                                 tipo="diretorio", ficheiros=k))
        else:
            ausentes.append(d + "/")

    out = dict(
        gerado_em=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        objeto="lastro do ensaio P2, janela 2026-09-01..2026-09-20",
        censo_de="Apêndice B de MANUSCRIPT-B.md (nunca lista de mão)",
        contrato="manifesto = detector de perda, NAO remedio; a copia verifica-se "
                 "recalculando no DESTINO (backup-lastro-p2.sh)",
        irreprodutivel="pod efemero + provider nao-determinista + vereditos pagos",
        n_artefatos=len(entradas),
        bytes_totais=sum(e["bytes"] for e in entradas),
        ausentes=ausentes,
        artefatos=entradas,
    )
    dest = RAIZ_ART / "MANIFESTO-LASTRO-P2.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"artefatos: {len(entradas)}  ·  "
          f"{out['bytes_totais']/2**20:,.1f} MiB  ·  manifesto: {dest}")
    for e in entradas:
        marca = "📁" if e["tipo"] == "diretorio" else "  "
        print(f"  {marca} {e['sha256'][:12]}…  {e['bytes']/2**20:8.2f} MiB  {e['nome']}")
    if ausentes:
        print(f"\n🔴 CITADOS PELO PAPER E AUSENTES ({len(ausentes)}): {ausentes}")
        print("   O paper cita o que não existe — ou o nome mudou, ou o ficheiro sumiu.")
        return 1
    print("\n✅ todo artefato citado pelo Apêndice B existe e está hasheado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
