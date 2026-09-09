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
