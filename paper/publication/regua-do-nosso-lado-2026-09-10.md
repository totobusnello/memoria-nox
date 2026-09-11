# O método do NOSSO lado da régua não estava declarado — e o número era 39, não 30

> Medido 2026-09-10, no `origin/main` (`2fe722b`). O `regua-simetrica-2026-09-10.md`
> consertou a assimetria de **tamanho** declarando o método dos aceitos (`ltx_bibitem` no
> HTML, tokens crus). Ele não declarou como o **nosso** `30` foi obtido — a mesma omissão
> que ele denuncia, do outro lado da comparação, na quarta volta desta régua.
>
> Este documento **substitui** a linha `nosso` da tabela do §2 e as rotas do §3 daquele
> documento. O resto dele segue válido.

---

## 1. Dois defeitos no nosso lado, em direções opostas

**(a) O numerador contava auto-referência.** Das 53 footnotes definidas, **14 não são
obras**: são ponteiros para o nosso próprio código (`src/salience.ts`), para as nossas
env vars (`NOX_SALIENCE_MODE`), para uma medição nossa (`~341 MB RSS`, 2026-05-24), para
uma decisão interna (o pivô Q/A/P), e cinco descrevem o *stack de deployment* de um
competidor **como nós o medimos**. Nenhum dos quatro aceitos tem essa categoria na
bibliografia — contá-la infla o nosso lado.

**(b) O tokenizador do §5 não se aplica a markdown.** O método declarado remove tags HTML
(`<[^>]+>`), o que é correto para os quatro aceitos, que são HTML. Aplicado ao nosso
markdown, esse regex casa de um `<` matemático até o `>` seguinte e **apaga o texto entre
eles**: devolve 15.009 palavras contra as 24.111 reais, um erro de −38%.

Controle de reprodução, no commit que publicou o número: o tokenizador sem remoção de tags
devolve **24.111** contra os **24.126** registrados — delta de 15 palavras (0,06%). O que
remove tags devolve 15.009. ⇒ o método comparável para markdown é o cru **sem** remoção de
tags.

## 2. Remedição

| | régua (`fa3d28e`) | hoje (`2fe722b`) | delta |
|---|---:|---:|---:|
| palavras (cru, ≥1 alfanumérico) | 24.111 | **24.821** | +710 |
| footnotes definidas | 43 | 53 | +10 |
| **obras** (análogo de `ltx_bibitem`) | 24 | **39** | +15 |
| auto-referências (não contam) | 19 | 14 | −5 |
| arXiv IDs | 21 | 34 | +13 |
| entradas em `refs.bib` | 34 | 46 | +12 |
| **densidade** | 1,00/mil | **1,57/mil** | +0,57 |

O `30` publicado ficava entre as duas contagens — acima das 24 obras de então, abaixo das
43 footnotes. Não era erro de aritmética: era um numerador sem definição.

**Faixa dos aceitos, método uniforme:** 5.335–17.265 palavras · 2,06–2,95 refs/mil.
**Nós hoje:** 24.821 palavras = **1,44× o maior aceito** · **1,57/mil**, ainda abaixo do
piso, mas a 76% dele em vez dos 60% publicados. Os quatro PRs de referências (`#513`,
`#514`, `#516`, `#519`) valeram **+0,57/mil**, e nenhum deles foi contabilizado até agora.

## 3. As rotas, recalculadas — e o ponto fixo que faltava

A rota "só citar" **não é** a tamanho constante: cada obra nova precisa de discussão no
corpo, e discussão move o denominador. O número de obras necessárias é o ponto fixo de
`(39+n)/((24.821+n·W)/1000) ≥ 2,06`, onde `W` é o custo médio em palavras por obra:

| custo por obra | obras novas | tamanho final | × o maior aceito |
|---:|---:|---:|---:|
| 0 (citação seca — **não** admitida aqui) | 13 | 24.821 | 1,44× |
| 30 palavras | 13 | 25.211 | 1,46× |
| 45 palavras | 14 | 25.451 | 1,47× |
| 60 palavras | 14 | 25.661 | 1,49× |
| 90 palavras | 15 | 26.171 | 1,52× |
| 120 palavras | 17 | 26.861 | 1,56× |

⇒ **14 obras** é o alvo operacional, e o número é robusto ao custo de discussão na faixa
plausível. Combinando com corte, o esforço cai rápido:

| obras novas | corte necessário para o piso 2,06/mil |
|---:|---|
| +4 | 3.947 palavras (15,9%) |
| +8 | 2.005 palavras (8,1%) |
| +10 | 1.035 palavras (4,2%) |
| **+14** | **nenhum** |

## 3b. Realizado — e o ponto fixo acertou

Executado no mesmo dia. As 15 obras entraram com discussão no §1.5 (quatro parágrafos
novos e cinco inserções em parágrafos existentes).

| | previsto | realizado |
|---|---|---|
| obras novas | 15 (a W≈90) | **15** |
| custo por obra | 90 palavras | **76** |
| palavras | 26.171 | **25.967** |
| obras totais | 54 | **54** |
| densidade | 2,06/mil | **2,08/mil** ✓ |
| tamanho | 1,52× o teto | **1,50×** |

O modelo do ponto fixo acertou o número, e o desvio ficou no custo por obra (76 contra 90
previstas), a favor. Vale notar por que 14 não bastava: a **primeira** tentativa inseriu 14
e parou em **2,05/mil** — 0,01 abaixo do piso. O ponto fixo já dizia 15 nessa faixa de
custo; foi a minha estimativa de "14 é o alvo operacional" que arredondou para baixo o que
o próprio modelo tinha calculado.

⚠️ **A rota B fecha a densidade e agrava o tamanho**, exatamente como a tabela do §3
previa: 1,44× → **1,50×** o maior aceito. As duas dimensões movem-se em sentidos opostos
sob esta rota, e a decisão de fechar a segunda é separada — chegar ao teto de 17.265
palavras exigiria cortar 8.702 (34% do documento), o que não é uma edição, é outro artigo.
O que se afirma aqui é só que a dimensão de **densidade** deixou de ser outlier.

## 4. O censo agora é um artefato, e um guarda o prende

`paper/bibitem-census.json` classifica cada uma das 53 footnotes como `obra` ou
`evidencia`, com o motivo, e registra o tokenizador e o controle de reprodução. O
`censo_bibitem_check` do `claims_check.py` falha se uma footnote não estiver classificada,
se o censo classificar chave que já não existe, se uma chave estiver nas duas classes, ou
se o próprio censo estiver ausente — neste caso dizendo que **a perna não pode correr**,
em vez de passar calada.

Sem essa perna, acrescentar footnote muda o numerador em silêncio e a densidade publicada
envelhece sem alarme. Foi o que aconteceu entre `fa3d28e` e hoje: **+15 obras e ninguém
recontou**, e a decisão em aberto era calibrada contra `30`.

Quatro mutações verificadas, cada uma isolando esta perna — a de footnote nova usa autoria
que **casa** o manifesto de propósito, senão o balanço e a correspondência de autoria
acusam primeiro e a prova não distinguiria "a perna morde" de "outra decidiu antes".

## 5. Um ratchet frouxo apareceu quando a bateria destravou

A bateria de mutação estava **vermelha desde o `#519`**: instalei a perna de autoria e não
copiei `authors-manifest.json` para o tempdir dos casos, então o baseline ficava vermelho
e a bateria recusava-se a dizer qualquer coisa — corretamente, porque mutação sobre
baseline vermelho não informa nada. Ela ficou assim por um PR inteiro porque **acrescentei
um guarda e não rodei o teste do guarda.**

Destravada, apareceu um caso que não mordia: `PR_BASELINE = 66` contra **53** ocorrências
reais de `PR #NNN`. Um ratchet cujo baseline está acima do valor medido não é ratchet — dá
folga para 13 evidências não-arquiváveis novas em silêncio, e a mutação da bateria (que
soma 1) cabia dentro da folga. O baseline afrouxou porque os cortes do `#494`/`#507`
removeram ocorrências e ninguém apertou o número.

Agora o ratchet prende nos **dois** sentidos: acima do baseline acusa aumento; abaixo
acusa que o baseline ficou frouxo e diz o valor a escrever. Duas mutações,
uma por sentido.

⚠️ **O que este documento NÃO estabelece.** Que 2,06/mil seja um limiar de aceitação —
é o piso *observado* em quatro aceitos, população pequena e não amostrada ao acaso. E nada
aqui liga tamanho ou densidade à recusa de 2026-09-03: o e-mail não trouxe feedback
item-a-item.
