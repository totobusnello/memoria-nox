# Revisão da carta de apelação (§3.3) e do dataset do §6: Kimi + Codex

Data: 2026-10-04 (noite). Escopo: o bloco §3.3 de `../noxmem-apelacao-pacote.md` e o dataset `payload/` (rascunho Zenodo 23146656).

## Vozes

| voz | recibo | exit | conta? |
|---|---|---|---|
| Kimi k3 | `.remember/adversary-receipt-kimi-2026-10-04T195016-72806.txt` | 0 | sim |
| Codex gpt-6-astra | `.remember/adversary-receipt-codex-2026-10-04T195018-72868.txt` | 0 | sim |

Conferi cada achado por `grep` da citação e contra o repositório, o dataset, o manuscrito, a API do Zenodo e o Gmail (só leitura). Nenhum comando git, nenhuma publicação, nenhum contato.

## Achados

20 achados no total (Kimi 8, Codex 12), que somam 16 questões distintas. **15 confirmados** (11 questões distintas), **5 rejeitados**.

| # | achado | citação achada? | veredito | evidência | o que fiz |
|---|---|---|---|---|---|
| Codex 1 | o scorer credita o mesmo id relevante a cada ocorrência; nDCG e recall passam de 1 | sim (§6.3.2 (e), "a collision cannot mis-score a retrieval") | **CONFIRMADO** | rc4 `mem0.json`: 20 de 2.482 queries repetem um id no top 10, todas LongMemEval, todo id repetido é um dos 8 ids que nomeiam dois documentos; em 3 o id repetido é gold (`07741c44` e `07741c45` nDCG 1,57 / recall 2,0; `2ebe6c90` 0,75 / 1,5). Nenhum outro output repete id. Creditando cada id uma vez: 10 dos 135 checks mudam (9 valores impressos): R07 0,4061→0,4030, R08 0,036→0,035, R11/A05 0,4337→0,4331, E10 0,5852→0,5842, C13 0,4570→0,4565, C18 0,2955→0,2930, R17 +0,119→+0,123, C14 +0,093→+0,094, C19 +0,142→+0,144. LoCoMo e MRR não mudam. Tudo baixa o Mem0; nenhuma ordem ou sinal muda. Calculado duas vezes (script ad-hoc e bloco novo do verificador) com o mesmo resultado | **declarado, não corrigido no paper**: README do dataset ("Further observations"), bloco de sensibilidade no `verify_dataset.py` fora do exit code, descrição do Zenodo, e uma frase no item 3 da carta. Corrigir o scorer muda números do paper: é a v1.0.6 (abaixo) |
| Codex 2 | a carta atribui ao plano de maio o que ele não contém | sim | **CONFIRMADO** | `specs/2026-05-23-Q4-comparison-execution-plan.md`: linha 17 "LongMemEval n=100 + LoCoMo", linha 47 "LongMemEval n=100"; não fala em 2.482 nem em 500 queries do LongMemEval; métrica descrita como "gold relevance × discount". Fixa: corpus, queries e gold idênticos (138-139), k = 10 (141), nDCG@10/R@10/MRR/latência (23), os dois datasets (147), variante all-Gemini opcional (142) | item 2 reescrito: o que o plano fixa, que ele dimensionava o LongMemEval em 100, e que os 2.482 vieram depois |
| Kimi F1 / Codex 3 | o DOI do dataset ainda não resolve | sim | **CONFIRMADO (processo)** | `GET /api/records/23146656` → 404; rascunho `status: draft`, `published: False` | texto mantido: a carta só sai depois de você publicar. O texto alternativo do Codex ("not yet publicly available") seria falso no momento do envio. Passo 8b do checklist continua sendo bloqueante |
| Kimi F2 / Codex 9 | datas das respostas aos tickets | sim | **CONFIRMADO** | Gmail (2026-10-04): MOD-97655 enviada 25/07, respondida **11/08**; MOD-98296 enviada 31/07, respondida **03/08**. As datas da carta estavam certas, mas a ordem "answered on 3 and 11 August" casava cada uma com o ticket errado. O "13/08" das §3.4/§3.5 do pacote estava errado | cabeçalho da carta reescrito com cada data presa ao seu ticket; §3.4, §3.5, checklist 1-2 e §7 do pacote atualizados. O e-mail de recusa também foi conferido: as duas citações batem, destinatário `lab@generantis.com.br` |
| Kimi F3 / Codex 5 | salience descrito no estágio errado | sim | **CONFIRMADO** | manuscrito l. 397: `active` soma salience − 0,5 "to each retrieval layer's boost sum before RRF fusion"; `shadow` é o default e não muda o ranking | frase do item 2 reescrita |
| Kimi F5 / Codex 4 | "135 numbers recomputed" exagera | sim | **CONFIRMADO** | `N` no verificador: 118 `num` + 1 `min` + 13 `bool` + 3 `str` = 135; X01-X03 são aritmética sobre valores impressos. Sobram 132 recomputados dos arquivos | carta (itens 1 e 3), README, docstring, mensagem final do verificador e descrição do Zenodo dizem agora "135 values / checks", 132 + 3 |
| Kimi F6 | README lista 10 linhas, o script imprime 12 grupos | sim | **CONFIRMADO** | duas linhas fundidas (EverOS 6.3.1 + 6.3.2 (e); cross-encoder + p50) | README separado em 12 linhas, "prints the same 12 groups" |
| Codex 6 | o §6.3.2 diz "The per-query outputs are not distributed" | sim (l. 1022) | **CONFIRMADO (paper)** | a frase está no v1.0.5 | declarado no README do dataset; correção recomendada para a v1.0.6 |
| Codex 7 | garantias de auditoria maiores que a evidência | sim, as duas | **CONFIRMADO** | "every statement was checked again" é certificação exaustiva; o script de paridade compara números, citações, referências e cabeçalhos, não alegações | as duas frases do item 5 reescritas no tamanho do que foi feito |
| Codex 8 | "A fifth system, Letta" some com o agentmemory | sim | **CONFIRMADO** | §6.2: cinco concorrentes; agentmemory só no canônico de 15/06 (n = 100) | frase do item 2 nomeia o agentmemory e o Letta, citando 6.3 e 6.3.1 |
| Codex 11 | o README público do repo contradiz a carta | sim (`README.md` l. 58 e 313) | **CONFIRMADO (repo)** | l. 313 "The win is architectural"; l. 58 "same corpus, queries and embedder" numa linha que inclui Zep (`text-embedding-3-small`, §6.2) | **não aplicado**: fora do escopo (carta e dataset) e exige commit. Texto sugerido abaixo |
| Kimi F4 | "less than a tenth" está no limite (9,8%) | n/a | rejeitado | verdadeiro hoje; é alerta, não defeito | nada |
| Kimi F7 | a frase da condição não cumprida | sim | rejeitado | a própria Kimi recomenda manter; o pacote §4 já registra a decisão | nada |
| Kimi F8 | quebrar o marcador de 4 de outubro | sim | rejeitado | estilo | nada |
| Codex 10 | "MIT" pode atribuir licença ao manuscrito | sim | rejeitado | `LICENSE` do repo é MIT e cobre o repositório inteiro; o próprio paper diz "github.com/totobusnello/memoria-nox (MIT license)"; o preprint no Zenodo é CC BY 4.0, o que não torna a frase falsa | nada |
| Codex 12 | a apelação não cumpre a condição do e-mail | sim | rejeitado | a carta já diz no item 1 que a condição não foi cumprida; a troca proposta é de estilo | nada |

