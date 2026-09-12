# audits/_archive — auditorias fechadas, preservadas

Auditorias de **2026-04-26 a 2026-05-31** que nenhum documento do repositório cita.
Movidas para cá em **2026-09-12** para deixar `audits/` navegável: eram **28 de 63**
arquivos soltos na raiz, e a raiz passou a ter **35**.

## O critério foi medido, não estimado

`scripts/censo-citacoes.py --dir audits` mede, para cada arquivo, quem o cita — em
**duas pernas reportadas separadamente**, porque elas leem o repo com semânticas
diferentes e uma pode estar morta enquanto a outra responde:

| perna | o que acha | o que não distingue |
|---|---|---|
| `por_caminho` | o caminho relativo inteiro escrito em algum arquivo | — é o que quebra literalmente num `git mv` |
| `por_basename` | só o nome do arquivo, citado em prosa | homônimos |

Só veio para cá o que deu **zero nas duas**. Verificado à parte que nenhum é referido
por `.github/`, `scripts/` ou `tests/`.

O instrumento tem **um controle positivo por perna** e sai `!=0` se qualquer uma deixar
de medir — sem isso, «não há citação» e «não consegui medir citação» produziriam a mesma
saída. O primeiro controle que escrevi **falhou de propósito** e foi assim que se
descobriu que o manuscrito cita `output/zep.json` por basename e nunca pelo caminho
completo.

## Reverter

Nada foi apagado. `git mv audits/_archive/<arquivo> audits/` devolve, e o histórico do
arquivo segue inteiro (`git log --follow`).

⚠️ **Antes de arquivar mais alguma coisa, rodar o censo de novo.** Um arquivo hoje sem
citação pode ganhar uma amanhã, e a régua de ontem manda o trabalho na direção oposta
hoje.
