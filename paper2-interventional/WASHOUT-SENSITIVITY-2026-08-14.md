# O washout de 2h basta? — análise exploratória, 2026-08-14

> ⚠️ **Exploratória, não pré-especificada.** Não entra no desfecho do estudo e
> não altera nenhum número do `pilot_replay`. Existe para desbloquear uma
> decisão de desenho: `SIZING-2026-08-14-v2.md` §4 mostra que encurtar o epoch
> é a única alavanca que compra calendário sem vender MDE (24h→242 d,
> 8h→113 d), mas o washout é **fixo em 2h** — custa 8% de um epoch de 24h e
> 25% de um de 8h — e a premissa de que 2h bastam nunca foi verificada.

## Resposta curta

**Sim, para o efeito de borda que existe sem tratamento.** A anomalia está
concentrada nas duas primeiras horas e o nível de base já é atingido em 2–4h.
O washout de 2h captura o fenômeno inteiro, com pouca folga e pouco
desperdício.

Isso **não** licencia epoch curto sozinho — ver §4.

## 1. Onde o efeito está: incidência de erro

`is_error` é **censo** — sem amostragem, sem peso, sem composição que possa
confundir. É o teste limpo.

| zona | n | taxa `is_error` | IC 95% |
|---|---|---|---|
| **0–2h** | 2.090 | **10,67%** | [9,42% ; 12,07%] |
| 2–4h | 1.616 | 6,68% | [5,57% ; 8,01%] |
| 4–6h | 1.112 | 4,50% | [3,43% ; 5,88%] |
| 6–12h | 2.614 | 6,69% | [5,80% ; 7,72%] |
| 12–24h | 2.147 | 6,61% | [5,64% ; 7,74%] |

0–2h contra todo o resto: **10,67% vs 6,34%**, diferença **+4,33 pp**,
IC 95% **[+2,89 ; +5,76]**, não cruza zero.

A fronteira do epoch **não é um ponto neutro**: erra-se 68% mais nas duas
primeiras horas. E o efeito **termina ali** — 2–4h (6,68%) já é
indistinguível de 12–24h (6,61%). O washout está bem calibrado: nem curto
demais, nem generoso.

O bin 4–6h (4,50%) fica *abaixo* da base, com IC quase tocando-a. Não tenho
explicação e não vou inventar uma; com n=1.112 e cinco bins olhados, é o tipo
de coisa que aparece por acaso.

## 2. Uma armadilha que eu caí, e por que ela fica registrada

A primeira leitura desta análise comparou `p0` agregado entre zonas e concluiu
que havia efeito de borda: **0,397 em 0–2h contra 0,316 em 2h+**, IC da
diferença [+0,026 ; +0,136], sem cruzar zero. Parecia limpo.

Estava errado. A **composição** varia entre as zonas:

| zona | % estrato A | `p0` no A | `p0` no B |
|---|---|---|---|
| 0–2h | **37,5%** | 0,967 (n=151) | 0,056 (n=252) |
| 2–6h | 30,5% | 0,880 (n=108) | 0,037 (n=246) |
| 6h+ | 29,8% | 0,960 (n=227) | 0,056 (n=534) |

Com `p0_A ≈ 0,96` contra `p0_B ≈ 0,05`, uma diferença de 7 pontos na proporção
de A move o agregado sozinha. Aplicando a composição de 2h+ à zona 0–2h:
`0,30 × 0,967 + 0,70 × 0,056 = 0,329`, contra os 0,316 observados. **O efeito
some.** Dentro de cada estrato não há gradiente algum.

O agregado continua na saída do script, marcado
`testes_confundidos_NAO_USAR`, em vez de removido — quem reproduzir precisa
ver a armadilha, não um resultado limpo que esconde que ela existia.

Note que a composição variar **é** o achado do §1 visto por outro ângulo: há
mais estrato A em 0–2h porque se erra mais em 0–2h. O sinal era real; o
estimador é que estava errado.

## 3. E o `p0`?

Não há gradiente de `p0` dentro de estrato. O que muda perto da fronteira é
**quantos erros acontecem**, não **com que frequência um erro conhecido se
repete**. São coisas diferentes, e só a segunda é o desfecho do estudo.

## 4. O que isto NÃO autoriza

**No corpus do replay, todo epoch é controle — nunca houve troca de braço.**
Portanto isto não mede carry-over de tratamento. Mede a estrutura temporal
intra-epoch na ausência de intervenção: ritmo de trabalho, sessões que
atravessam a fronteira, fuso.

A lógica é assimétrica, e é preciso ser explícito sobre a direção:

- Gradiente aqui **provaria** que 2h não bastam nem sem tratamento.
- Ausência de gradiente **não prova** que bastam sob tratamento.

O que este resultado faz é remover uma objeção, não conceder uma licença. A
premissa "2h lavam o efeito do braço anterior" segue sem evidência direta —
só se sabe agora que ela não está sendo contrariada pelo comportamento
natural do sistema.

Para epoch curto especificamente: como o efeito de borda natural dura menos de
2h, o washout de 2h continua capturando-o em epochs de 8h ou 6h. O que piora
não é a suficiência, é o **custo** — 25% do epoch a 8h, 33% a 6h — e isso a
tabela do §4 do sizing já modela.

## 5. Reprodução

```
python3 washout_sensitivity.py \
  --episodes universo-combinado.jsonl \
  --verdicts verdicts-combinado-v2.jsonl \
  --estrato-b-ids estrato-b-ids.txt \
  --replicas 'tiebreak-rep*.jsonl' 'tiebreak-v2-rep*.jsonl' 'extensao-moonshot-cycle-*.jsonl'
```

Corpus: 9.579 episódios, 30 epochs, 7.184 pares `(episódio, painelista)`.
Testes de proporção rodam em contagens **brutas** — o peso HT amplifica o
estrato B por ~5,2× e inflaria qualquer `n` usado num teste, produzindo
significância onde não há.
