#!/usr/bin/env python3
"""Estende `MANIFESTO-LASTRO-P2.json` com artefatos novos, SEM regenerá-lo.

Existe porque `manifesto-lastro-p2.py` (sem `--hash-dir`) REESCREVE o manifesto a
partir do Apêndice B de `MANUSCRIPT-B.md` — rodá-lo apagaria toda extensão. Este
script só ACRESCENTA, e prova que as entradas antigas ficaram byte-idênticas.

Contratos herdados do lastro de 2026-09-22 (ver `backup-lastro-p2.sh`):

  🔑 UMA implementação do hash: importa `sha256`/`sha256_dir` do próprio
     `manifesto-lastro-p2.py`. A 1ª versão em shell divergiu por uma newline final.
  🔑 Nada aqui copia para as pernas nem verifica cópia: isso é do
     `backup-lastro-p2.sh --verificar`, que recalcula NO DESTINO.

Regra de localização (por caminho relativo a `paper2-interventional/`, ou absoluto):

  - sob ~/Backups/paper2-ensaio-2026-09-21 ou ~/.paper2-verdicts → entra como está;
  - no repo, TODO ficheiro versionado, limpo contra HEAD e igual em origin/main
    (`git fetch` antes) → entra com caminho do repo
    (o backup salta-o: "vive no repo, versionado"), mais commit e id do objeto git;
  - no repo e NÃO versionado (ou sujo) → copiado para RAIZ_ART/<rotulo>/<rel> e entra
    com esse caminho, para o `backup-lastro-p2.sh` o levar às duas pernas. Nunca
    sobrescreve um destino que já exista com conteúdo diferente.

Uso:
  python3 scripts/estende-lastro-p2.py --rotulo item10 [--dry-run] REL [REL ...]
"""
from __future__ import annotations
import argparse, datetime, hashlib, importlib.util, json, shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO_ROOT = AQUI.parent
P2 = REPO_ROOT / "paper2-interventional"

_spec = importlib.util.spec_from_file_location("mlp2", AQUI / "manifesto-lastro-p2.py")
mlp2 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mlp2)
RAIZ_ART, RAIZ_VER = mlp2.RAIZ_ART, mlp2.RAIZ_VER
MAN = RAIZ_ART / "MANIFESTO-LASTRO-P2.json"
ANTERIORES = RAIZ_ART / "manifestos-anteriores"


def git(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO_ROOT), *a], capture_output=True, text=True)


def hashear(p: Path) -> dict:
    if p.is_dir():
        hx, n, k = mlp2.sha256_dir(p)
        return dict(sha256=hx, bytes=n, tipo="diretorio", ficheiros=k)
    hx, n = mlp2.sha256(p)
    return dict(sha256=hx, bytes=n, tipo="ficheiro")


