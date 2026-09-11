Verifiquei a política do arXiv de 2025-10-31 e o processo de apelação antes de arbitrar. Três fatos mudam o quadro: a política aceita **journal OU conferência** (não só journal; workshop não conta), a apelação é explicitamente "depois que o artigo completou peer review", e as decisões em apelação são finais e sem feedback. Não existe nenhum canal de "Section Chair" documentado.

## D1. Alvo de comprimento: Kimi tem razão sobre a régua, Grok está errado, e o número final é **20.700–22.000 palavras**, com 20.718 como teto e não como meta.

Grok está errado por aritmética, não por opinião. A mediana de 8–12 mil palavras com 55 obras dá densidade de 4,6 a 6,9 obras/mil, o dobro do teto de 2,95. Para caber na mediana você teria que **cortar** obras, não acrescentar:

| palavras | densidade com 55 obras | obras máximas p/ ficar ≤ 2,95 |
|---|---|---|
| 10.000 | 5,50 | 29 |
| 12.000 | 4,58 | 35 |
| 18.644 | 2,95 | 55 |
| 20.718 | 2,65 | 61 |

Atenção a uma inversão na sua pergunta: abaixo de 18.644 palavras a densidade **sobe** acima do teto. O remédio seria remover obras, não acrescentar. Cortar 20 obras de um paper experimental com 55 citações é destruir a ancoragem bibliográfica para satisfazer uma régua que Kimi corretamente chama de precisão falsa.

Kimi está certo que n=4 aceitos de primeira não medem o que reverte recusa. A consequência é que o comprimento não é a variável causal e não deve ser otimizado. O alvo passa a ser de **composição**, não de tamanho: trabalho alheio ≤ 9%, §7 ≤ 5%, e zero moldura de produto. O total resultante cai onde cair dentro de 18.644–26.699. Se o corte de composição render menos de 4.000 palavras, pare, não invente corte para bater 20.718.

## D2. Bloco B: **cancelar**, sem condição. As 686 palavras saem de §7 e da prosa redundante de §5/§6.

As duas vozes estão certas e a medição nova reforça: §3.5 é arquitetura própria, o único conteúdo que prova "sistema" em ambas as hipóteses de D4. Sob (A) survey, cortar o próprio método aumenta a proporção que você quer reduzir. Sob (B) whitepaper, a descrição técnica é o que separa paper de folheto. Não há hipótese em que o bloco B ajude. A única condição em que estaria certo é se §3.5 repetisse §3.1–3.4, e nesse caso o corte seria de duplicação, não de condensação para 300.

Fonte das 686 palavras:

- **§7 de 1.866 para 1.200** (−666). "Future work" longo é o marcador clássico de position paper, e é exatamente o tipo de texto que a política do arXiv nomeia como "papers not introducing new research results". Limitações ficam, futuro vira 3 parágrafos curtos.
- **§5/§6, prosa que narra o que a tabela já mostra** (−200 a −400). São 14.427 palavras, 55% do paper. Você já moveu 2.177 para suplemento sem perder resultado. Há margem para mais sem tocar em §3.

Saldo: 686 cobertas com folga, razão contribuição:alheio sobe de 7,5:1 para cerca de 8,5:1.

## D3. Journal: **Grok tem razão no efeito, errado no motivo. Não apelar agora, não tentar via processual. Apelar só com a carta de aceite em mãos.**

Grok acerta que apelar sem venue é pedir waiver. Mas o motivo não é "o email tornou a condição obrigatória". O motivo é que a política publicada já diz literalmente que a apelação é "para ressubmeter se o artigo desde então completou peer review", e que a decisão em apelação é final e sem feedback. O email só repetiu a regra. Apelar agora gasta o ativo único contra um moderador que tem instrução escrita para negar.

Kimi está errado em fato: não existe canal de Section Chair para questão processual no processo de apelação do arXiv. Qualquer resposta ao email de moderação sobre essa submissão cai na fila de apelação. "Perguntar sem contestar" é indistinguível de apelar, do lado deles. Kimi estaria certo apenas se você localizar, na página oficial de appeals, um canal nomeado e distinto. A página que a própria política linka não o menciona.

Dois pontos a favor do dono do projeto: a política aceita **conferência peer-reviewed** além de journal, mais rápida que TMLR se a janela importar. E a memória do projeto já fixou TMLR como rota; com aceite, a apelação vira execução de regra, não pedido de exceção.

## D4. Causa: **(B) whitepaper de produto foi o gatilho, (A) survey foi o rótulo.** A correção é a de (B).

O template de recusa é o de (A), porque é o único template que o moderador tem para "precisa de peer review prévio". Mas o conteúdo não sustenta (A): related work é 9,1% e experimentos são 55,3%. Nenhum leitor que abriu §5 classifica isso como survey. Surveys em CS têm 100–300 referências; o paper tem 55. Logo o moderador decidiu pela superfície de 2 minutos: título, abstract, headers, links. E a superfície tem nome de produto como nome de sistema, tagline de posicionamento, repositório com SDKs, diretório GTM e benchmark contra três concorrentes comerciais nomeados. Isso lê como vendor benchmark, e vendor benchmark cai na mesma gaveta de "não é resultado de pesquisa novo".

Como medir a diferença, barato e reversível:

1. **Teste cego de superfície.** Dar às 6 vozes adversariais apenas título, abstract, lista de headers e contagem de refs, e pedir classificação em três classes: survey/position, whitepaper de produto, research paper. Se ≥4 de 6 dizem whitepaper, (B) confirmada. Se dizem survey, (A). Custo Anthropic zero, recibo verificável.
2. **Censo de marcadores de produto.** Contar no abstract e §1: ocorrências do nome do produto, tagline, URLs para o repositório, verbos de entrega ("ship", "deploy", "customers"). Comparar com os 4 aceitos.
3. **Censo de marcadores de posição.** Contar "we argue", "should", "call for", "roadmap" em §1 e §7. Se for alto, (A) tem base real e a correção de §7 em D2 cobre.

Correção de (B), que precede qualquer apelação: sistema com nome neutro no paper, sem tagline, benchmark contra "três sistemas open-source" com os nomes só na tabela e no apêndice, e o repositório citado apontando para um tag de código sem GTM nem launch assets.

## Ordem de execução

1. **Não responder ao email do arXiv.** Irreversível. Decisão já tomada pela política, não pelo dono.
2. **Rodar o teste cego de superfície e os dois censos** (item D4). Reversível, 1 hora, custo zero. Decide entre correção (A) e (B) antes de cortar uma palavra.
3. **Cancelar bloco B; cortar §7 para 1.200; podar prosa redundante em §5/§6.** Reversível via git. Alvo de composição, não de contagem; total fica onde cair em 18.644–26.699.
4. **Aplicar a correção de (B)** se o teste cego confirmar: nome neutro, sem tagline, tag de código limpo. Reversível.
5. **Escolher o venue.** Decisão do dono: TMLR (rota já fixada, mais lento) ou conferência peer-reviewed (aceita pela política, workshop não). Submissão é semi-irreversível.
6. **Apelar ao arXiv com a carta de aceite anexa.** Uso único; só depois do passo 5.

Fontes: [arXiv, Updated Practice for Review Articles and Position Papers in CS (2025-10-31)](https://blog.arxiv.org/2025/10/31/attention-authors-updated-practice-for-review-articles-and-position-papers-in-arxiv-cs-category/), [arXiv Content Moderation](https://info.arxiv.org/help/moderation/index.html), [404 Media sobre a mudança](https://www.404media.co/arxiv-changes-rules-after-getting-spammed-with-ai-generated-research-papers/).
