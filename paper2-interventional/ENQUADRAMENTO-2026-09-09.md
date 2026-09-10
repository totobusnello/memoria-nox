# Enquadramento do Paper 2 — decisão de 2026-09-09

> **Instrução do Toto:** *"faz a dívida de infra e item 3 e regra 6 como sugeriria"*
> (09/09/2026, 16:01 BRT), em resposta à recomendação abaixo. O "item 3" era a única
> das três frentes que dependia dele: **o que o paper reporta.**

## A decisão

**O método vira a manchete. O contraste pré-registrado entra como piloto
subdimensionado declarado — com intervalo à vista e a frase explícita de que não é
evidência de ausência de efeito.**

## Por que, com os números recontados da fonte

O desenho pré-registrado (OSF `yf7d2`) pede **117/39/39/39 em 234 epochs**. A janela
elegível real é de **20 epochs** — os 19 designados têm `created_at` único
(2026-08-21 22:51:23Z) e a janela global de frescor é de 30 d, então todos expiram
juntos em **2026-09-20 22:51:23Z**.

Recontado de `ASSIGNMENT-SERVING.json` (sha `8957cc5fe8696204…`) em 09/09:

| recorte | controle (w=0) | w=2,0 | w=4,0 | w=7,5 |
|---|---|---|---|---|
| 20 epochs (com os 2 parciais) | 9 | 6 | 4 | **1** |
| 18 inteiros | 8 | 6 | 3 | **1** |

Os parciais são **2026-09-01** (tratamento, w=4,0, 22,38 h de 24) e **2026-09-20**
(controle, 13,86 h — o corte cai dentro do epoch). Descartá-los tira um do controle e
um do w=4,0; o braço de dose máxima é **n=1 nos dois recortes**.

**Reportar o contraste pré-registrado como resultado seria reportar um nulo que é
artefato de poder** — a exata família de defeito que este trabalho passou oito semanas
documentando. Não é uma escolha de tom: com `n=1` no topo da dose-resposta, o estimando
registrado **não pode ser estimado no poder registrado**.

## Adendo 2026-09-10 — alocado ≠ servido, e a pendência do `w=7,5` está fechada

Medido no `p2-serving.ndjson` (12.166 linhas, `modo` active 5.229 / shadow 6.937):

| | alocado | **servido** |
|---|---|---|
| controle (w=0) | 9 | **8** |
| tratamento | 11 | 11 |
| parciais | 2 | **3** |

**O epoch 2026-09-02 (controle) nunca foi servido.** Contado pelos dois métodos: por
`ts` há 252 registros no dia 09-02, por chave `epoch` há **zero**. Como o epoch vira às
09:00Z, esses 252 são as ~9 h de 00:00–09:00Z que pertencem ao epoch de 09-01 — e de
09:00Z em diante o serving parou. Controle positivo: 09-06 dá 672 nos dois métodos.

> Contar por dia-calendário diria *"09-02 serviu 252 briefs"*; contar por epoch diz
> *"nunca servido"*. As duas respostas saem do **mesmo arquivo**. É a chave temporal
> grosseira errando nos dois sentidos.

Parciais servidos: **09-01** (tratamento, w=4,0 — 630 de 672 em active, os 42 primeiros
ainda em shadow), **09-03** (controle, 441 de 672) e **09-20** (controle, corte às
22:51Z). O braço de controle entregue é **8**, não 9.

### A pendência do `w=7,5`: fechada, e não há dose-resposta a ler

O epoch de **2026-09-06** foi servido **inteiro** — 672 linhas. A preocupação de que ele
tivesse sido atingido por perda de dado é **falsa**.

Briefs em que a dose mudou o **pertencimento** do conjunto servido
(`set(ids_controle) != set(ids_tratado)`), por epoch de tratamento, `modo=active`:

| epoch | w | pertencimento muda | só ordem | % de servidos |
|---|---|---|---|---|
| 09-01 | 4,0 | 22 (de 630) | 11 | 3,49 |
| 09-04 | 2,0 | 35 | 5 | 5,21 |
| 09-05 | 2,0 | 33 | 0 | 4,91 |
| **09-06** | **7,5** | **38** | 0 | **5,65** |
| 09-08 | 2,0 | 20 | 28 | 2,98 |
| 09-09 | 2,0 | 19 | 20 | 2,83 |

`w=2` varre **2,83–5,21%** com n=4; `w=4` dá 3,49% com n=1; `w=7,5` dá 5,65% com n=1.
O extremo fica **acima** do topo do braço mínimo, e a dispersão dentro do próprio `w=2`
(2,83 a 5,21) é da ordem da diferença entre braços.