## O que mudou na carta (§3.3)

1. Cabeçalho: "status inquiries MOD-97655, sent 25 July 2026 and answered 11 August, and MOD-98296, sent 31 July 2026 and answered 3 August; both answers said that no decision had yet been reached."
2. Item 1: "a script checks 135 values printed in Section 6 against them (item 3)".
3. Item 2: salience "in its active mode … is added to each retrieval layer's boost before fusion; the default shadow mode computes it without changing the ranking (3.4.3)".
4. Item 2: o protocolo diz o que o plano de 21/05 fixa, que dimensionava o LongMemEval em 100 queries, e que as corridas posteriores usam 2.482.
5. Item 2: "Of the five competitors the paper selected, agentmemory was measured only in the first comparison run (n = 100 per dataset), and Letta could not be run at this scale; the paper gives the reason (6.3, 6.3.1)."
6. Item 3: decomposição 132 + 3, e a declaração do defeito do scorer, com o exemplo 0.4061 → 0.4030 e "changes no ordering".
7. Item 5: "the manuscript's statements were checked again … and the discrepancies found were corrected"; "A script confirms over the whole manuscript that no number, reference or citation changed, and a separate review checked for changes in meaning."

Caracteres proibidos no bloco: zero travessões, asteriscos, sublinhados, chaves, colchetes, pipes e marcadores `<<`; um único `+` (+4.01 pp), sem par. **Contagem: 1.768 palavras, 11.070 caracteres** (antes: 1.597 / 10.039).

