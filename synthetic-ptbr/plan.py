#!/usr/bin/env python3
"""Plan the synthetic PT-BR corpus: files, planted facts, variants, negatives, queries, labels.

  python3 -I synthetic-ptbr/plan.py            write plan/plan.json and plan/COVERAGE.md
  python3 -I synthetic-ptbr/plan.py --check    regenerate in memory; exit 1 if the committed
                                               files differ (the plan is fixed before generation)

Deterministic: everything comes from SEED. Nothing here calls a model or the network.

What is planted (PLANO.md, «Objetivo (2026-11-25)», after the Codex and Kimi challenge):
  - each FACT is (entity, attribute, value); the value is invented and unique, and has FORMS
    (literal + declared variants, e.g. "3.417" and "3417"). Its PRIMARY sentence uses the literal;
    PARAPHRASE positives, written by this script, use a variant;
  - context NEGATIVES carry the same entity and attribute and a DIFFERENT invented value, in a
    rejected or superseded context: lexically close to the query, and labelled not relevant;
  - DUPLICATES repeat a primary sentence as a standalone paragraph in the same file;
  - FALSE-PREMISE queries ask an attribute that no file states for that entity;
  - OPERATION targets: facts whose primary lives alone in a dedicated file, one operation each
    (the matrix of PLANO.md), so an operation never touches another fact's evidence.
Labels: T (latent truth) = primary + paraphrases; R (registered) = primary + each paraphrase with
probability R_KEEP, drawn here, before any ranking exists.
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import s_common as C  # noqa: E402

SEED = 20261125
R_KEEP = 0.25

AGENTS = ["Sabiá", "Jatobá", "Quaresmeira", "Ipê", "Tucano"]
BOOKS = ["O Rio Sem Margem", "Cartas de um Farol Apagado", "A Cidade dos Relógios Parados",
         "Mapa das Marés Altas", "O Inverno de Vila Aurora", "Sal e Ferrugem",
         "Os Cadernos do Sótão", "Pequeno Atlas das Chuvas", "Ninguém Mora no Quinto Andar",
         "A Última Linha do Bonde", "Vento Norte sobre a Serra Baixa", "O Jardim de Cera"]
AUTHORS = ["Ismênia Valadares Tor", "Bartolomeu Quintanilha Reis", "Celeste Arruda Mourão",
           "Teodoro Lins Avelar", "Marieta Sousa Brandão", "Osório Fagundes Lemos"]
PRINTERS = ["Gráfica Pedra Lisa", "Gráfica Três Ventos", "Gráfica Agulha de Ouro",
            "Gráfica Lumiar Offset"]
PROJECTS = ["Coleção Faróis", "Clube de Leitura de Março", "Feira do Livro de Vila Aurora",
            "Reedição dos Cadernos", "Audiolivros da Casa", "Site Novo da Editora"]
TOPICS = ["revisão de provas", "escolha de capa", "conversa com livrarias", "planejamento das redes",
          "ajuste de cronograma", "conversa com a tradutora", "inventário do depósito",
          "preparação de feira", "compra de papel", "orientação aos estagiários",
          "leitura de originais", "atendimento a leitores", "release para a imprensa",
          "organização do arquivo", "parceria com bibliotecas", "fotos para divulgação",
          "ajuste na diagramação", "reunião de pauta", "cobrança de direitos", "logística de envio"]

MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro"]
UNITS = ["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
TEENS = ["dez", "onze", "doze", "treze", "catorze", "quinze", "dezesseis", "dezessete",
         "dezoito", "dezenove"]
TENS = ["", "", "vinte", "trinta", "quarenta"]

# Coverage targets (the matrix of PLANO.md). The planner fails if it cannot meet them.
N_FACTS = 45
N_FALSE_PREMISE = 5
N_ENTITY_PRIMARY = 10
OPERATIONS = ["reingest_unchanged", "edit_outside_span", "edit_inside_span",
              "rename_with_reingest", "rename_without_reingest", "delete"]
N_PER_OPERATION = 5
N_DUPLICATE = 4
PARAPHRASE_COUNTS = [0] * 20 + [1] * 15 + [2] * 5 + [3] * 5      # 45 facts
N_NEG_REJECTED, N_NEG_SUPERSEDED = 8, 7
N_DAILY, N_DECISIONS, N_LESSONS = 130, 22, 20


def extenso(n):
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEENS[n - 10]
    t, u = divmod(n, 10)
    return TENS[t] + ("" if u == 0 else " e " + UNITS[u])


def slug(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "-".join("".join(c if c.isalnum() else " " for c in s).split())


# ── value generators: each returns (literal, [forms]) ──────────────────────────────────────────
def v_tiragem(rng):
    n = rng.choice([x for x in range(1203, 8990) if x % 100 and x % 10])
    lit = f"{n // 1000}.{n % 1000:03d}"
    return lit, [lit, str(n)]


def v_preco(rng):
    lit = f"R$ {rng.randint(39, 98)},{rng.choice(range(15, 90, 5)):02d}"
    return lit, [lit, lit[3:] + " reais"]


def v_reais(rng, lo, hi):
    n = rng.choice([x for x in range(lo, hi, 10) if x % 100])
    lit = f"R$ {n // 1000}.{n % 1000:03d}"
    return lit, [lit, lit[3:] + " reais"]


def v_data(rng):
    d, m = rng.randint(2, 27), rng.randint(7, 11)          # no daily note falls in Jul–Nov 2027
    return f"{d:02d}/{m:02d}/2027", [f"{d:02d}/{m:02d}/2027", f"{d} de {MONTHS[m - 1]} de 2027"]


def v_code(rng, prefix, digits=False):
    alpha = "0123456789" if digits else "ACDEFHJKMNPQRTUVWXY3479"
    lit = prefix + "".join(rng.choice(alpha) for _ in range(5 if digits else 4))
    return lit, [lit]


def v_prazo(rng):
    d = rng.choice([x for x in range(11, 48) if x % 7 and x not in (15, 20, 30, 40, 45)])
    return f"{d} dias", [f"{d} dias", f"{extenso(d)} dias"]


# attribute: entity kind, value generator, question, primary, paraphrase, rejected, superseded.
# The paraphrase slot holds three templates, one per paraphrase of the same fact.
# {E} entity name, {v} literal, {v2} last form (the variant; the literal when there is none),
# {vn} the negative's literal.
ATTRS = {
    "tiragem": ("book", v_tiragem, "Qual é a tiragem inicial de {E}?",
                "A tiragem inicial de {E} ficou definida em {v} exemplares.",
                ("Para {E}, a primeira impressão sai com {v2} cópias.",
                 "A gráfica confirmou {v2} cópias de {E} na primeira leva.",
                 "Ficou acertado: {v2} cópias de {E} para começar."),
                "Chegou a circular a proposta de imprimir {vn} exemplares de {E}, mas ela foi descartada.",
                "A conta antiga previa {vn} exemplares para {E}, número que depois foi revisto."),
    "preco": ("book", v_preco, "Qual é o preço de capa de {E}?",
              "O preço de capa de {E} foi fixado em {v}.",
              ("{E} chega às livrarias custando {v2}.",
               "Nas livrarias, {E} vai sair por {v2}.",
               "O leitor vai pagar {v2} por {E}."),
              "O comercial sugeriu vender {E} a {vn}, sugestão que não passou.",
              "A primeira estimativa de preço para {E} era {vn}, valor depois abandonado."),
    "lancamento": ("book", v_data, "Quando é o lançamento de {E}?",
                   "O lançamento de {E} ficou marcado para {v}.",
                   ("A noite de autógrafos de {E} acontece em {v2}.",
                   "{E} chega ao público em {v2}.",
                   "A festa de {E} ficou para {v2}."),
                   "Houve quem defendesse lançar {E} em {vn}, mas a ideia não foi adiante.",
                   "Antes, o lançamento de {E} estava previsto para {vn}, data que caiu."),
    "pedido": ("book", lambda r: v_code(r, "PED-", digits=True),
               "Qual é o número do pedido de impressão de {E}?",
               "O pedido de impressão de {E} na gráfica recebeu o número {v}.",
               ("No sistema da gráfica, {E} aparece sob o pedido {v2}.",
               "Para acompanhar {E} na gráfica, use o pedido {v2}.",
               "A nota de {E} cita o pedido {v2}."),
               "Um pedido {vn} chegou a ser aberto para {E} por engano e foi cancelado.",
               "O pedido {vn} de {E} foi substituído por um novo."),
    "adiantamento": ("author", lambda r: v_reais(r, 8010, 24990), "Qual é o adiantamento de {E}?",
                     "O adiantamento de {E} ficou em {v}.",
                     ("{E} recebe {v2} de adiantamento pelo contrato.",
                     "Já foram reservados {v2} para o adiantamento de {E}.",
                     "O financeiro separou {v2} para adiantar a {E}."),
                     "{E} chegou a pedir {vn} de adiantamento, mas a editora não aceitou.",
                     "A proposta inicial de adiantamento para {E} era {vn} e foi renegociada."),
    "contrato_autor": ("author", lambda r: v_code(r, "AUT-"), "Qual é o código do contrato de {E}?",
                       "O contrato de {E} com a editora tem o código {v}.",
                       ("Na pasta jurídica, o contrato de {E} está arquivado como {v2}.",
                       "Quem procurar o contrato de {E} deve buscar por {v2}.",
                       "A referência {v2} identifica o acordo com {E}."),
                       "O código {vn} chegou a ser reservado para o contrato de {E}, mas não foi usado.",
                       "O código {vn} era do contrato anterior de {E}, já encerrado."),
    "contrato_grafica": ("printer", lambda r: v_code(r, "GRF-"),
                         "Qual é o código do contrato com a {E}?",
                         "O contrato com a {E} tem o código {v}.",
                         ("Na pasta de fornecedores, a {E} aparece com o contrato {v2}.",
                         "Toda cobrança da {E} cita o contrato {v2}.",
                         "O acordo vigente com a {E} é o {v2}."),
                         "O código {vn} foi proposto para o contrato com a {E}, mas recusado.",
                         "O código {vn} era do contrato antigo com a {E}, já encerrado."),
    "prazo": ("project", v_prazo, "Qual é o prazo de {E}?",
              "O prazo de {E} ficou em {v}.",
              ("A equipe tem {v2} para concluir {E}.",
              "{E} precisa estar pronto em {v2}.",
              "Sobram {v2} de trabalho para fechar {E}."),
              "Alguém propôs um prazo de {vn} para {E}, mas não houve acordo.",
              "O cronograma antigo de {E} previa {vn}, e foi refeito."),
    "orcamento": ("project", lambda r: v_reais(r, 2010, 7990), "Qual é o orçamento de {E}?",
                  "O orçamento aprovado para {E} é de {v}.",
                  ("{E} vai custar {v2} no total.",
                  "Foram liberados {v2} para {E}.",
                  "A verba de {E} soma {v2}."),
                  "Um orçamento de {vn} para {E} foi apresentado e recusado.",
                  "A primeira versão do orçamento de {E} era de {vn}, valor revisto depois."),
}
KIND_ENTITIES = {"book": BOOKS, "author": AUTHORS, "printer": PRINTERS, "project": PROJECTS}
KIND_DIR = {"book": "livros", "author": "autores", "printer": "fornecedores", "project": "projetos"}


class PlanError(Exception):
    pass


def fresh_value(rng, gen, used_pairs, value_id):
    """Draw until no form collides with any form already planted."""
    for _ in range(500):
        lit, forms = gen(rng)
        cand = [(value_id, f) for f in forms]
        if not C.form_collisions(used_pairs + cand):
            used_pairs.extend(cand)
            return lit, forms
    raise PlanError(f"no collision-free value for {value_id}")


def build(seed=SEED):
    rng = random.Random(seed)

    # ── files ────────────────────────────────────────────────────────────────────────────────
    files = []
    entity_file = {}
    for kind, names in KIND_ENTITIES.items():
        for name in names:
            path = f"memory/entities/{KIND_DIR[kind]}/{slug(name)}.md"
            entity_file[name] = path
            files.append({"path": path, "kind": "entity", "entity_kind": kind, "entity": name})
    import datetime as dt
    days = [dt.date(2027, 1, 4) + dt.timedelta(days=i) for i in range(178)]   # 04/01 .. 30/06/2027
    for d in sorted(rng.sample(days, N_DAILY)):
        files.append({"path": f"memory/{d.isoformat()}.md", "kind": "daily", "date": d.isoformat()})
    kinds = ["decision"] * N_DECISIONS + ["lesson"] * N_LESSONS
    rng.shuffle(kinds)
    for i, (d, kind) in enumerate(zip(sorted(rng.sample(days, len(kinds))), kinds)):
        files.append({"path": f"memory/{kind}s/{d.isoformat()}-{kind}-{i:02d}.md",
                      "kind": kind, "date": d.isoformat()})
    if len(files) != 28 + N_DAILY + N_DECISIONS + N_LESSONS:
        raise PlanError(f"file count {len(files)}")
    for f in files:
        f["author_agent"] = rng.choice(AGENTS)
        f["topics"] = rng.sample(TOPICS, 2)
        f["items"] = []
    by_path = {f["path"]: f for f in files}

    # ── facts ───────────────────────────────────────────────────────────────────────────────
    combos = [(a, e) for a, spec in ATTRS.items() for e in KIND_ENTITIES[spec[0]]]
    rng.shuffle(combos)
    fact_combos, rest = combos[:N_FACTS], combos[N_FACTS:]
    premise_combos = rest[:N_FALSE_PREMISE]
    used = []
    facts = []
    for i, (attr, ent) in enumerate(fact_combos):
        spec = ATTRS[attr]
        fid = f"F{i:02d}"
        lit, forms = fresh_value(rng, spec[1], used, fid)
        facts.append({"id": fid, "attribute": attr, "entity": ent, "entity_kind": spec[0],
                      "literal": lit, "forms": forms, "question": spec[2].format(E=ent),
                      "negatives": [], "paraphrases": [], "operation": None,
                      "duplicate": False, "primary": None})

    # roles, drawn in a fixed order so the matrix is met by construction and checked below
    order = list(range(N_FACTS))
    rng.shuffle(order)
    entity_ids = order[:N_ENTITY_PRIMARY]
    rest_ids = [i for i in order if i not in entity_ids]
    op_ids = rest_ids[:len(OPERATIONS) * N_PER_OPERATION]
    free_ids = rest_ids[len(op_ids):]
    dup_ids = free_ids[:N_DUPLICATE]
    paras = PARAPHRASE_COUNTS[:]
    rng.shuffle(paras)
    neg_ids = rng.sample(range(N_FACTS), N_NEG_REJECTED + N_NEG_SUPERSEDED)

    # operation targets live alone in a decision or lesson file; everything else goes in daily notes
    dedicated_pool = [f["path"] for f in files if f["kind"] in ("decision", "lesson")]
    rng.shuffle(dedicated_pool)
    if len(dedicated_pool) < len(op_ids):
        raise PlanError("not enough decision/lesson files for the operation targets")
    dedicated = dedicated_pool[:len(op_ids)]
    shared_daily = [f["path"] for f in files if f["kind"] == "daily"]

    def add_item(path, item):
        by_path[path]["items"].append(item)

    for k, i in enumerate(op_ids):
        facts[i]["operation"] = OPERATIONS[k // N_PER_OPERATION]
    for i in range(N_FACTS):
        f = facts[i]
        spec = ATTRS[f["attribute"]]
        primary_text = spec[3].format(E=f["entity"], v=f["literal"])
        if i in entity_ids:
            path, section = entity_file[f["entity"]], "compiled"
        elif i in op_ids:
            path, section = dedicated[op_ids.index(i)], None
        else:
            path, section = rng.choice(shared_daily), None
        f["primary"] = {"id": f"{f['id']}-P", "path": path, "section": section, "text": primary_text}
        add_item(path, {"id": f"{f['id']}-P", "role": "primary", "value": f["id"],
                        "section": section, "text": primary_text,
                        "count": 2 if i in dup_ids else 1})
        f["duplicate"] = i in dup_ids
        taken = {path}
        for j in range(paras[i]):
            ppath = rng.choice([p for p in shared_daily if p not in taken])
            taken.add(ppath)
            text = spec[4][j].format(E=f["entity"], v=f["literal"], v2=f["forms"][-1])
            pid = f"{f['id']}-A{j}"
            f["paraphrases"].append({"id": pid, "path": ppath, "text": text})
            add_item(ppath, {"id": pid, "role": "paraphrase", "value": f["id"], "section": None,
                             "text": text, "count": 1})
    for k, i in enumerate(neg_ids):
        f = facts[i]
        spec = ATTRS[f["attribute"]]
        nid = f"{f['id']}-N0"
        lit, forms = fresh_value(rng, spec[1], used, nid)
        kind = "rejected" if k < N_NEG_REJECTED else "superseded"
        text = (spec[5] if kind == "rejected" else spec[6]).format(E=f["entity"], vn=lit)
        npath = rng.choice([p for p in shared_daily
                            if p != f["primary"]["path"] and p not in {a["path"] for a in f["paraphrases"]}])
        f["negatives"].append({"id": nid, "kind": kind, "literal": lit, "forms": forms,
                               "path": npath, "text": text})
        add_item(npath, {"id": nid, "role": "negative", "value": nid, "section": None,
                         "text": text, "count": 1})

    # registered labels R: primary always; each paraphrase kept with probability R_KEEP
    queries = []
    for f in facts:
        t = [f["primary"]["id"]] + [a["id"] for a in f["paraphrases"]]
        r = [f["primary"]["id"]] + [a["id"] for a in f["paraphrases"] if rng.random() < R_KEEP]
        queries.append({"id": f"Q{f['id'][1:]}", "kind": "fact", "fact": f["id"],
                        "text": f["question"], "T": t, "R": r,
                        "negatives": [n["id"] for n in f["negatives"]]})
    for k, (attr, ent) in enumerate(premise_combos):
        queries.append({"id": f"QP{k}", "kind": "false_premise", "fact": None,
                        "attribute": attr, "entity": ent,
                        "text": ATTRS[attr][2].format(E=ent), "T": [], "R": [], "negatives": []})

    plan = {"seed": seed, "r_keep": R_KEEP, "agents": AGENTS, "operations": OPERATIONS,
            "files": files, "facts": facts, "queries": queries}
    plan["coverage"] = coverage(plan)
    verify(plan)
    return plan


def coverage(plan):
    facts = plan["facts"]
    files = plan["files"]
    return {
        "files_total": len(files),
        "files_by_kind": {k: sum(f["kind"] == k for f in files)
                          for k in ("entity", "daily", "decision", "lesson")},
        "queries_total": len(plan["queries"]),
        "fact_queries": len(facts),
        "false_premise_queries": sum(q["kind"] == "false_premise" for q in plan["queries"]),
        "facts_by_relevant_count": {str(n): sum(1 + len(f["paraphrases"]) == n for f in facts)
                                    for n in (1, 2, 3, 4)},
        "facts_with_variant_paraphrase": sum(bool(f["paraphrases"]) and len(f["forms"]) > 1
                                             for f in facts),
        "facts_with_negative": {k: sum(any(n["kind"] == k for n in f["negatives"]) for f in facts)
                                for k in ("rejected", "superseded")},
        "facts_with_duplicate_primary": sum(f["duplicate"] for f in facts),
        "facts_with_entity_primary": sum(f["primary"]["section"] == "compiled" for f in facts),
        "facts_by_operation": {op: sum(f["operation"] == op for f in facts)
                               for op in plan["operations"]},
        "facts_by_attribute": {a: sum(f["attribute"] == a for f in facts) for a in ATTRS},
        "queries_where_R_is_incomplete": sum(len(q["R"]) < len(q["T"]) for q in plan["queries"]),
    }


def verify(plan):
    """The invariants the rest of the pipeline relies on. A failure here is a planner bug."""
    cov = plan["coverage"]
    want = {"files_total": 200, "fact_queries": N_FACTS, "false_premise_queries": N_FALSE_PREMISE,
            "facts_with_duplicate_primary": N_DUPLICATE,
            "facts_with_entity_primary": N_ENTITY_PRIMARY}
    for k, v in want.items():
        if cov[k] != v:
            raise PlanError(f"coverage {k}={cov[k]}, want {v}")
    if any(v != N_PER_OPERATION for v in cov["facts_by_operation"].values()):
        raise PlanError(f"operations {cov['facts_by_operation']}")
    if cov["facts_with_negative"] != {"rejected": N_NEG_REJECTED, "superseded": N_NEG_SUPERSEDED}:
        raise PlanError(f"negatives {cov['facts_with_negative']}")
    bad = C.form_collisions(C.all_value_forms(plan))
    if bad:
        raise PlanError(f"value collisions: {bad[:3]}")
    # an operation target's file holds that fact's primary and nothing else
    paths = {f["path"]: f for f in plan["files"]}
    for f in plan["facts"]:
        if f["operation"]:
            items = paths[f["primary"]["path"]]["items"]
            if [it["id"] for it in items] != [f["primary"]["id"]]:
                raise PlanError(f"{f['id']}: operation file is shared: {[it['id'] for it in items]}")
    # a false premise is really absent: no fact plants that (attribute, entity)
    planted = {(f["attribute"], f["entity"]) for f in plan["facts"]}
    for q in plan["queries"]:
        if q["kind"] == "false_premise" and (q["attribute"], q["entity"]) in planted:
            raise PlanError(f"{q['id']} premise is planted")
    # every primary/paraphrase/negative text is distinct, so a text check can locate it
    texts = [it["text"] for f in plan["files"] for it in f["items"]]
    if len(texts) != len(set(texts)):
        raise PlanError("two planted items share a text")


def coverage_md(plan):
    cov = plan["coverage"]
    lines = ["# Coverage of the synthetic corpus (generated by plan.py; do not edit)", "",
             f"Seed {plan['seed']}; registered labels keep each paraphrase with p = {plan['r_keep']}.",
             "Fixed before any text is generated and before any ranking exists.", "",
             "| what | count |", "|---|---|"]
    for k, v in cov.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                lines.append(f"| {k}: {kk} | {vv} |")
        else:
            lines.append(f"| {k} | {v} |")
    return "\n".join(lines) + "\n"


def main():
    try:
        plan = build()
    except PlanError as e:
        print(f"plan: FAIL {e}")
        return 1
    want = {C.PLAN_FILE: C.dump_json(plan), C.PLAN_DIR / "COVERAGE.md": coverage_md(plan)}
    if "--check" in sys.argv:
        diff = [p.name for p, s in want.items() if not p.exists() or p.read_text(encoding="utf-8") != s]
        print(f"plan --check: {'FAIL, differs: ' + ', '.join(diff) if diff else 'ok'}")
        return 1 if diff else 0
    C.PLAN_DIR.mkdir(exist_ok=True)
    for p, s in want.items():
        p.write_text(s, encoding="utf-8")
    print(json.dumps(plan["coverage"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
