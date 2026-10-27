# Codex (gpt-6-astra) — challenge do §11 (pré-registro, opção c)

receipt: /Users/lab/Claude/logs/adversary-receipts/adversary-receipt-codex-2026-10-27T134055-51300.txt
output_file: /Users/lab/Claude/logs/adversary-receipts/adversary-output-codex-2026-10-27T134055-51300.txt
transport: harness/nativo · exit: 0 · duration_s: 155

---

**Veredito: o §11 ainda não está pronto para pré-registro confirmatório.** Li integralmente os dois ficheiros. A segunda tentativa corrige a unidade nominal de inferência, mas repete a classe do erro do §4: declara que o desenho sustenta uma conclusão antes de demonstrar que a intervenção, a variância e a regra de decisão correspondem a essa conclusão.

O experimento pode estimar uma interação **entre truncagem artificial e prompt naquele benchmark**. Como está, não confirma o mecanismo de produção, sua magnitude nem a explicação por sobrevivência de identificadores.

**1. Alta — O fator manipulado muda de significado (§§2, 11.2 e 11.5).**

Há duas substituições substantivas:

- Em produção, a janela é descrita como **prosa parcialmente vista dentro de uma sessão**, cortada em `processed_at`, além dos mecanismos temporais de seleção. No benchmark, a intervenção remove **sessões inteiras** de um histórico.
- Os 24,0% referem-se à fração de **prosa** vista; a intervenção conserva 24,0% do **número de sessões**, com arredondamento para cima. Sem ponderação pelos comprimentos, não preserva sequer a dose nominal.

Além disso, §11.5 afirma que remover as sessões **mais antigas** justifica conservar um prefixo com as sessões **mais antigas**. Essa justificativa está invertida. O prefixo poderia representar um registro congelado cedo pelo mecanismo *see-once*, mas isso exigiria outra demonstração; não decorre do prune.

O que importa não é apenas a quantidade removida: são a posição temporal da evidência, atualizações contraditórias, redundância e distribuição das respostas. A intervenção mistura indisponibilidade com antiguidade e composição do contexto.

**Consequência:** o resultado pode ser causal para essa truncagem sem identificar o mecanismo de produção. Variar 0,12/0,48 não resolve essa diferença; uma checagem “em um braço” também não estima a interação sob outra forma de truncagem. Seriam necessárias as quatro células para isso.

**2. Média — A calibração cria dependência de desenho, não necessariamente contaminação estatística (§§10, 11.2 e 11.6).**

Usar uma estatística exploratória de produção para fixar previamente a intervenção pública é defensável. Não implica, por si só, vazamento das respostas do benchmark nem invalida o teste nele.

Mas as pernas não são independentes no sentido amplo anunciado: produção fornece a hipótese, a dose e o efeito usado no dimensionamento. O benchmark testa uma intervenção **condicionada a essas escolhas**; não é uma confirmação independente da representatividade delas.

Faltam, nos dois ficheiros, o denominador e a incerteza da mediana de 0,240. Os 12 casos com variância de janela não permitem deduzir quantos sustentam essa mediana na faixa escolhida.

**Consequência:** a separação defensável é entre dados exploratórios e dados de teste, não entre dois instrumentos que corroboram independentemente o mesmo mecanismo. A conversão de fração de caracteres para fração de sessões é um problema adicional, mais grave que essa dependência.

**3. Alta — O poder não está demonstrado para o contraste primário (§§3 e 11.4).**

O contraste aditivo é adequado à pergunta “o efeito conjunto excede a soma dos efeitos?”. Para cada instância:

\[
D_i=Y_{11,i}-Y_{10,i}-Y_{01,i}+Y_{00,i},
\qquad D_i\in\{-2,-1,0,1,2\}.
\]

O alvo é \(E[D_i]\), em pontos percentuais. Seu erro-padrão depende de \(\operatorname{Var}(D_i)\), portanto da distribuição conjunta das **quatro respostas**.

Uma “discordância de 0,30” não especifica essa distribuição. Definindo \(A=Y_{11}-Y_{10}\) e \(B=Y_{01}-Y_{00}\):

\[
\operatorname{Var}(D)=\operatorname{Var}(A)+\operatorname{Var}(B)
-2\operatorname{Cov}(A,B).
\]

Mesmo conhecendo a discordância de cada par, falta a covariância entre os contrastes. Não há fundamento apresentado para chamar 0,30 de conservador.

A tabela é numericamente compatível com a aproximação

\[
n\approx(1{,}96+0{,}84)^2\,0{,}30/0{,}214^2\approx52,
\]

mas isso trata 0,30 como **variância do contraste**, algo que o documento não estabelece. Pareamento não faz toda a variância entre instâncias desaparecer.

Há ainda duas incompatibilidades:

- O §3 prescreve interação em modelo logístico. Esse coeficiente mede interação na escala de **log-odds**, não superaditividade em pontos percentuais. Podem levar a conclusões diferentes.
- A tabela usa α=0,05; a regra posterior usa 0,03/0,02. O poder precisa corresponder ao procedimento efetivo.

