# Peça (b) — prosa do §6, migrável, com zero números

> **Contrato desta peça.** Nenhum número aparece aqui, por desenho. Todo valor
> vive em `RESULTADOS-Q4-2026-09-10.md` (peça (a)), que é autossuficiente. Assim
> a sessão par pode migrar esta prosa para o manuscrito sem arrastar medição, e
> um número corrigido em (a) não deixa uma frase mentirosa em (b).
>
> Escrita para ser colada em §6 com edição de forma, não de conteúdo. Onde há
> `[→(a) §N]`, a par insere o valor da seção N da peça (a).

## O que estas duas colunas acrescentam

As duas entradas novas fecham lacunas de natureza diferente, e convém não as
tratar como uma só. Uma delas era um vazio de **execução**: o sistema existia,
era instalável, e a razão registrada para não o ter corrido estava errada — a
busca pelo repositório havia sido feita com o nome trocado. A outra era um vazio
de **credencial**: o sistema corria, mas o arranque exigia uma chave paga que o
estudo declarava não possuir, e essa declaração deixou de ser verdadeira.

A distinção importa para o leitor porque muda o que ele deve concluir sobre as
ausências restantes. Um vazio de execução por engano de sondagem não diz nada
sobre o sistema; um vazio de credencial diz algo sobre o custo de o avaliar. Ao
fechar os dois, o que sobra de ausência no §6 passa a ser de um só tipo, e o
texto deve dizer qual.

## Por que os tetos de busca não se comparam pelo nome

Cada um dos sistemas expõe mais de um parâmetro que parece ser "quantos
resultados devolver", e eles não concordam entre si. Num deles há um teto
declarado generosamente e um segundo, mais apertado, que é o que de facto
governa: quem lê o nome mais visível sobredeclara a capacidade do sistema. A
consequência prática é que o número de candidatos que chega à fusão final é
fixado pelo parâmetro menos anunciado [→(a) §4].

Isto tem uma assinatura observável, e vale reportá-la em vez de a inferir: se o
teto morde, **toda** query devolve exatamente o mesmo número de resultados. Uma
distribuição de contagens com valor único é evidência direta de saturação, e
distingue-se de "o corpus não tinha mais" porque esta última produziria variação.

## Duas superfícies de retrieval, e a escolha de exercitar uma

Um dos sistemas expõe duas superfícies de busca com semânticas distintas: uma de
**memória por sessão**, onde vive a contribuição própria dele — sumarização e
extração por conversa —, e uma de **coleção**, que o trataria como armazém
vetorial genérico. Medimos a primeira, e o censo de rotas contra o container em
serviço mostra que a segunda nunca foi populada [→(a) §5.2].

Esta é uma escolha, não uma limitação, e o texto deve dizê-lo nesses termos. O
custo de varrer todas as sessões por query é o custo da superfície de memória sob
o mapeamento fiel de uma conversa por sessão — **não um teto do sistema**. Se a
busca de coleção daria resultado diferente é **não testado**, e não afirmamos que
daria igual nem pior. Fazer essa medição exigiria uma nova ingestão paga.

## Autonomia: o que é restrição do sistema e o que é decisão nossa

Duas configurações deste estudo parecem restrições dos sistemas avaliados e são
nossas. Removemos um servidor de embedding local que um deles oferece, para que
todas as colunas embedassem com o mesmo provedor e dimensão — decisão de
**comparabilidade**. E dispensámos, no outro, um caminho de classificação que a
assinatura da função de busca simplesmente não expõe.

Ambas empurram a leitura na direção **favorável aos sistemas avaliados**, e é
por isso que precisam de estar escritas: sem elas, um leitor concluiria que um
dos sistemas exige provedor pago para embedar, o que é falso. A tabela de
autonomia do manuscrito deve refletir isto.

## Retenção: dois mecanismos, um número, e o que ele não diz

Duas das colunas convergem para a mesma contagem de documentos retidos por
caminhos independentes, e duas para outra. A convergência não é coincidência nem
idiossincrasia do nosso carregador: é a consequência de honrar unicidade de
identificador num corpus que contém identificadores repetidos [→(a) §2].

Duas advertências, e a segunda é a que se perde com facilidade.

A primeira: comparar **mecanismos** entre corridas diferentes é legítimo — a
pergunta "este sistema recusa o segundo documento de id repetido?" tem a mesma
resposta em qualquer data. Atribuir os **números** a uma só população não é, e por
isso cada linha da tabela nomeia a sua corrida.

A segunda: esta convergência **não diminui** a assimetria medida dentro de uma
única população na corrida canônica anterior. São perguntas diferentes — uma é
sobre a política de identificadores, a outra sobre cobertura — e responder à
primeira não responde à segunda.

## Onde a contagem de retenção pode ser lida errada

Três contadores divergem por desenho ao longo de uma ingestão, e só um é
publicável: as linhas do registo de escrita, os diretórios em disco produzidos
pelo extractor, e o índice pesquisável. Os dois primeiros correm à frente ou
atrás por trabalho em curso; é o terceiro, **e só depois da sincronização final**,
que responde "quantos documentos esta busca pode alcançar" [→(a) §3].

O conferidor que usámos recusa reportar o número do índice se a última
sincronização não estiver marcada como final. Isso é deliberado: um número do
índice a meio da ingestão é plausível, é menor que o correto, e não traz consigo
nenhum sinal de que está incompleto.

## O que declaramos sobre falhas, e por que classificar em vez de contar

Houve falhas ao nível de sessão durante a varredura, e a sua **contagem** não
informa nada útil. A sua **origem** informa: separá-las entre defeito do nosso
cliente, do nosso pool de conexões e do provedor externo mostra que nenhuma é
falha de retrieval do sistema avaliado [→(a) §5.5].

Cada falha retira uma sessão do conjunto de candidatos daquela query. O efeito é
declarado, não corrigido — corrigi-lo exigiria repetir as queries afectadas, e
repetir só as que falharam introduz uma segunda corrida no mesmo número.

## Reprodutibilidade: a configuração não estava no artefato

O artefato de saída registra o que se pediu ao harness e não registra a
configuração de retrieval que produziu os resultados — modelo de embedding,
dimensão, reranker. Um valor publicado só com esse artefato não diz sob que
configuração foi obtido.

Capturámos a configuração do ambiente do processo enquanto ele corria, porque
depois do fecho deixa de ser observável, e o recibo fica ao lado do artefato
[→(a) §4.1]. O manuscrito deve apontar para o recibo, e o harness devia passar a
gravar isto no próprio artefato — está anotado como dívida, não como feito.