def versionado_limpo(p: Path) -> tuple[bool, str]:
    rel = p.relative_to(REPO_ROOT).as_posix()
    arquivos = [f for f in ([p] if p.is_file() else sorted(p.rglob("*"))) if f.is_file()]
    rastreados = set(git("ls-files", "--", rel).stdout.split("\n")) - {""}
    for f in arquivos:
        if f.relative_to(REPO_ROOT).as_posix() not in rastreados:
            return False, f"não versionado: {f.relative_to(REPO_ROOT)}"
    if git("diff", "--quiet", "HEAD", "--", rel).returncode != 0:
        return False, "difere de HEAD"
    # versionado só conta se estiver EMPURRADO: commit local não é cópia fora da máquina
    h = git("rev-parse", f"HEAD:{rel}").stdout.strip()
    o = git("rev-parse", f"origin/main:{rel}").stdout.strip()
    if not h or h != o:
        return False, "versionado mas não em origin/main (não empurrado)"
    return True, rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rotulo", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("rels", nargs="+")
    a = ap.parse_args()

    txt_old = MAN.read_text()
    old = json.loads(txt_old)
    sha_old = hashlib.sha256(txt_old.encode()).hexdigest()
    ja = {e["nome"]: e for e in old["artefatos"]}
    head = git("rev-parse", "HEAD").stdout.strip()
    agora = datetime.datetime.now(datetime.timezone.utc).isoformat()

    novas, copias, erros = [], [], []
    for rel in a.rels:
        src = Path(rel) if Path(rel).is_absolute() else P2 / rel
        nome = src.name if src.is_relative_to(RAIZ_ART) or src.is_relative_to(RAIZ_VER) \
            else src.relative_to(P2).as_posix()
        if not src.exists():
            erros.append(f"AUSENTE: {rel}"); continue
        h = hashear(src)
        if nome in ja:
            if ja[nome]["sha256"] == h["sha256"]:
                print(f"  = já no manifesto, idêntico: {nome}"); continue
            erros.append(f"JÁ NO MANIFESTO COM OUTRO HASH: {nome}"); continue
        e = dict(nome=nome)
        if src.is_relative_to(RAIZ_ART) or src.is_relative_to(RAIZ_VER):
            e.update(caminho=str(src), **h, versionado=False)
        else:
            ok, info = versionado_limpo(src)
            if ok:
                obj = git("rev-parse", f"HEAD:{info}").stdout.strip()
                e.update(caminho=str(src), **h, versionado=True,
                         git_commit=head, git_objeto=obj)
            else:
                dst = RAIZ_ART / a.rotulo / src.relative_to(P2)
                if dst.exists() and hashear(dst)["sha256"] != h["sha256"]:
                    erros.append(f"DESTINO EXISTE COM OUTRO CONTEÚDO (não sobrescrevo): {dst}")
                    continue
                copias.append((src, dst))
                e.update(caminho=str(dst), **h, versionado=False,
                         origem=str(src), motivo_copia=info)
        e.update(adicionado_em=agora, adicionado_por=a.rotulo)
        novas.append(e)

    for x in erros:
        print("🔴", x, file=sys.stderr)
    if erros:
        return 1
    for e in novas:
        tag = "git" if e["versionado"] and "git_commit" in e else ("cópia" if "origem" in e else "lastro")
        print(f"  + {e['sha256'][:12]}…  {e['bytes']:>10}  {tag:6} {e['nome']}")
    if a.dry_run or not novas:
        print(f"{'dry-run: ' if a.dry_run else ''}{len(novas)} a acrescentar"); return 0

    # cópias para dentro de RAIZ_ART, com hash recalculado na cópia
    for src, dst in copias:
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
        if hashear(dst)["sha256"] != hashear(src)["sha256"]:
            print(f"🔴 cópia diverge da origem: {dst}", file=sys.stderr); return 1

    ANTERIORES.mkdir(exist_ok=True)
    guarda = ANTERIORES / f"MANIFESTO-LASTRO-P2.{sha_old[:12]}.json"
    if not guarda.exists():
        guarda.write_text(txt_old)

    new = dict(old)
    new["artefatos"] = old["artefatos"] + novas
    new["n_artefatos"] = len(new["artefatos"])
    new["bytes_totais"] = sum(e["bytes"] for e in new["artefatos"])
    new.setdefault("extensoes", []).append(dict(
        em=agora, rotulo=a.rotulo, adicionados=len(novas),
        bytes_adicionados=sum(e["bytes"] for e in novas),
        manifesto_anterior_sha256=sha_old, manifesto_anterior_guardado=str(guarda),
        nota="extensão por scripts/estende-lastro-p2.py; NÃO rodar manifesto-lastro-p2.py "
             "sem --hash-dir: ele regenera do Apêndice B e apaga as extensões"))
    txt_new = json.dumps(new, indent=2, ensure_ascii=False)

    # prova: o bloco das entradas antigas é byte-idêntico no ficheiro novo
    # fecho do array = o PRIMEIRO "\n  ]" depois da abertura (entradas têm indentação ≥ 4).
    # A 1ª versão usava o ÚLTIMO, que depois da 1ª extensão é o fecho de "extensoes": o
    # bloco antigo engolia as extensões e o guarda abortava (2026-10-05, abortou certo).
    bloco_old = txt_old.split('"artefatos": [', 1)[1].split("\n  ]", 1)[0]
    if bloco_old + ",\n    {" not in txt_new:
        print("🔴 entradas antigas NÃO ficariam byte-idênticas — abortado", file=sys.stderr)
        return 1
    MAN.write_text(txt_new)
    sha_new = hashlib.sha256(txt_new.encode()).hexdigest()
    print(f"manifesto: {sha_old[:12]}… → {sha_new[:12]}…  ({old['n_artefatos']} → "
          f"{new['n_artefatos']} artefatos; antigas byte-idênticas: {len(old['artefatos'])}/"
          f"{len(old['artefatos'])}); anterior guardado em {guarda}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