A frase “revisar para cima se a discordância vier menor” também não decorre do cálculo: mantendo o efeito, menor variância requer menos observações. Se a intenção é adaptar pelo efeito observado, isso precisa de outra regra explicitamente especificada.

**Correção necessária:** fixar o estimando aditivo, dimensionar usando distribuições conjuntas plausíveis das quatro respostas e avaliar o procedimento completo de dois estágios.

**4. Alta — A partição dos ICs pode ser completa; as decisões científicas não são válidas (§11.4).**

Interpretando as frases como condições sobre um IC fechado \([L,U]\):

| Condição | Ação prevista |
|---|---|
| \(L>0{,}08\) | Parar por sucesso |
| \(L\le0{,}08\le U\) | Avançar |
| \(U<0{,}08\) | Parar e reportar nulo |

Assim formalizadas, são **exaustivas e mutuamente exclusivas** para um IC válido. Não inventaria uma lacuna nessa partição. A condição adicional de excluir zero na primeira linha é redundante.

O problema está nas conclusões:

- IC **[1, 7] pp** produz “nulo”, apesar de excluir zero e indicar interação positiva.
- IC **[9, 15] pp** “confirma a magnitude de produção”, apesar de excluir **21,4 pp**.
- IC **[−20, 40] pp** contém 8 pp, mas não sugere especificamente um efeito menor: sugere grande incerteza.

Além disso, ICs bilaterais de 95% não implementam automaticamente α=0,03/0,02. A soma dos alfas pode controlar os testes previstos se eles forem devidamente definidos; mencionar a divisão não ajusta os ICs usados nas decisões.

**Há estados sem ação definida:** falha em obter IC válido — por exemplo, separação ou não convergência do modelo herdado — e os critérios finais de classificação no estágio 2. Também falta conciliar a adaptação de tamanho com o teto de 240. Pela própria tabela, 240 não entrega o poder anunciado para 8 pp.

**5. Alta — Ambos os controles podem passar com um pipeline incorreto (§11.3).**

O contraexemplo mais simples é um pipeline que sempre responde `NAO SEI`:

- No positivo, fica no piso: passa.
- No negativo, mantém a mesma acurácia do contexto completo: passa.

Isso mostra que os resultados exigidos não bastam como validação.

No **positivo**, acurácia baixa também pode decorrer de falha do leitor ou do juiz. Inversamente, acertar sem as sessões anotadas não prova acesso indevido: pode haver conhecimento prévio, pistas na pergunta, redundância não anotada ou falsos positivos do juiz. “Sem sessão marcada” não equivale demonstradamente a “sem informação utilizável”.

No **negativo**, igualdade agregada pode esconder perdas e ganhos compensatórios. E remover sessões sem resposta pode alterar distração, recuperação e competição por orçamento: isso pode ser um mecanismo real do tratamento, não “contaminação” do estimador.

Faltam critérios quantitativos para “piso” e “≈”, uma margem de equivalência, desempenho mínimo de um controle respondível e diagnóstico pareado por item. Os ficheiros não permitem verificar a completude das anotações de evidência nem a implementação dos controles.

**6. Alta — Faltam limites que bloqueiam conclusões, e um limite declarado é uma inferência injustificada (§§11.1–11.6; README).**

Quatro problemas adicionais:

- **Haystacks diferentes não demonstram independência.** “0 compartilhando um haystack” pode excluir duplicatas completas sem excluir sessões componentes, fatos ou fontes geradoras compartilhadas. Não afirmo que haja sobreposição; os dois ficheiros não mostram a auditoria necessária para concluir “n é n”. Essa é uma possível repetição direta da falha do §4.

- **Menor densidade de identificadores não estabelece um piso.** A transportabilidade depende também de dificuldade, redundância, categorias de perguntas e competição por capacidade. Uma densidade maior pode aumentar o benefício do prompt ou saturar o armazenamento e reduzi-lo. Sem hipóteses adicionais, não existe ordenação demonstrada entre os efeitos nos dois corpora.

- **Juiz constante não significa erro constante.** O prompt de identificadores pode produzir respostas mais literais, favorecidas pelo juiz mesmo sem igual ganho de correção. Saída estruturada evita uma inconsistência de formato; não valida os rótulos. Esse risco ameaça a interação interna, não apenas a comparação com leaderboard. A validação humana mencionada no §7 para H2 precisaria alcançar o contraste primário.

- **O fatorial não identifica sozinho o mecanismo nem a refutação reivindicada.** O prompt pode alterar quantidade de memória, comprimento, seleção e recuperabilidade junto com identificadores. Uma interação positiva não demonstra que a sobrevivência de identificadores governa o efeito. Tampouco igualdade pontual de acurácia refuta uma afirmação sobre retenção incondicional — distinção que o próprio README reconhece antes de voltar a apresentar o resultado como refutação. H2 e H3 também não recebem dimensionamento e operacionalização suficientes no §11.

**Decisão recomendada:** manter o §11 como redesenho em elaboração. Antes do depósito, fixar uma única conclusão confirmatória, alinhar a intervenção a ela, demonstrar a unidade independente, refazer o poder para o contraste correto e transformar a regra sequencial em decisões matemáticas explícitas. O resultado hoje defensável é mais estreito que a tese do README.