## O que mudou no dataset

- `payload/README.md`: frase de abertura (135 checks = 116 números + 13 sim/não + 3 strings dos arquivos + 3 diferenças de valores impressos); critério 4 do Quick start; tabela "cannot recompute" com 12 linhas; duas observações novas: o scorer e a frase "not distributed" do §6.3.2.
- `payload/verify_dataset.py`: docstring com a decomposição; função `sensitivity()` que imprime, depois da tabela e **fora do exit code**, as queries com id repetido por arquivo e os 10 checks recalculados creditando cada id uma vez, mais "nox-mem still leads rc4 Mem0 overall and in every §6.4 category: yes". Mensagem final: "135/135 Section 6 values checked".
- `zenodo-metadata.json`: descrição com a decomposição e o defeito do scorer.
- `deposit_draft.py` rodado: `SHA256SUMS` regenerado; `verify_dataset --manuscript` no payload e na cópia extraída do zip: **OK 135/135, exit 0**; zip 2.411.484 B, sha256 `5c96f889…3669a`, md5 `97b62942e259fc97f03a37d1dfae94b7`; README md5 `92b36597…`; readback OK; **`published: False`, `status: draft`**; registro público ainda 404.
- Não toquei em `scripts/aggregate.py` (é cópia verbatim do harness; mudar ali faria o dataset discordar do paper que ele lastreia).

## Antes de enviar (seu)

1. **Bloqueante:** publicar o rascunho 23146656 e conferir que `https://doi.org/10.5281/zenodo.23146656` resolve (checklist 8b).
2. **Decisão sua, recomendada:** v1.0.6 do paper antes do envio, com três mudanças: (a) §6.3.2 (e), trocar "Scoring is by id, so a collision cannot mis-score a retrieval" por uma frase que diga que, em 3 queries do LongMemEval, o Mem0 devolveu as duas cópias de um id gold e o scorer creditou as duas; (b) os nove valores acima, recalculados com crédito único (ou uma nota que os dê ao lado dos atuais); (c) §6.3.2, trocar "The per-query outputs are not distributed" pelo DOI do dataset. Se fizer a v1.0.6, o dataset precisa de nova rodada (os 135 checks passam a testar o scorer novo) e a carta troca DOI/MD5 e a frase do defeito vira correção datada no item 5. Se **não** fizer, a carta como está é verdadeira: ela declara o defeito e o dataset o mede.
3. **Recomendado:** README público do repo. Linha 313: tirar "The win is architectural (hybrid FTS5 + dense + RRF), not an embedding-mode artifact." e pôr "The embedding-matched comparison does not isolate architecture from version, backend or sample scope (§6.3.2)." Linha 58: trocar "same corpus, queries and embedder" por "same corpus and queries; nox-mem and Mem0 share the embedder, EverOS and Zep run their own configurations (§6.3.3, §6.3.4)". O moderador chega ao repo pela carta.
