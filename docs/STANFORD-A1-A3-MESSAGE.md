# Stanford — mensagem A1 + A3

> ## ✅ ENVIADO em 2026-09-08 (~23:00 BRT) pelo Toto
>
> **Para:** `yomri@stanford.edu` · **Assunto:** `arXiv:2606.06448 — phase-attributed
> memory telemetry from 32 days in production` · **Texto:** `docs/stanford-email-a1-a3.txt`
>
> **🔴 Compromisso em aberto que o envio criou:** o e-mail oferece *"the telemetry as a
> dataset with its schema"*. Se houver resposta pedindo, isso é um export real de
> `provider_telemetry` — 13 colunas, janela fechada 2026-08-07T00:00Z → 2026-09-08T00:00Z,
> 3.544 linhas. Verificado que **não há coluna de texto de query**, só hash ⇒ nada a
> sanitizar. Montar **com gate**: o `dose2.mjs` e o epoch perdido de 09-02 são as duas
> lições de exportar sem verificação.
>
> **Números que o e-mail afirma** (todos da janela fechada, aritmética conferida em 6
> pontos): 3.544 chamadas · USD 0,1352 · fases 3,16/94,6/2,3% das ops contra
> 55,7/30,5/13,8% do custo · USD por mil tokens de entrada 0,000122/0,000150/0,000157 ·
> 5.500 contra 82 tokens por chamada · 3 chamadas = 0,08% das ops e 29,7% do custo ·
> sem elas construção 55,7% → 37,0% · metade do gasto em 31 chamadas (0,87%) ·
> construção em 19 de 32 dias, manutenção em 11.
>
> **Alegações sobre o paper deles**, conferidas verbatim no HTML do arXiv em 2026-09-08:
> §3.1 *"Histories are streamed in 4096-token chunks, matching the MAB protocol"* ·
> §4.7 *"scale one user's history from about 64 K to 1 M tokens"* (histórico total, não
> tamanho por chamada) · §2.1 *"In **many** current systems, maintenance is weak or
> absent"* · abstract: harness atribui a *"construction, retrieval, and generation"* ·
> §4.7 *"None of the evaluated systems prune or forget by default"*. Se a v2 do paper
> mudar qualquer uma, o parágrafo correspondente cai.

> Corte A1+A3 decidido em 2026-08-15 (`STANFORD-OUTREACH.md` §4).
> A1 oferece a telemetria de fases; A3 mostra a política de esquecimento. A4 (survey /
> James Zou) é **canal separado**, depois — não misturar.

## Destinatário

**`yomri@stanford.edu`** (autor de correspondência de `arXiv:2606.06448`). Zexue He e
Alex Pentland assinam o mesmo paper e o MemoryArena, e são o elo com o Alvo B — mas
segundo o §5 a primeira mensagem não se espalha por vários destinatários. **Um
destinatário, o de correspondência.**

## Os números, e de onde vêm

Extraídos do `provider_telemetry` do store compartilhado, leitura read-only. ⚠️ A
primeira extração (2026-09-07) usou janela **aberta** — incluía o dia parcial e dava
3.545. Os números abaixo e os do e-mail são da janela **fechada**, remedida em
2026-09-08:

| | |
|---|---|
| janela | 2026-08-07T00:00Z → 2026-09-08T00:00Z, **32 dias completos**, todos com dado |
| registros | **3.544** chamadas de provider |
| custo total da série | **USD 0,1352** |
| provedores | `gemini-embedding-001` (3.426) · `gemini-2.5-flash-lite` (119) |

**Atribuição de custo por fase — o número que a bancada não produz:**

| fase | ops | % ops | custo USD | % custo | USD/op |
|---|---:|---:|---:|---:|---:|
| construction | 112 | **3,16%** | 0,0753 | **55,7%** | 0,00067 |

Soma: 112 + 3.351 + 81 = **3.544**, e 3,16 + 94,55 + 2,29 = **100,00**.
| query | 3.351 | 94,55% | 0,0412 | 30,5% | 0,0000123 |
| maintenance | 81 | 2,28% | 0,0187 | 13,8% | 0,00023 |

