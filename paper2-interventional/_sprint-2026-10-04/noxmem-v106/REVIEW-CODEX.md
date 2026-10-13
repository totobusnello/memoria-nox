# Revisão Codex do pacote v1.0.6: NÃO OCORREU

Data: 2026-10-04 (noite).

## Veredito: inválido, sem recibo

A casca do Codex não chegou a rodar a voz. O classificador do auto mode barrou a chamada ao
`adversary-run.sh` antes de qualquer execução, e a casca devolveu só a negação:

> [Auto-Mode Bypass] — The Bash tool blocked the call to ~/Claude/scripts/adversary-run.sh

Não existe `=== ADVERSARY RECEIPT ===` e não existe `exit: 0`. Pela regra das vozes ("sem recibo
com `exit: 0`, reportar a falha e nunca escrever um veredito no lugar dela"), esta rodada **não
tem achados**: nenhum foi confirmado, rejeitado ou aplicado, e nenhum foi inventado aqui.

A falha é do **roteamento/permissão**, não da voz nem do pacote. Repetir a mesma chamada sob o
mesmo classificador falha igual. Para obter a revisão: rodar a casca de novo com a permissão
liberada para `adversary-run.sh`, ou o Toto rodar a voz no terminal dele.

## Estado do pacote, conferido nesta passagem (sem mudanças)

Nada foi editado no paper, no dataset nem na carta. Nenhum script de depósito foi rodado,
porque não havia correção a depositar.

| item | valor | como foi conferido |
|---|---|---|
| PDF local `paper/build/paper-tecnico-nox-mem.pdf` | MD5 `415e9e5da9630f73b6f9ce5446a6b256`, 73 páginas | `md5`, `mdls kMDItemNumberOfPages` |
| paper v1.0.6 | rascunho Zenodo 23147633, DOI `10.5281/zenodo.23147633` | API pública: 404 (rascunho, não publicado) |
| paridade v1.0.5 → v1.0.6 | `PARITY OK`, 22 substituições de 22 esperadas | `noxmem-v106/PARITY.txt` |
| dataset §6 | rascunho Zenodo 23146656, DOI `10.5281/zenodo.23146656`; zip MD5 `ef4c0240372ad48bff3b90b0abebfc0c` | `md5` do zip local; API pública: 404 |
| carta (§3.3 de `noxmem-apelacao-pacote.md`) | linha Attached com v1.0.6, DOI 23147633 e o MD5 acima | leitura do bloco |

O MD5 do PDF local é o mesmo que a carta e o checklist citam, e o MD5 do zip é o mesmo que a nota
de atualização da v1.0.6 registra. O readback autenticado dos rascunhos não foi refeito nesta
passagem; o último readback OK é o registrado na nota de 2026-10-04 (noite) do pacote.

## Pendências que continuam valendo

- Publicar a v1.0.6 (23147633) e o dataset (23146656), e conferir que os dois DOIs resolvem,
  antes de enviar a carta. Até lá, "six versions" no item 3 da carta não é verdade.
- Revisão Codex do pacote v1.0.6: **ainda por fazer**.
