#!/usr/bin/env python3
"""Teste de mutação para `claims_check.py` — cada guarda tem de MORDER.

POR QUE ISTO EXISTE
-------------------
Em 2026-09-03 eu rodei um censo de alegações de SOTA, ele classificou 26 linhas
como "SOTA de terceiros, legítimo", e eu **reportei isso sem ler nenhuma das
26**. Doze eram alegações próprias. O classificador usava "a frase menciona um
baseline" como prova de ser de terceiro — e toda alegação própria menciona o
baseline que alega bater. O filtro estava ANTICORRELACIONADO com o que devia
detectar, e nada revelou isso porque eu nunca o mutei.

Mutei ao final, depois de o escopo já ter sido reportado errado duas vezes. A
mutação achou o defeito em segundos.

⇒ **Um censo não é reportável antes de o próprio teste de mutação passar.**

E o teste tem de exigir a MENSAGEM, não só o `exit != 0`: um guarda que falha
pelo motivo errado passaria num teste que só olha o código de saída. Cada caso
aqui declara um marcador que a mensagem precisa conter.

Nada é escrito nos arquivos reais: cada mutação roda numa cópia em tempdir.

USO
---
    python3 claims_check_mutation_test.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).parent
PAPER = "paper-tecnico-nox-mem.md"
BIB = "refs.bib"
SCRIPT = "claims_check.py"
MANIFESTOS = ("authors-manifest.json", "bibitem-census.json", "q4-corridas-census.json")
# O abstract standalone entrou na copia em 2026-09-10: sem ele a perna de espelho
# acusa "ausente" em TODOS os casos e o baseline fica vermelho por falta de
# fixture, nao por defeito — a suite acusou isso na primeira corrida.
ABSTRACT = "abstract.md"


# O tamanho desta mutacao nao pode ser um literal. Ela ja morreu uma vez
# (2026-09-11): com a densidade em 2,08 bastavam ~200 palavras para furar o
# piso e 80 repeticoes sobravam; depois do corte para 2,47 passaram a faltar
# mais de 4.000 e a mutacao deixou de morder -- sem falhar, so parando de
# verificar. Derivar do estado fecha a classe: quantas palavras faltam HOJE
# para a densidade cair abaixo do piso, mais margem.
_FRASE_NEUTRA = (
    "The pipeline processes each file as it changes, and the resulting record "
    "is stored for later reading by whichever component asks for it next. "
)


def _repeticoes_para_furar_o_piso() -> int:
    """Repeticoes de `_FRASE_NEUTRA` que levam a densidade abaixo de DENSIDADE_PISO.

    Usa o MESMO tokenizador do guarda (`claims_check._densidade_check`): palavra
    e' todo token com ao menos um alfanumerico.
    """
    raiz = Path(__file__).resolve().parent
    md = (raiz / PAPER).read_text(encoding="utf-8")
    censo = json.loads((raiz / "bibitem-census.json").read_text(encoding="utf-8"))
    piso = float(
        re.search(r"^DENSIDADE_PISO\s*=\s*([0-9.]+)", (raiz / SCRIPT).read_text(encoding="utf-8"), re.M).group(1)
    )
    def conta(texto: str) -> int:
        return sum(1 for w in texto.split() if any(c.isalnum() for c in w))
    obras = len(censo["obra"])
    atual = conta(md)
    teto_de_palavras = obras / piso * 1000.0          # acima disto a densidade fura o piso
    faltam = teto_de_palavras - atual
    por_repeticao = conta(_FRASE_NEUTRA)
    reps = int(faltam / por_repeticao) + 12           # margem
    if reps <= 0:
        raise SystemExit(
            f"mutacao de densidade impossivel: o manuscrito ({atual} palavras) ja esta "
            f"acima do teto de {teto_de_palavras:.0f} com {obras} obras"
        )
    return reps


_REPS_PISO = _repeticoes_para_furar_o_piso()

# `contagem_sistemas_check` le artefatos FORA de paper/. Sem copia-los, a guarda
# acusa "eval/q4-comparison nao encontrado" em TODA mutacao — e a bateria inteira
# passaria pelo motivo errado, que e' o defeito que este arquivo existe para pegar.
ARTEFATOS = (
    "eval/q4-comparison/output/_aggregate.json",
    "eval/q4-comparison/output-2026-09-10/_aggregate.json",
)
RAIZ_REPO = AQUI.parent

# (nome, arquivo, de, para, marcador esperado na mensagem)
# `de=None` => append ao fim do arquivo.
CASOS = [
    (
        # O universal sobre a literatura nao e' verificavel sem survey exaustivo, e e'
        # dispensavel: o fato medido sustenta-se so.
        "universal sobre a literatura reintroduzido",
        PAPER, None,
        "\nAmong all memory systems, no published competitor reports retrieval latency in this band.\n",
        "universal sobre a literatura",
    ),
    (
        # Palavra promocional sobre trabalho proprio, num paper cujo §7.1 cita um
        # "breakthrough" passado como exemplo cautelar.
        "palavra promocional reintroduzida",
        PAPER, None,
        "\nThe Q3 IterC result is a breakthrough for high-level synthesis.\n",
        "palavra promocional",
    ),
    (
        # ⚠️ ESTA e' a que prova a ISENCAO, nao a deteccao. A L1079 contem a palavra
        # "breakthrough" como CITACAO de um overclaim sendo retratado, e sobrevive
        # porque a frase carrega a retratacao medida (5-batch contra 1). Quebrando o
        # marcador de retratacao NO GUARDA, a citacao tem de passar a ser acusada --
        # e' isso que mostra que a isencao esta a sustentar peso, em vez de a linha
        # apenas nao casar por acidente.
        "marcador de RETRATACAO quebrado no guarda",
        SCRIPT,
        "r\"5-batch reality|labelled\\s+\\S{0,2}breakthrough|overstatement|\"\n    r\"would have been overclaimed\"",
        "r\"NUNCA-CASA-NADA-XYZ\"",
        "palavra promocional",
    ),
    (
        # Citacao sem definicao rende marcador cru no PDF.
        "footnote citada e NAO definida",
        PAPER, None,
        "\nThis mechanism follows prior work[^naoexiste] on retrieval fusion.\n",
        "citada e nao tem defini",
    ),
    (
        # Definicao nunca citada = enchimento de bibliografia, que e' o defeito
        # que eu recusei cometer com HotpotQA/DPR/FiD.
        "footnote definida e NUNCA citada",
        PAPER, None,
        "\n[^orfa]: Some Author, *Some Paper*, 2024. arXiv:2401.00001.\n",
        "nunca citada",
    ),
    (
        # `[^hipporag2]` afirmava sistema academico sem localizador nenhum:
        # irresolvivel e' indistinguivel de inventada.
        "footnote ACADEMICA sem localizador resolvivel",
        PAPER,
        "doi:10.1561/1500000019. Cited in \u00a73.1",
        "Cited in \u00a73.1",
        "sem localizador",
    ),
    (
        # A regex de serie viva casava SO `94.9k`, forma que o paper nunca usou:
        # ele escrevia `~95k` e `94,936`, e os 8 guardas passavam com o defeito
        # presente em tres sitios. Este caso prende as grafias reais.
        "numero de serie viva na grafia que o paper REALMENTE usa",
        PAPER, None,
        "\nThe production corpus is now 67,724 chunks after the latest pass.\n",
        "número de série viva sem data na frase",
    ),
    (
        # O guarda de data NAO alcanca isto: a frase pode ter data e ainda
        # atribuir a contagem a populacao errada. Medido no mesmo dia, main store
        # = 67.724 e soma dos 7 = 79.220 -- 11.496 de diferenca.
        "mesma contagem atribuida a DUAS populacoes, ambas datadas",
        PAPER, None,
        "\nThe corpus held ~95k chunks across 7 databases as of 2026-09-09.\n",
        "populações diferentes",
    ),
    (
        "fence impar quebra toda varredura",
        PAPER, None, "\n```\n",
        "code fence",
    ),
    (
        "alegacao superlativa propria sem limitador",
        PAPER, None, "\nnox-mem achieves SOTA on both benchmarks.\n",
        "superlativa própria sem limitador",
    ),
    (
        "superlativo POR EXTENSO (a cegueira do censo original)",
        PAPER, None, "\nOur system is state-of-the-art on this task.\n",
        "superlativa própria sem limitador",
    ),
    (
        "entrada obsoleta na lista de permitidos = falso verde",
        PAPER, "reader SOTA numbers are published", "reader numbers exist",
        "SUPERLATIVO_PERMITIDO",
    ),
    (
        "sitio NOVO herdando a isencao por substring",
        # Alegação falsa que CONTÉM o trecho isento. Sem contagem esperada por
        # âncora, a isenção por substring a absolvia em silêncio — buraco real,
        # achado em 2026-09-04 ao generalizar a análise de um patch alheio.
        PAPER, None,
        "\nnox-mem is SOTA, and reader SOTA numbers are published elsewhere.\n",
        "herdando a isenção por substring",
    ),
    (
        "tabela de QA classico sem declarar split",
        PAPER, None, "\n| Beam Retrieval | 69.20% | +10.58 pp |\n",
        "não declara split",
    ),
    (
        "ID arXiv citado sem entrada bib",
        PAPER, None, "\nAs shown in (arxiv:9911.12345), this holds.\n",
        "não tem entrada",
    ),
    (
        # ⚠️ Este caso mutava o BIB para criar a condicao "divida ja paga". Deixou de
        # morder em 2026-09-09, quando as cinco dividas foram pagas e a BIB_DIVIDA
        # ficou VAZIA: com a lista vazia, nenhuma mutacao sobre o paper ou o bib
        # alcanca a perna -- ela continua correta e ficou sem caso. Correcao que
        # nenhum teste alcanca exige nomear o que a protege, e o que protege aqui e'
        # mutar o PROPRIO guarda: reintroduzir na lista um ID que ja tem entrada.
        # `_prepara` copia SCRIPT junto do paper e do bib, entao isso e' alcancavel.
        "divida bib ja paga e nao removida da lista (muta o GUARDA, lista vazia)",
        SCRIPT,
        "BIB_DIVIDA: dict[str, str] = {",
        'BIB_DIVIDA: dict[str, str] = {\n    "2104.08663": "reintroduzida pela mutacao",',
        "BIB_DIVIDA",
    ),
    (
        "evidencia nao-arquivavel AUMENTOU (ratchet)",
        PAPER, None, "\nEvidence in PR #999.\n",
        "AUMENTOU",
    ),
    (
        # Este caso existe porque o de cima NAO mordia quando o baseline estava
        # acima do valor medido (66 contra 53 reais): somar 1 cabia na folga.
        # Um ratchet afrouxado admite a diferenca em silencio, e a bateria nao
        # ve porque a mutacao e' menor que a folga. Com o baseline em 0
        # (2026-09-11, todas as referencias a PR removidas do manuscrito),
        # afrouxar passou a ser SUBIR o baseline, nao baixa-lo.
        "baseline do ratchet AFROUXADO acima do real",
        SCRIPT, "PR_BASELINE = 0", "PR_BASELINE = 26",
        "FROUXO",
    ),
    (
        "PR # como fonte em tabela de comparacao externa",
        PAPER, None, "\n| MemOS | 42.55% | dev | fonte (PR #998) |\n",
        "usa `PR #NNN` como fonte",
    ),
    (
        "numero de serie viva sem data",
        PAPER, None, "\nThe store holds 94.9k chunks today.\n",
        "série viva sem data",
    ),
    (
        "alegacao retratada reaparece sem enquadramento",
        PAPER, None, "\nWe report 58.62% and 73.37% on these tasks.\n",
        "dual_sota_classico",
    ),
    (
        "cross-backbone reaparece sem declarar o backbone",
        PAPER, None, "\nWe reach 63.28% and 88.42% overall.\n",
        "memos_cross_backbone",
    ),
    (
        "cross-metric reaparece sem declarar metrica",
        PAPER, None, "\nWe get 74.52% versus 66.88% there.\n",
        "locomo_cross_metric",
    ),
    (
        "aritmetica em pp misturando F1 e strict EM",
        PAPER, None, "\nThat leaves a 55 pp gap between F1 and strict EM.\n",
        "mistura F1 e EM",
    ),
    (
        # A perna de censo. A footnote e' CITADA e a autoria casa o manifesto de
        # proposito: sem isso o balanco e a correspondencia acusam primeiro, e a
        # prova nao distinguiria "a perna morde" de "outra decidiu antes".
        "footnote nova, citada e com autoria certa, FORA do censo de bibitems",
        PAPER, None,
        "\nA fourth axis follows prior work[^mutante-censo].\n"
        "\n[^mutante-censo]: Hu, Li, Gao, Chen, Bai, Xu, Lin, Li, Han, Pei & Deng, "
        "*Evaluating Long-Horizon Memory for Multi-Party Collaborative Dialogues*, "
        "2026. arXiv:2602.01313.\n",
        "nao esta no bibitem-census",
    ),
    (
        # Censo que classifica chave morta: o numerador da densidade fica maior
        # do que a bibliografia real.
        "censo classifica footnote que nao existe mais",
        "bibitem-census.json",
        '"obra": [', '"obra": [\n  "chave-fantasma",',
        "nao existe mais no manuscrito",
    ),
    (
        # O manuscrito trazia `arxiv:2402.17753` em MINUSCULAS (o LoCoMo, benchmark
        # central do §6) e a perna de autoria casava `arXiv:` case-sensitive. A/B
        # medido: com re.I a autoria inventada e' apanhada; sem, escapa inteira —
        # e os nomes deste caso sao os MESMOS tres que o #519 achou inventados.
        "footnote com id em MINUSCULAS e autoria inventada",
        PAPER, None,
        "\nA prior benchmark[^mut-caixa] motivates this.\n"
        "\n[^mut-caixa]: Yin, Ni & Peng, *Evaluating Very Long-Term Conversational "
        "Memory of LLM Agents*, ACL 2024. arxiv:2402.17753.\n",
        "nao constam da autoria",
    ),
    (
        # A perna de autoria do footnotes_check varre so corpos de footnote. As 11
        # linhas de PROSA que citam id com o autor ao lado nao passavam por perna
        # alguma — foi como 2402.17753 ficou fora do manifesto sem alarme.
        "prosa atribui id arXiv a autor que nao consta",
        PAPER,
        "LoCoMo (Maharana et al. 2024; arxiv:2402.17753)",
        "LoCoMo (Yin et al. 2024; arxiv:2402.17753)",
        "nao consta da autoria",
    ),
    (
        # Desde 2026-09-10 o paper diz `6,822` do corpus do rc4 (§6.3.2, §6.9) E do
        # indice do EverOS (§6.3.1) — medicoes diferentes que coincidem. A
        # coincidencia e' o achado; ler as duas como uma e' o defeito. A primeira
        # versao do guarda exigia os dois sistemas na MESMA frase e esta mutacao
        # passava incolume, porque deixa `nox-mem` numa frase e `EverOS` na
        # seguinte: a janela tem de ser o PARAGRAFO.
        "contagem de corpus de 2 sistemas com uma corrida so nomeada",
        PAPER,
        "from a **different run** (the 2026-09-10 EverOS ingest of \u00a76.3.1, not rc4, "
        "and therefore not a fourth column here): offered the same corpus, EverOS also "
        "retained **6,822**",
        "EverOS also retained **6,822**",
        "nomeia 1 corrida",
    ),
    (
        "paragrafo novo com 2 sistemas e nenhuma corrida nomeada",
        PAPER, None,
        "\nBoth nox-mem and EverOS retained 6,822 documents; Mem0 kept 6,830.\n",
        "nomeia 0 corrida",
    ),
    (
        # Instalado depois de acontecer: o PR que acrescentou 415 palavras ao
        # §6.3.1 — prosa densa e necessaria, sem referencia nova — levou a
        # densidade de 2,08 para 2,05, fora do piso, e os 14 guardas ficaram
        # verdes. A mutacao muta o MANUSCRITO e nao o censo: mutar o censo
        # aciona tambem o censo_bibitem_check e a prova nao discriminaria.
        # A frase e' neutra de proposito — nao dispara superlativo, serie viva,
        # populacao nem contagem de corpus.
        "prosa nova sem referencia derruba a densidade abaixo do piso",
        PAPER, None,
        "\n" + 'The pipeline processes each file as it changes, and the resulting record is stored for later reading by whichever component asks for it next. ' * _REPS_PISO + "\n",
        "abaixo do piso",
    ),
    (
        # A entrada do NOSSO sistema prometia "update with arXiv ID after
        # submission" enquanto o CITATION.cff registra a ausencia no arXiv como
        # FATO, nao tarefa. Duas fontes do mesmo repo em contradicao, e a que o
        # leitor segue e' a bibliografia.
        "entrada de bibliografia promete atualizacao futura",
        BIB, "doi          = {10.5281/zenodo.22649268},",
        "note2        = {update with arXiv ID after submission},",
        "promete atualizacao futura",
    ),
    (
        # Chave nas duas classes: a soma nao fecha e o numerador fica ambiguo.
        "censo classifica a mesma chave como obra E evidencia",
        "bibitem-census.json",
        '"evidencia": {', '"evidencia": {\n  "mem0": "duplicada",',
        "em duas classes",
    ),
    (
        # L5 (completude). Sem este caso, "a L5 nao acusa nada" seria
        # indistinguivel de "a L5 nao olha". Ela ja achou dois sitios que a
        # primeira versao do censo, montada a mao, tinha perdido — mas isso e'
        # historia, nao teste.
        "sitio de contagem NOVO, fora do censo",
        PAPER, None,
        "\n\nIn this revision four competitors could not produce a number at all.\n",
        "contagem/L5",
    ),
    (
        # A perna que importa: um gap FECHOU (artefato com numero em disco) e o
        # censo ainda diz que o sistema nao produziu. E' o cenario do Zep quando
        # a corrida dele fechar. Mutar o censo reproduz o estado sem mexer no disco.
        "gap fechou e o censo ainda diz SEM numero",
        "q4-corridas-census.json",
        '"produziu_numero": true,\n      "corridas": [\n        "2026-09-10"',
        '"produziu_numero": false,\n      "corridas": [\n        "2026-09-10"',
        "contagem/L2",
    ),
    (
        "censo declara ndcg que o artefato nao tem",
        "q4-corridas-census.json",
        '"ndcg10_no_artefato": 0.64553667642804',
        '"ndcg10_no_artefato": 0.7',
        "contagem/L1",
    ),
    (
        # Artefato em disco cujo sistema o censo nao declara NEM exclui.
        "alias do sistema sumiu do censo",
        "q4-corridas-census.json",
        '        "evermind",\n        "everos"',
        '        "evermind-com-outro-nome"',
        "contagem/L2",
    ),
    (
        # Sem este caso, "os quatro sitios canonicos passam" seria indistinguivel
        # de "a guarda os pula em silencio".
        "contagem presa a corrida canonica adulterada",
        PAPER,
        "**Two of the five competitors produced head-to-head quality numbers**",
        "**Three of the five competitors produced head-to-head quality numbers**",
        "canonica-produziram",
    ),
    (
        # A guarda tem de ACUSAR quando nao acha os artefatos, nao ficar calada
        # por falta do dado (regra 9 do CLAUDE.md).
        "guarda perde os artefatos e teria de calar",
        SCRIPT,
        '    for cand in (root, root.parent):\n        if (cand / "eval" / "q4-comparison").is_dir():\n            return cand\n    return None',
        "    return None",
        "eval/q4-comparison nao encontrado",
    ),
    (
        # O abstract standalone e' o texto que vai para o formulario de submissao e
        # nao era lido por guarda nenhuma — ficou em "two/three" enquanto o
        # manuscrito ja dizia "four/one".
        "abstract standalone com a contagem velha",
        ABSTRACT,
        "four (Mem0, agentmemory, EverOS, Zep)",
        "three (Mem0, agentmemory, EverOS, Zep)",
        "abs-produziram",
    ),
    (
        "abstract standalone com o numero de non-runs errado",
        ABSTRACT,
        "one (Letta) is a documented deployment non-run",
        "two (Letta) is a documented deployment non-run",
        "abs-nao",
    ),
    (
        # Sem sitios declarados a perna nao verifica nada; o verde seria decoracao.
        "censo sem sitios_abstract",
        "q4-corridas-census.json",
        '"sitios_abstract"',
        '"sitios_abstract_DESLIGADO"',
        "nao declara `sitios_abstract`",
    ),
    (
        # Prova que a perna usa a DERIVACAO do censo e nao um literal: reabrir o gap
        # do Zep muda o esperado de four para three sem tocar no abstract.
        "gap do Zep reaberto no censo — derivacao 4 volta a 3",
        "q4-corridas-census.json",
        '"zep"\n      ],\n      "produziu_numero": true',
        '"zep"\n      ],\n      "produziu_numero": false',
        "abs-produziram",
    ),
    (
        # A perna de unicidade. A mutacao faz DUAS footnotes ja classificadas como
        # `obra` apontarem para o mesmo arXiv id — que e' exatamente o estado em que
        # a densidade publicada (2,078) era na verdade 1,937. Mutar por id, e nao
        # acrescentando footnote nova, e' deliberado: footnote nova cairia primeiro
        # no `censo_bibitem_check` e a morte seria por outro motivo.
        "duas obras do censo apontando para o mesmo arXiv id",
        PAPER,
        "*MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers*, NeurIPS 2020. arXiv:2002.10957.",
        "*MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers*, NeurIPS 2020. arXiv:1901.04085.",
        "e' UMA obra contada",
    ),
]

# Controle NEGATIVO: texto inócuo não pode disparar nada.
CONTROLE = (PAPER, "\nThe pipeline indexes files as they change.\n")


def _prepara(tmp: Path) -> None:
    for f in (PAPER, BIB, SCRIPT, ABSTRACT, *MANIFESTOS):
        shutil.copy2(AQUI / f, tmp / f)
    for rel in ARTEFATOS:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RAIZ_REPO / rel, dst)


def _roda(tmp: Path) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(tmp / SCRIPT), "--root", str(tmp)],
        capture_output=True, text=True,
    )
    return p.returncode, p.stdout + p.stderr


def _classifica(rc: int, saida: str, marcador: str) -> str:
    """Veredicto de um caso de mutação: extraído para poder ser TESTADO.

    Existe por um furo que eu mesmo declarei e não havia fechado: os casos
    mutam o arquivo do paper, que é o input do PROCESSO FILHO, enquanto esta
    classificação roda no PAI. Envenenar o filho nunca exercita o pai — então
    se a checagem de marcador quebrasse, um guarda falhando pelo motivo errado
    passaria por 'mordeu' e a bateria diria 15/15.

    A forma que fecha isso é infrator sintético contra ESTA função, no próprio
    processo (ver `_meta_controle`). Diagnóstico e forma vindos da sessão do
    7_problems, onde a mesma classe apareceu como `${2@Q}` abortando o corpo da
    função antes do contador de falhas.
    """
    if rc == 0:
        return "nao_mordeu"
    if marcador not in saida:
        return "marcador_errado"
    return "ok"


def _meta_controle() -> list[str]:
    """Prova que `_classifica` distingue as três respostas, antes de qualquer caso.

    Sem isto, "15/15" é compatível com a classificação estar quebrada.
    """
    casos = [
        ((0, "ok — tudo verde", "qualquer"), "nao_mordeu",
         "exit 0 tem de ser 'não mordeu', mesmo com marcador ausente"),
        ((1, "FAIL — divergência: superlativa própria", "superlativa própria"),
         "ok", "exit 1 com o marcador presente tem de ser 'ok'"),
        ((1, "FAIL — divergência: outra coisa qualquer",
          "MARCADOR-QUE-NAO-PODE-APARECER"), "marcador_errado",
         "exit 1 SEM o marcador tem de ser 'marcador errado' — é esta perna "
         "que prova que a checagem de marcador está viva"),
    ]
    fails = []
    for (rc, saida, marcador), esperado, porque in casos:
        got = _classifica(rc, saida, marcador)
        if got != esperado:
            fails.append(f"_classifica({rc}, ...) deu {got!r}, esperado "
                         f"{esperado!r} — {porque}")
    return fails


def main() -> int:
    meta = _meta_controle()
    if meta:
        print("FAIL — o meta-controle reprovou; nenhum caso foi rodado, "
              "porque um resultado verde não significaria nada:", file=sys.stderr)
        for m in meta:
            print(f"  {m}", file=sys.stderr)
        return 1
    print("meta-controle ................. ✅ _classifica distingue as 3 respostas")

    with tempfile.TemporaryDirectory() as d:
        base = Path(d) / "base"
        base.mkdir()
        _prepara(base)
        rc, saida = _roda(base)
        if rc != 0:
            print("FAIL — baseline já está vermelho; mutação não diz nada:",
                  file=sys.stderr)
            print(saida, file=sys.stderr)
            return 1
        print("baseline ...................... ✅ verde")

    falhas = []
    for nome, arquivo, de, para, marcador in CASOS:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            _prepara(tmp)
            alvo = tmp / arquivo
            txt = alvo.read_text()
            if de is None:
                alvo.write_text(txt + para)
            else:
                if de not in txt:
                    falhas.append(f"{nome}: âncora `{de}` não existe — "
                                  f"o teste não testa nada")
                    print(f"{nome[:44]:<46} 🔴 âncora ausente")
                    continue
                alvo.write_text(txt.replace(de, para, 1))

            rc, saida = _roda(tmp)
            v = _classifica(rc, saida, marcador)
            if v == "nao_mordeu":
                falhas.append(f"{nome}: guarda NÃO mordeu")
                print(f"{nome[:44]:<46} 🔴 não mordeu")
            elif v == "marcador_errado":
                falhas.append(
                    f"{nome}: falhou, mas sem o marcador `{marcador}` — "
                    f"pode ter falhado pelo motivo errado")
                print(f"{nome[:44]:<46} 🟡 mordeu, marcador errado")
            else:
                print(f"{nome[:44]:<46} ✅ mordeu, marcador certo")

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _prepara(tmp)
        arquivo, texto = CONTROLE
        alvo = tmp / arquivo
        alvo.write_text(alvo.read_text() + texto)
        rc, saida = _roda(tmp)
        if rc != 0:
            falhas.append("controle negativo: texto inócuo disparou guarda")
            print(f"{'controle negativo (texto inocuo)':<46} 🔴 falso positivo")
            print(saida, file=sys.stderr)
        else:
            print(f"{'controle negativo (texto inocuo)':<46} ✅ silencioso")

    print()
    if falhas:
        print(f"FAIL — {len(falhas)} caso(s) de mutação sem valor:",
              file=sys.stderr)
        for f in falhas:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"ok — {len(CASOS)} mutações mordidas com o marcador certo, "
          f"controle negativo silencioso")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