Uma operação de `construction` custa **55×** uma de `query`. Contando operações, a
construção é ruído; contando dinheiro, é a maioria. **É a mistura que produz isso, e a
mistura só existe em produção contínua.**

Cadência: `query` em 32 dos 32 dias, `construction` em 19, `maintenance` em 11.

## 🔴 O que NÃO afirmar — três coisas medidas

1. **Não é telemetria de fleet.** Os **6 bancos por agente não têm a tabela
   `provider_telemetry`** (verificado hoje). Todos os 3.544 registros são do **store
   compartilhado do workspace**, que os agentes consultam. Dizer "fleet" a quem escreveu
   o harness de perfilamento por fase seria pego na primeira pergunta.
2. **São 6 agentes, não 7** — Nox, Atlas, Boris, Cipher, Forge, Lex.
3. ~~**Não há amortização demonstrada.**~~ 🔴 **ESTA SÉRIE MEDIA A GRANDEZA ERRADA** —
   corrigido 2026-09-08 depois de o Fable apontar. `custo_query ÷ queries` é o custo do
   *embedding de query*, que é ~constante por construção; amortização é o custo **fixo**
   (construção + manutenção) diluído no volume. Recomputado na grandeza certa,
   `(construction+maintenance) ÷ queries` por semana, ×10⁻⁵ USD:

   | semana | queries | amortizado |
   |---|---:|---:|
   | 2026-W31 | 290 | 2,41 |
   | 2026-W32 | 1.229 | 3,02 |
   | 2026-W33 | 828 | 3,71 |
   | 2026-W34 | 376 | 3,44 |
   | 2026-W35 | 359 | **0,00** |
   | 2026-W36 | 271 | 2,32 |

   Spearman(volume, amortizado) = **+0,657** — sinal oposto ao de amortização. Mas
   **n=6 semanas, uma delas sem nenhuma construção** (W35 = 0 por ausência de evento, não
   por diluição). Isso **não testa** amortização em direção nenhuma. E a Rec 6 condiciona
   a *high-volume query workloads*: ~100 queries/dia não é esse regime. ⇒ o e-mail diz
   **"não consigo testar", e por quê** — não "não se reproduz".

4. **🔴 A manchete "3,16% das ops = 55,7% do custo" NÃO é achado sobre fases.** Por mil
   tokens de entrada as três fases custam 0,000122 / 0,000150 / 0,000157 USD —
   indistinguíveis. A razão 55× por operação **é** a razão 67× de tamanho de entrada
   (5.500 contra 82 tokens). Pior: **3 chamadas** (142k+125k+125k tokens) são **29,7%** de
   toda a série, e removê-las derruba construção de 55,7% para 37,0%. Metade do gasto está
   em **31 chamadas — 0,87%** (o ponto de Lorenz; eu havia escrito 1,4% por não
   tê-lo computado). ⇒ o e-mail apresenta isso como **cautela sobre o instrumento
   deles** (atribuição por fase segue a distribuição de tamanho de entrada, e é instável),
   não como confirmação. A frase antiga *"a bench characterization on a fixed workload
   cannot produce that ratio"* era **falsa** — uma bancada com entradas grandes produz
   exatamente isso.

5. **Não somos a mesma decomposição.** A deles termina em *generation*; a nossa não mede
   generation nenhuma (só vemos chamadas que o próprio sistema de memória faz, não os
   turnos de LLM dos agentes). Em troca atribuímos *maintenance*, que o harness deles não
   atribui. Dizer "the same decomposition" seria pego na primeira leitura — e a
   **diferença é a força da oferta**, não a fraqueza.

