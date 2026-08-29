#!/usr/bin/env python3
"""
pool-elegivel.py — quantos chunks o canal de cobertura CONSEGUE ver, e ele os esgota?

Substitui a explicação do §4.3.1 que a predição de 29/08 refutou. A história antiga era
"cada lote de ingestão alimenta o canal por 7 dias e expira". Ela estava errada por
generalizar a janela de **um** sub-pool para um lote que vive no **outro**:

| sub-pool | padrões de `source_file` | janela |
|---|---|---|
| por agente | `sessions/<agente>/%` (via `scopePatterns`) | `freshMaxAgeDays = 7` |
| global | `memory/entities/%` **e** `memory/lessons.md` (`GLOBAL_FRESH_PATTERNS`) | `freshGlobalMaxAgeDays = 30` |

O lote de 09–10/08 era todo `sessions/boris/…` ⇒ agente ⇒ parou limpo aos 7,0 dias. O de
21–22/08 é `entities/%` + `lessons.md` ⇒ global ⇒ seguia servido aos 7,4. As duas
observações são consistentes; o erro foi tratá-las como o mesmo canal.

⚠️ **`brief_log` não registra por qual canal cada linha foi servida.** Não há coluna de
origem. Logo "o lote continua sendo servido" é afirmação sobre a UNIÃO dos canais e não
diz nada sobre a cobertura especificamente. Qualquer script que conte serves sem separar
por elegibilidade está medindo os dois somados — foi o que `ciclo-do-lote.py` fez, e é por
isso que o guarda do corte dele acusou violação onde não havia: parte dos serves vinha do
pool principal, que não tem filtro de idade nenhum.

Aqui a atribuição é por **elegibilidade reconstruída do predicado do código**, não por
adivinhação: um chunk que não passa o predicado do canal não pode ter sido servido por
ele.

⚠️ **Uma constante que eu tinha na memória estava desatualizada, e ela quase virou o
achado.** Em 19/08 `GLOBAL_FRESH_PATTERNS` era só `["memory/entities/%"]`, e o conteúdo
havia migrado para `memory/lessons.md` — padrão órfão, mecanismo inerte. Isso **foi
consertado**: hoje o código tem os dois padrões. Construí uma explicação inteira sobre a
memória antes de ler o fonte, e ela dava 55 elegíveis onde o predicado real dá 108.
Constante memorizada não substitui `grep` no código.

Uso:
  pool-elegivel.py --db nox-mem.db --dia 2026-08-29 [--json] [--out ...]
"""
import argparse
import json
import sqlite3
import sys

# Verbatim de `src/api/brief.ts:135` e `brief-diversity.ts:59-62`, em 2026-08-29.
GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"]
FRESH_GLOBAL_MAX_AGE_DAYS = 30
FRESH_MIN_IMP = 0.7
FRESH_MIN_PAIN = 0.7
FRESH_SLOTS = 2  # slots de cobertura por brief


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--dia", required=True, help="YYYY-MM-DD")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)

    # Predicado do canal global, montado do fonte. O `OR` no piso é do código
    # (`brief.ts:642`) — contar como `AND` dá 13 onde o certo dá 128, e foi erro meu
    # numa primeira passagem.
    pat = " OR ".join(["source_file LIKE ?"] * len(GLOBAL_FRESH_PATTERNS))
    onde = (f"julianday(?) - julianday(COALESCE(source_date, created_at)) <= ? "
            f"AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?) "
            f"AND ({pat})")
    # âncora temporal: fim do dia medido, não `now` — senão o script devolve outra
    # resposta a cada hora e a série deixa de ser comparável.
    ref = f"{a.dia} 23:59:59"
    args = [ref, FRESH_GLOBAL_MAX_AGE_DAYS, FRESH_MIN_IMP, FRESH_MIN_PAIN,
            *GLOBAL_FRESH_PATTERNS]

    pool = c.execute(f"SELECT COUNT(*) FROM chunks WHERE {onde}", args).fetchone()[0]
    nunca = c.execute(
        f"SELECT COUNT(*) FROM chunks WHERE {onde} "
        f"AND id NOT IN (SELECT chunk_id FROM brief_log)", args).fetchone()[0]
    servidos_dia = c.execute(
        f"SELECT COUNT(*) FROM chunks WHERE {onde} AND id IN "
        f"(SELECT chunk_id FROM brief_log WHERE substr(served_at,1,10) = ?)",
        args + [a.dia]).fetchone()[0]
    briefs = c.execute(
        "SELECT COUNT(DISTINCT brief_id) FROM brief_log WHERE substr(served_at,1,10)=?",
        (a.dia,)).fetchone()[0]
    corpus = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    slots = briefs * FRESH_SLOTS
    saida = {
        "dia": a.dia, "corpus": corpus,
        "predicado": {"padroes": GLOBAL_FRESH_PATTERNS,
                      "idade_max_dias": FRESH_GLOBAL_MAX_AGE_DAYS,
                      "piso": f"importance >= {FRESH_MIN_IMP} OR pain >= {FRESH_MIN_PAIN}"},
        "pool_elegivel": pool,
        "pct_do_corpus": round(100 * pool / corpus, 3) if corpus else None,
        "nunca_servidos_no_pool": nunca,
        "servidos_no_dia": servidos_dia,
        "cobertura_do_pool_no_dia": round(100 * servidos_dia / pool, 1) if pool else None,
        "briefs_no_dia": briefs,
        "slots_de_cobertura_no_dia": slots,
        "slots_por_candidato": round(slots / pool, 1) if pool else None,
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) medir um dia sem brief nenhum devolveria 0% de cobertura, que se leria como
    #     "o canal não serviu" quando o certo é "não houve medição".
    if briefs == 0:
        print(f"⛔ {a.dia} não tem brief nenhum — 'cobertura 0%' aqui seria ausência de "
              f"medição lida como resultado.", file=sys.stderr)
        return 1
    # (2) servido-mas-não-elegível é impossível sob o predicado reconstruído; se
    #     acontecer, o predicado deste script divergiu do código.
    if servidos_dia > pool:
        print(f"⛔ {servidos_dia} servidos do pool contra {pool} elegíveis — o predicado "
              f"deste script não é o do código.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"dia {a.dia}")
        print(f"  pool elegível do canal global : {pool} de {corpus} "
              f"({saida['pct_do_corpus']}% do corpus)")
        print(f"  nunca servidos dentro do pool : {nunca}")
        print(f"  servidos no dia               : {servidos_dia} "
              f"({saida['cobertura_do_pool_no_dia']}% do pool)")
        print(f"  briefs / slots de cobertura   : {briefs} / {slots}")
        print(f"  slots por candidato elegível  : {saida['slots_por_candidato']}×")
        if saida["cobertura_do_pool_no_dia"] == 100.0:
            print("  ⇒ o pool é ESGOTADO no dia: a ordenação por last_served ordena, "
                  "mas não exclui ninguém.")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
