# A régua de forma estava assimétrica — remedição dos quatro aceitos com o método deles

> Medido 2026-09-10, depois de o `fable-paper-optimizer` apontar que o
> `diagnostico-arxiv-2026-09-09.md` **não declara** se a bibliografia entrou na contagem
> dos aceitos. A investigação achou um defeito maior do que o suspeitado, e o efeito é o
> **oposto** do esperado: o nosso desvio de tamanho é maior do que o publicado, não menor.
>
> Este documento **substitui** a tabela do §2 do diagnóstico e a seção de alvos do
> `regua-recontada-2026-09-10.md`. O resto dos dois documentos segue válido.

---

## 1. O defeito: os dois lados foram medidos de formas diferentes

O diagnóstico declara *"prosa contada com blocos de código e linhas de tabela removidos,
para não inflar o **nosso** número"*. A frase é honesta sobre o que fez com o nosso
manuscrito — e é aí que está o problema: **o mesmo tratamento não foi aplicado aos
aceitos.**

Reproduzi o número publicado do Theoria (18.956) varrendo variantes de método sobre o
mesmo HTML (`arxiv.org/html/2607.16848`, o mesmo artefato — o `ltx_bibitem` dá 51, casando
exatamente com o diagnóstico):

| variante aplicada ao Theoria | palavras | delta vs 18.956 |
|---|---:|---:|
| bruto, só `<script>`/`<style>` removidos | 17.265 | −1.691 |
| sem tabelas | 14.204 | −4.752 |
| sem tabelas nem código | 14.204 | −4.752 |
| sem tabelas, código e bibliografia | 11.536 | −7.420 |
| **bruto, tokens incluindo símbolos** | **18.732** | **−224** ✓ |

Só a variante **crua** reproduz o publicado. ⇒ Os aceitos foram contados **com** as
tabelas, **com** a bibliografia e **com** tokens de matemática; o nosso, sem tabelas e sem
código. A razão publicada de **1,19×** compara o nosso número enxugado ao número cru deles.

## 2. Remedição: os quatro aceitos e o nosso, mesmo lado da régua

Todos crus, tokens com pelo menos um alfanumérico. Os quatro HTML são os mesmos artefatos
do levantamento original — `ltx_bibitem` = 21, 16, 11 e 51, idêntico ao publicado.

| paper | publicado | remedido (cru) | delta | refs | refs/mil |
|---|---:|---:|---:|---:|---:|
| MemMachine `2604.04853` | 10.724 | 10.112 | −5,7% | 21 | 2,08 |
| MERIT `2609.05441` | 6.662 | 6.094 | −8,5% | 16 | 2,63 |
| Human-Insp. `2605.08538` | 5.787 | 5.335 | −7,8% | 11 | 2,06 |
| Theoria `2607.16848` | 18.956 | 17.265 | −8,9% | 51 | **2,95** |
| **nosso** (`origin/main`) | 22.469 *(enxuto)* | **24.126** | — | **30** | **1,24** |

Os quatro aceitos caem 5,7–8,9% em relação ao publicado — **offset sistemático** do meu
tokenizador contra o original, na mesma direção e magnitude para todos, que portanto
**cancela na razão**. Controle: sob o método *conhecido* do `#509` (sem tabela, sem
código) o meu tokenizador devolve 21.832 contra os 22.469 registrados — os mesmos ~3%
para baixo, offset e não erro de escala. A diferença entre 1,19× e 1,40× é 18%, fora da
margem.

**Faixa dos aceitos, método uniforme:** 5.335 a 17.265 palavras · 2,06 a 2,95 refs/mil.
**Nós:** 24.126 palavras = **1,40× o maior aceito** · **1,24 refs/mil**, abaixo do piso.

## 3. O que isso muda na decisão — cortar palavra não resolve

| rota | ação | tamanho resultante | densidade resultante |
|---|---|---|---|
| **A** — só cortar | −6.861 palavras (**28%** do documento) | 1,00× o teto | **1,74/mil** — ainda abaixo do piso 2,06 |
| **B** — só citar | +20 referências (30 → **50**) | 1,40× o teto | **2,07/mil** — no piso |
| **C** — combinada | −3.000 palavras e +10 referências (→ 40) | 1,22× o teto | **1,89/mil** |

⇒ **A rota A é insuficiente sozinha.** Cortar mais de um quarto do manuscrito ainda deixa
a densidade abaixo do piso observado, porque cortar prosa move o numerador e o
denominador na mesma direção só até certo ponto — o déficit é de **referências**, e o
único lever que o fecha é referência.

Isso reabilita o **item 1** do diagnóstico (*"Bibliografia: 7 → 35-50 referências reais"*)
como a ação de maior retorno, e rebaixa a corrida por corte de palavras que o
`regua-recontada` tinha colocado à frente. O item 1 estava certo desde o começo; o que
estava quebrado era a medição da população contra a qual ele foi calibrado.

## 4. Terceira vez que esta régua move, e as três em direções diferentes

| # | data | o que dizia | o que era |
|---|---|---|---|
| 1 | 09-09 | *"7 apêndices vs 0"* ⇒ eu li como déficit e propus **criar** apêndices | os 7 eram **nossos**; o achado era **cortar**, e o `#494` já havia cortado C–G |
| 2 | 09-10 (#507/#509) | alvo de **3.513** palavras ou 13 referências | projeção de −5.159 era otimista; §5.1 não podia mover |
| 3 | 09-10 (aqui) | **1,19×** o teto, alvo de 3.513 | régua assimétrica ⇒ **1,40×**, e corte sozinho não fecha |

A lição que fica é a que já estava na memória e não impediu a terceira: **régua medida
não é régua verificada.** As três vezes o número publicado estava certo *para o método que
o produziu* — o que faltou foi declarar o método dos **dois** lados e conferir que era o
mesmo. Um número comparativo sem o método dos dois operandos declarado não é medição, é
coincidência de unidade.

## 5. Reprodução

```sh
for id in 2604.04853 2609.05441 2605.08538 2607.16848; do
  curl -sL -o "a-$id.html" "https://arxiv.org/html/$id"
  grep -o ltx_bibitem "a-$id.html" | wc -l    # confere contra a tabela do §2
done
```

Contagem: remover `<script>`/`<style>`, remover todas as tags, decodificar entidades,
contar tokens separados por espaço com ≥1 alfanumérico. Nada mais é removido — é essa
omissão que define a régua original.

⚠️ **O que este documento NÃO estabelece.** Que tamanho ou densidade tenham causado a
recusa de 2026-09-03 — o e-mail não trouxe feedback item-a-item, e a delimitação do §1 do
diagnóstico segue valendo. O que se afirma é só que somos outlier nas duas dimensões, com
a régua consertada, e que a ordem das ações muda por causa disso.
