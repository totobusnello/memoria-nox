# `receipts/` — recibos das rodadas adversariais

Existe porque o Anexo B da `AMENDMENT-DRAFT-band-collapse-2026-08-26.md` exige
recibo verificável de cada voz adversarial, e os recibos nasciam em
`$TMPDIR/adversary-receipts/` — diretório **efêmero**, que o macOS limpa. Um
requisito de auditoria cujo artefato mora em `/var/folders` não é requisito.

A cópia para cá foi disparada por um achado do Kimi que estava **errado no fato e
certo no risco**: ele afirmou que o recibo do GLM não existia, tendo checado só
`.remember/` na raiz do repo. O recibo existia — em `$TMPDIR`. Mas a inferência
"não achei no lugar que olhei ⇒ não existe" é exatamente o defeito que o Anexo B
descreve, e o fato de o recibo estar num diretório que se apaga é o que tornava a
inferência plausível.

## O que estes arquivos provam — e o que NÃO provam

Cada recibo fixa: voz, modelo, timestamp, `cwd`, `prompt_sha256`, `prompt_bytes`,
`exit`, `duration_s`, `output_sha256`, `output_bytes`, comando.

**Provam:** que o processo rodou, com um prompt de conteúdo determinado (pelo
hash), e que produziu uma saída de tamanho e conteúdo determinados (pelo hash).
Um `exit: 0` acompanhado de `output_bytes` não-trivial distingue execução real de
**casca vazia** — o padrão em que a camada adversarial responde sem nunca chamar o
provider, que já ocorreu neste projeto em 3 de 4 vozes numa rodada.

**NÃO provam** — e isto é a lacuna que fica aberta:

1. **O texto da saída não está aqui.** Ele foi consumido pelo agent que fez a
   chamada e não foi persistido. Logo um terceiro pode confirmar que houve uma
   execução cuja saída tinha aquele `sha256`, mas **não pode ler o que a voz
   disse**, nem conferir se o resumo que eu fiz representa fielmente o conteúdo.
   Enquanto isso não mudar, a fidelidade do meu relato das rodadas é
   **inverificável por terceiro**.
2. **O prompt também não está aqui**, só o hash. Serve para provar que dois
   recibos usaram o mesmo prompt, ou que o prompt não foi trocado depois — não
   para auditar o que foi perguntado.
3. **O campo `host:` foi redigido** (`<laptop-do-autor, redigido>`) porque este
   repo é público. É a **única** alteração de byte em relação ao recibo emitido, e
   nenhum dos quatro campos que sustentam a verificação depende dela.

## Correção pendente do próprio instrumento

O wrapper (`scripts/adversary-run.sh`, fora deste repo) devia gravar a **saída**
ao lado do recibo, com o nome derivado do `output_sha256`, e num diretório não
efêmero. Sem isso, o recibo atesta que houve conversa e não o que foi dito — e a
rodada seguinte reencontra o mesmo limite.

## Rodada registrada aqui

Quatro vozes sobre a emenda, todas `exit: 0`:

| voz | modelo | `output_bytes` | `duration_s` |
|---|---|---|---|
| codex | assinatura(OpenAI/gpt-5.x) | 1.472.973 | 493 |
| kimi | assinatura(Moonshot/K2) | 58.869 | 617 |
| deepseek | deepseek-v4-pro | 14.413 | 485 |
| glm | glm-5.3 | 9.535 | 90 |

⚠️ `output_bytes` mede volume, **não qualidade nem profundidade**: a saída do
codex inclui o log de raciocínio inteiro, a do glm é só o veredito. O recibo mais
curto desta rodada não é o mais fraco.