6. **`mutate` sem controle agêntico pode ser contradição-em-termos na taxonomia deles**,
   não célula vazia. Enquadrar como *desafio ao eixo* ("mutabilidade e controle talvez
   sejam eixos separáveis"), nunca como "achei um buraco na sua Tabela 1".

7. **Tratamento:** Knight-Hennessy é bolsa de pós-graduação ⇒ **"Dear Yasmine Omri"**, não
   "Dr. Omri".

## Rascunho da mensagem

🔴 **O texto a enviar vive em `docs/stanford-email-a1-a3.txt`, e SÓ lá.** Duas cópias do
mesmo texto é cache sem invalidação: o rascunho abaixo ficou falso em 4 pontos enquanto
esta seção dizia que estava pronto. Ele fica **só** como registro do que foi corrigido —
não copiar, não enviar.

<details>
<summary>Rascunho de 2026-09-07 — <b>SUPERADO, contém as 4 falsidades do bloco acima</b></summary>

> **Assunto:** Phase-attributed memory telemetry from a production deployment — 33 days,
> possibly useful for 2606.06448
>
> Dear Dr. Omri,
>
> I read *Agent Memory: Characterization and System Implications of Stateful
> Long-Horizon Workloads* in full. Your phase decomposition — construction, retrieval,
> generation — is the same decomposition I instrumented in a production memory system,
> and I am writing to offer the data, not to ask for anything.
>
> The system serves six agents on a single VPS and has been running continuously since
> 2026. Provider-level telemetry is attributed per phase; over the 33 days from
> 2026-08-07 the shared workspace store logged 3,545 provider calls at a total cost of
> USD 0.135. The phase attribution inverts what operation counts suggest:
> **construction is 3.16% of operations and 55.7% of cost** (USD 0.00067 per
> construction op against USD 0.0000123 per query). A bench characterization on a fixed
> workload cannot produce that ratio, because it is the workload *mix* that produces it,
> and the mix only exists in continuous operation.
>
> Two caveats I would rather state than have you discover. The telemetry covers the
> shared store the agents query, **not** six per-agent stores — those carry no telemetry
> table. And your recommendation on amortization via query volume **does not** reproduce
> here: weekly cost per query is non-monotonic across the series.
>
> Separately, your Recommendation 9 asks operators to add independent pruning or
> forgetting policies, and notes that all ten characterized systems accumulate state
> monotonically. This system has one — retention windows typed per content class,
> salience decay, epoch pruning, graph pruning — and, more usefully, the record of it
> failing: a compounding error in the decay drained the knowledge graph from ~21.5k
> nodes to 554 before it was diagnosed and recovered. On the four axes, it sits at
> mixed construction, multi-store storage, hybrid retrieval, and `mutate` mutability
> **without agent control** — maintenance is deterministic cron, not an LLM in a loop.
> I could not find that combination in Table 1.
>
> Happy to share the telemetry as a dataset, the schema, or the forgetting-policy
> post-mortem — whatever is useful, in whatever form. A technical report on the system
> is at `10.5281/zenodo.22649269`; it is a preprint and has **not** been peer reviewed.
>
> With respect for the work,
> Luiz Antonio Busnello — Independent Researcher

</details>

## Conferência contra o §5 antes de enviar

- [x] não reivindica o gap "memória guia decisão" (prior art do próprio grupo)
- [x] cita o Paper 1 **com** DOI, e sem a frase sobre peer review (o Toto tirou —
      "preprint" já diz, e "not peer reviewed" numa primeira mensagem se auto-deprecia)
- [x] não pede endosso, coautoria nem revisão — oferece
- [x] não menciona o harness deles (não é público)
- [x] declara as limitações antes de serem descobertas — agora **quatro**: sem generation,
      concentração em 3 chamadas, amortização não-testável, `provider_telemetry` sem texto
      de query (⇒ nada a sanitizar, o export é executável hoje)
- [x] **Toto revisou e ENVIOU** — 2026-09-08 ~23:00 BRT

## Contradições que a revisão do Fable matou

Cinco objetos foram conferidos entre si (o paper deles, o que afirmamos sobre ele, os dados
medidos, o e-mail, e a aritmética da manchete). **As 8 alegações sobre o paper deles são
verdadeiras** — verificadas uma a uma contra o texto. O que não estava alinhado era nosso:

| # | onde estava | o que era falso |
|---|---|---|
| 1 | e-mail, §amortização | media custo de embedding de query, não amortização |
| 2 | e-mail, 1ª linha | *"the same decomposition"* — a deles termina em generation |
| 3 | e-mail, manchete | *"a bench on a fixed workload cannot produce that ratio"* — pode |
| 4 | e-mail, mutabilidade | célula vazia × contradição-em-termos na taxonomia |
| 5 | e-mail, saudação | "Dr. Omri" — Knight-Hennessy é bolsa de pós-graduação |

Achado meu, fora da lista do Fable: a atribuição por fase é **instável** — 3 chamadas =
29,7% do custo, e sem elas construção cai de 55,7% para 37,0%. Isso virou o miolo do
e-mail, porque é a única coisa aqui que a bancada deles estruturalmente não pode ver.

## Segunda passada (v2), 2026-09-08 — o que sobreviveu

O Fable revisou a reescrita. Três resultados, e o mais importante é que **a réplica óbvia
existia e eu não a tinha visto**:

**🔴 A cláusula *"a fixed-workload bench holds fixed the thing that varies"* tinha resposta
de uma linha:** o §4.7 deles **varia entrada** ("scaling one user's history from about 64 K
to 1 M tokens"). Omri responderia *"we do vary input size, §4.7"* e o parágrafo cairia.
A defesa está no protocolo, e é melhor que a alegação original — verificado verbatim no
§3.1: *"Each sample is fed incrementally in 4096-token chunks"* e *"Histories are streamed
in 4096-token chunks, matching the MAB protocol"*. Com chunk fixo, a distribuição de
tamanho por chamada é **constante por construção** e não pode ter cauda; o §4.7 varia
histórico **total** de um usuário, que é outro eixo. O e-mail agora diz isso, nomeando os
dois. Mostrar que se leu o protocolo é o melhor sinal que um cold e-mail dá.

**🟠 Achado 7 — misquote, corrigido.** §2.1 diz *"In **many** current systems, maintenance
is weak or absent"*; o e-mail dizia "most". Citar a frase da pessoa **para mais forte**, na
frase em que se cita ela, é o erro mais barato de corrigir e o mais caro de deixar passar.

**✅ Achado 6 — REJEITADO nos fatos.** O Fable supôs que as porcentagens vinham da janela
aberta (`query = 3.352`, soma 3.545). Na janela fechada a query é **3.351**:
112 + 3.351 + 81 = **3.544**, e 3,16 + 94,55 + 2,29 = **100,00**. Custo idem:
0,075345 + 0,041226 + 0,018665 = **0,135236** = o total. Nada herdado — os números da v2
já eram todos da janela fechada. Conferido também: `constr sem top3` = 37,0%,
`31/3.544` = 0,87%, `usd/1k tok` = 0,000122 e 0,000150. Fecha em todos os pontos.

### Divergência deliberada do conselho do Fable

Ele recomendou **cortar** o parágrafo de amortização (n=6, negativo não-testável).
**Comprimi em vez de cortar**, e a razão é que a Rec 6 condiciona a *"high-volume query
workloads against **stable histories**"* — e **nenhuma das duas** condições vale aqui.
Isso é resposta precisa e curta à recomendação nomeada deles, em 4 linhas, e é melhor que
silêncio e muito melhor que o `rho`. O `rho = +0,66` **saiu** do e-mail: era o único
pedaço de insinuação com negação plausível. Os bursts ficaram, mas reenquadrados como
**fato de arquitetura** ("construction only runs when documents change, by design"), não
como correlação — que eu não computei.

Também: a oferta tripla virou **uma** (dataset + schema), com o post-mortem como aposto.
"Or both" transferia a escolha ao destinatário.

**Estado:** 650 palavras, zero markdown, zero PT-BR, 8 termos obrigatórios presentes,
aritmética conferida. ⚠️ Longo para contato frio — decisão do Toto.
