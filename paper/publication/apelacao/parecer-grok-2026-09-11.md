**1. O plano ataca o sintoma mensurável, não a causa.** Moderador de arXiv não conta palavras, densidade de refs nem o fator 1,20×. O e-mail já nomeou o critério: *precisa de revisão que o arXiv não oferece*, com via de reconsideração *se publicado em journal*. Isso é o overlay de 2025-10-31 (survey/review/position) **ou** o juízo “isto ainda não é um article”. Os dois se alimentam da mesma coisa visível em 90 segundos: taxonomia de gaps, tabela larga de sistemas, Related Work inchado, tom de position paper, 69 footnotes, 52 arXiv IDs.

O que o plano corta é em grande parte *carne de system paper* (arquitetura, latência/custo/footprint, ablações). O que *não* toca é o que dispara survey. Esforço desperdiçado: A (números de sistema), B, G, K, e a camisa de força [18.644; 26.699]. Esforço útil: E, F, C, D, e **reescrever §1.4** — que vocês excluíram de propósito.

A densidade 2,06–2,95 é overfitting com n=4. Nenhum moderador calcula obras/mil palavras. Tratar isso como restrição dura é numerologia e está ditando cortes errados.

**2. Bloco B enfraquece o argumento de system paper. Não é irrelevante.**

Paper de sistema vive de *o que foi construído e como*. 986→300 em descrição de arquitetura, enquanto §1.4 (768) e §1.5 (1.587) ficam intocados, é o sinal inverso ao que a apelação precisa emitir. Citada só 2×: ou o mecanismo é periférico (aí não condensar — cortar ou integrar de verdade no resto) ou está sub-escrito no paper (aí encurtar piora). Condensar arquitetura para caber numa régua de comprimento é cargo-cult.

**3. Bloco D é o corte certo. O risco não é “esconder ressalvas”.**

Três blocos de honestidade (§5.8.5, §5.8.6, §7.1 L1–L8) parecem blog epistemológico, não article. Um §7.1 único é o padrão. O risco real é o oposto: *apagar substância* — em especial EverOS 0,6455 > 0,5013, o não-resultado do Letta, e o escopo do benchmark. Se cada ressalva única sobrevive em L1–L8 e o loss continua no §6 e no §6.6, consolidar é limpeza. Se alguma ressalva morrer no merge, aí sim parece encobrimento, e numa apelação de uso único isso é fatal.

**4. Reformatar §1.4 não é superstição. É o único corte estrutural que ataca a classificação.**

Tabela de 9 colunas + “Six Gaps” no início é o artefato mais survey/position do manuscrito. Moderador *skima*. Não precisa ganhar palavras; precisa deixar de parecer taxonomia do campo. Trocar por 1–2 parágrafos “diferenças operacionais face a X/Y/Z” (as 13 refs podem continuar no §1.5) reduz o gatilho sem mexer no numerador. Manter a tabela porque “corta refs” é otimizar a métrica errada. O framing “identificamos seis lacunas da área” é retórica de position paper; system paper diz em um parágrafo o que os anteriores não fazem e passa ao sistema.

**5. Erros de estratégia. O que eu faria no lugar.**

Erros:
- Tratar “informação adicional” como substituto da condição que *eles já impuseram neste caso*. “In some cases we may require” deixou de ser discricionário quando veio no e-mail. Apelação sem journal é pedir waiver da condição nomeada. Appellate moderator nega; Section Chair não reabre conteúdo; acabou para sempre.
- Gastar o ativo de uso único para argumentar reclassificação, com zero vitórias documentadas nesse caminho. Chen apelou *com* DOI IEEE. Isso confirma a via que o e-mail descreveu, não a que vocês querem.
- Acreditar que encurtar = informação adicional. Informação adicional, na política que vocês citam, é *descrição detalhada do conteúdo de pesquisa e por que a categoria cabe*. Comprimento não é isso. Se o problema fosse revisão, o movimento é *revisar e resubmeter*, não apelar o recusado. Apelação é para decisão *errada* sobre o material existente. Cortar 5,5k palavras torna o material outro; o overlay pode simplesmente recair.
- Desde 03/09 o manuscrito ficou *mais* survey: +13% palavras, footnotes 20→69, arXiv IDs 11→52. Apelar *esta* versão dizendo “não somos survey” é incoerente. A bibliografia “consertada” piorou o sinal que vocês tentam apagar.
- Cortar ablações (G) e arquitetura (B) num paper cujo headline empírico pré-registrado é uma *derrota*. Sem mecanismo e sem campanha de ablação, resta related work + loss. Isso não é system paper; é nota negativa com survey colado.

O que eu faria:
- **Não apelar agora.** O downside é permanente; o upside é especulativo.
- Submeter a workshop/conferência/journal (até workshop de NeurIPS/ICLR/ACL, IR, ou venue de sistemas). Pegar DOI. Aí apelar ou depositar, que é o caminho que o arXiv *escreveu* e o único com precedente.
- Enquanto isso, reescrever para caber em 8–12k palavras (mediana dos aceitos, não 1,20× o máximo): sistema e benchmark na frente; matar a tabela de gaps; matar histórico de campanha; uma tabela compacta de ablação + uma de latência/custo/footprint; arquitetura suficiente para reproduzir; loss do EverOS visível; footnotes abaixo de ~15.
- Na carta (só se um dia apelarem): zero menção a densidade, 1,20×, regra de 2025-10-31, ou “não somos survey”. Descrever o artefato (SQLite+FTS5+sqlite-vec+RRF), 9 gerações de ablação, H2H pré-registrado, 2.482 queries, o número que *perde*. Pedir categoria concreta (cs.IR ou cs.AI) com uma frase de encaixe. Qualquer numerologia na carta parece litigante, não cientista.

**6. Maior risco que vocês não nomearam: a apelação sem journal é, na prática, auto-deny procedimental — e é irreversível.**

O overlay já lhes deu a condição. Ignorá-la não é “informação adicional”; é desobediência à instrução do caso. Appellate moderator não precisa discutir se é survey. Nega. Section Chair não entra em conteúdo. Paper 1 nunca entra no arXiv.

Riscos que o plano também não precifica:
- 69 footnotes (monografia/blog). Não está no plano de corte e é mais visível que 5k palavras.
- 52 arXiv IDs não revisados num texto não revisado: círculo de preprints, reforço de survey.
- Suplemento *externo* para método/ablações: paper não autocontido, pior para arXiv, não melhor.
- Skim de 90s no loss 0,50 vs 0,65 sem as ablações: “não há contribuição”.
- Instabilidade: recusa → inchou 13% em 8 dias → quer cortar 21%. Não parece manuscript; parece draft ansioso.
- Novelty bar do stack (RRF+FTS5+sqlite-vec é IR padrão). O que impede “tech report de produto” são avaliação e ablação — exatamente G e parte de A.

**O plano está errado na alocação, não só na margem.** Inverter: não gastar a apelação; parar de otimizar densidade; cortar/reformatar §1.4 (tabela+“gaps”), E, F, footnotes, histórico Wave; *preservar* arquitetura, números de sistema (numa tabela, não em 927 palavras), ablações-chave, o loss, §6 e §6.6. Comprimento-alvo: parecer article de sistemas, não 1,202× o maior vizinho. Se precisam de timestamp já, a via que o e-mail deu é journal/workshop primeiro — não uma apelação de uso único apostada numa régua que o moderador não usa.