> **Com n=4 / n=1 / n=1 não há dose-resposta a ler.** Não é evidência de saturação e não
> é evidência de efeito. É a mesma conclusão do corpo deste documento, agora com o
> número que a produz.

⚠️ **Erro registrado:** a primeira versão deste adendo dizia *"a dose máxima não moveu
mais que a mínima"*, e era **falsa**. Vinha de comparar `ids_controle != ids_tratado` como
**lista**, sensível a ordem — que mistura reordenação com entrada/saída. Em 09-08 isso dava
48 onde o pertencimento muda em 20 (as outras 28 são só ordem). Reconstrução minha, não a
regra do código.

### Duas instrumentações, e a diferença é o achado

O guarda `p2-saturacao-da-dose` reportou, para o epoch 09-08:
`mexem_servido=0 churn_servido=0 estados=672`, com
`semantica=contrafactual-sob-a-designacao-ATUAL`.

O log de serving do **mesmo** epoch registra **20** mudanças de pertencimento e 20 com
`churn>0`. Não é contradição: o guarda **recomputa** um contrafactual sob a designação de
hoje, e o log guarda o que foi de fato servido no dia. O guarda rotula a própria semântica
no campo — e é por isso que a divergência é legível em vez de silenciosa.

Mas a implicação para o paper é direta: **um instrumento que recomputa reporta 0 onde o
registro do dia mostra 19 a 38 por epoch.** Quem inferir saturação do contrafactual está
lendo um zero que o serving não produziu. Os briefs que somem são os que a dose moveu —
porque a assinatura de busca usada para casar é a do controle.

Análise por replay do braço `n=1` perderia **100% do sinal registrado dele**. A associação
que este documento marcou como a verificar não era perda de epoch: **é perda de método.**

⚠️ **A verificar antes de o paper apoiar peso naquele epoch:** o único w=7,5 é
**2026-09-06**, a mesma data do defeito de seleção registrado no replay (o descarte
recaía justamente sobre os briefs em que a dose agiu). Associação a conferir, não
afirmada aqui.

## O que sustenta a manchete

Não é retórica de recuperação — é o que o ensaio produziu de verificável:

- **§10.17 a §10.25 do `DEVIATIONS-FOR-PAPER.md`**: sete defeitos de instrumento em
  produção, cada um com o predicado que o mantinha calado, e seis afirmações plausíveis
  falsificadas por uma consulta cada.
- A regra que atravessa todos: **guarda cujo predicado exige o dado que falta não cobre
  a falta do dado.** Apareceu em três instrumentos independentes no mesmo dia, e depois
  numa quarta forma pior — guarda que *afirma* divergência sem ler um dos operandos.
- Cada guarda corrigido tem **teste de mutação**, e no processo eu errei 2 de 4
  previsões de qual caso morreria. Esse erro é o dado que prova que prever não
  substitui testar.
- O corpus servido esteve a um `restart` da perda permanente — vivo só pelo fd 26 de um
  inode deletado — enquanto **três** guardas de integridade reportavam `orphans: 0`.

Nenhum desses achados sai de simulação. Saem de um ensaio pré-registrado rodando em
produção por oito semanas, e é por isso que ninguém os publicou.

## Forma proposta

| seção | conteúdo |
|---|---|
| principal | taxonomia dos defeitos de instrumento; o teste de suficiência de guarda; o protocolo de mutação (com os mutantes inválidos e o que eles ensinaram) |
| apêndice | desenho registrado (117/39/39/39 × 234) vs entregue (9 × 11 em 20); o motivo (janela de 30 d fechando em 20/09); ponto estimado **com** intervalo e `n` por braço na mesma linha; a frase de que não é evidência de ausência de efeito |

O ponto estimado **entra**. Esconder o número é o outro jeito de mentir sobre ele.

O pré-registro no OSF é o que dá credibilidade à declaração de subdimensionamento — é
ele que prova que 117/39/39/39 era a intenção, e não justificativa post-hoc.

## Rota descartada, e o custo dela

Redesignar e reiniciar recupera o desenho registrado por ~8 meses. Descartada porque o
desenho **não falhou por acaso estatístico — falhou por instrumento**: 32,5 h de epoch
nunca servido com a API viva, `top_chunk_ids` morto por 3,3 meses, corpus servido de
inode deletado. Reiniciar antes de consertar o instrumento compra a mesma falha mais
caro. Se algum dia for reiniciado, é *depois* de a taxonomia deste paper existir.
