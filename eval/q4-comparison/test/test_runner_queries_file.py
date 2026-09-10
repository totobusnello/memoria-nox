"""
Testes do CARREGAMENTO de queries do runner.

Prendem dois defeitos compostos medidos em 2026-09-10, na corrida de busca do
Zep, que juntos produziram um artefato aparentemente completo -- `(0 errors)`,
`meta` bem formado -- cobrindo 4% do corpus:

  (1) `--limit` (default 100) era aplicado tambem ao `--queries-file` explicito;
  (2) o laco `for ds in datasets` relia o MESMO arquivo combinado uma vez por
      dataset, duplicando as linhas carregadas.

Artefato real: 200 registros = 100 `question_id` distintos, cada um duplicado,
todos `locomo`, sobre um arquivo com 1.982 locomo + 500 longmemeval.

Testam COMPORTAMENTO (contagem carregada), nao presenca de texto no fonte:
um teste que so procura o nome da variavel passa com a correcao desfeita.
"""

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUNNER = RAIZ / "runner.py"


def _fixture(tmp_path, n_locomo: int, n_lme: int) -> Path:
    p = tmp_path / "queries.jsonl"
    linhas = []
    for i in range(n_locomo):
        linhas.append({"dataset": "locomo", "question_id": f"L{i}",
                       "question": f"q locomo {i}", "gold_chunk_ids": ["c1"]})
    for i in range(n_lme):
        linhas.append({"dataset": "longmemeval", "question_id": f"M{i}",
                       "question": f"q lme {i}", "gold_chunk_ids": ["c2"]})
    p.write_text("\n".join(json.dumps(x) for x in linhas) + "\n")
    return p


def _plano(queries_file: Path, *extra: str) -> dict:
    """Roda o runner em --dry-run e devolve o que ele diz ter carregado."""
    out = subprocess.run(
        [sys.executable, "-u", str(RUNNER), "--systems", "nox_mem",
         "--datasets", "locomo,longmemeval", "--queries-file", str(queries_file),
         "--dry-run", *extra],
        capture_output=True, text=True, cwd=RAIZ, timeout=120,
    )
    total = None
    limite = None
    for linha in out.stdout.splitlines():
        if linha.startswith("[plan]"):
            for campo in linha.split():
                if campo.startswith("total_queries="):
                    total = int(campo.split("=", 1)[1])
                if campo.startswith("limit="):
                    limite = campo.split("=", 1)[1]
    assert total is not None, f"nenhum [plan] na saida:\n{out.stdout}\n{out.stderr}"
    return {"total": total, "limite": limite, "stdout": out.stdout}


def test_arquivo_explicito_carrega_todas_as_linhas_sem_limit():
    """Sem `--limit`, um arquivo explicito de N linhas carrega N -- nao 100."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        q = _fixture(Path(d), 150, 40)          # 190 > 100, o default velho
        assert _plano(q)["total"] == 190


def test_arquivo_explicito_nao_duplica_por_dataset():
    """
    Com `--datasets locomo,longmemeval` e UM arquivo combinado, cada linha entra
    UMA vez. O defeito relia o arquivo por dataset e dobrava a contagem.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        q = _fixture(Path(d), 3, 2)             # 5 linhas
        p = _plano(q)
        assert p["total"] == 5, f"duplicou: {p['total']} (esperado 5)"
        assert "'locomo': 3" in p["stdout"] and "'longmemeval': 2" in p["stdout"]


def test_limit_explicito_continua_a_valer():
    """`--limit` pedido na linha de comando corta -- e o plano declara o teto."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        q = _fixture(Path(d), 3, 2)
        p = _plano(q, "--limit", "2")
        assert p["total"] == 2
        assert p["limite"] == "2"


def test_plano_declara_limite_efetivo_nao_o_default():
    """
    Sem `--limit`, o `[plan]` tem de dizer `nenhum`. Dizer `100` -- o valor de
    `args.limit` -- e' o mesmo defeito de nome que overstates o teto:
    induz confianca num corte que nao houve, ou medo de um que houve.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        q = _fixture(Path(d), 3, 2)
        assert _plano(q)["limite"] == "nenhum"
