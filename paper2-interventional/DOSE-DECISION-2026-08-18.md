# A dose, re-derivada do mecanismo medido

> Sucessor de todo cálculo de dose feito contra `CUT_FRESH`. Insumo da emenda v1.12.

## A pergunta que eu tinha formulado errado

Eu disse que a decisão aberta era **dose absoluta vs relativa ao cut do agente**,
porque o cut principal medido varia de 0,6100 (lex) a 0,7922 (cipher).

**A pergunta não existe.** O tratamento age na via de **cobertura**, e o cut
principal é da via **principal**. Medido sob inflow, os dois slots de cobertura
são **idênticos nos seis agentes** — `[0.745, 0.7444]` — porque o sub-pool do
agente está vazio nos seis (`agentFresh = 0`) e tudo vem do sub-pool **global**,
que é compartilhado por construção (`source_file LIKE 'memory/entities/%'`).

A via de cobertura é **agente-independente**. A variação 0,61–0,79 é real e não
toca o mecanismo.

## O que a fila realmente é

Sob o lock de campos do §2 — `compiled` ⇒ `importance = 0.90`, `access_count = 0`,
`retention_days = 180` — a salience do chunk escrito é

```
base(sev, idade) = 0.495 + 0.15·2^(−idade/180) + 0.10·sev
```

Duas quantidades decidem tudo:

| | |
|---|---|
| degrau entre bandas de severidade | **0,0250** |
| spread de recency em **toda** a janela de 30 d | **0,0163** |

**O degrau é maior que o spread inteiro.** Logo idade **nunca** move um chunk
através de uma banda de severidade: a fila de cobertura é uma **escada de
severidade**, com idade desempatando apenas *dentro* da banda.

Isso é estrutura, não acidente do corpus — sai do lock de campos e da janela,
ambos registrados.

## A dose, contra a barra que existe

A barra do slot 2 sob inflow é o **S4 mais fresco** (S4 ≈ 0,08% de ~396/dia ⇒ ~1/dia):
**0,7445** analítico, **0,744818** medido. A dose necessária para passá-lo:

| sev | share das falhas | base @1d | `w` necessário | registrado (vs `CUT_FRESH`) |
|---|---|---|---|---|
| **S1** | 69,73% | 0,6695 | **6,98** | 6,03 |
| **S2** | 29,62% | 0,6945 | **2,33** | 1,85 |
| S3 | 0,58% | 0,7195 | 0,78 | 0,46 |
| S4 | 0,08% | 0,7445 | 0,00 | 0,00 |

### O que isso faz com a banda travada

| braço | admite | alcance |
|---|---|---|
| `w = 2.0` | S3+S4 | **0,66%** |
| `w = 4.0` | S2+S3+S4 | **30,28%** |
| `w = 7.5` | S1+S2+S3+S4 | **100,00%** |

*(registrado: 58,27% / 78,58% / 100,00%)*

**O ponto que decide: S2 precisa de 2,33 e o braço mais baixo é 2,0.** O modelo
morto dizia 1,85 e portanto que `w = 2.0` alcançava S2. Erra por **0,33** unidade
de dose — e essa fração é a diferença entre o braço mais baixo alcançar 30% ou
0,66% das falhas.

Duas derivações independentes deram os mesmos três números: a analítica acima e a
contagem de `INGRESS-INFLOW` (só S4@1d entra sem boost).

## A banda fica

Não recomendo re-centrar. Cada braço continua pousando numa **classe de
severidade distinta**, que é exatamente a regra de leitura dose-resposta que o §2
pré-compromete (*"um degrau em `w = 2.0 → 4.0` concentrado em S2"*). Sob a escada
medida esse degrau é **real e cai onde foi registrado** — o que muda são os
números de alcance, não a banda. E o braço baixo virar quase-nulo (0,66%) é
propriedade útil: vira **comparador ativo**, não braço inerte com rótulo.

## O contraste primário NÃO muda — e eu quase o mudei sem precisar

O §2 diz, em duas linhas (89 e 521):

> *"A testabilidade de H1 repousa inteiramente no teto de 60,18% de `w = 2.0`
> contra um MDE de 30%, então o primário fica intocado."*

**Isso é falso, e já era antes desta auditoria.** O contraste primário registrado
não é contra braço nenhum: §3 (linhas 344-351) aloca **117 controle vs 117
tratamento**, com os três braços *pooled* como tratamento. O GLM-5.3 já tinha
apontado exatamente isto na revisão da v1.10 — *"60,18% é o teto do braço mais
fraco, não do primário pooled (78,6%)"* — e a correção não alcançou as duas
linhas onde a afirmação vive.

Sob o mecanismo medido:

| | alcance pooled | contra MDE 30% |
|---|---|---|
| registrado | 78,95% | folgado |
| **medido** | **43,65%** | **ainda folgado** |

**O primário sobrevive intacto.** Nenhuma mudança de contraste, nenhuma
re-alocação, `r̂`/`p̂0`/ICC/`N_epochs` intocados.

⚠️ **Uma ressalva que não dá para omitir:** 43,65% é *alcance*. A quantidade que
o §2 compara contra o MDE é o **teto sobre o efeito incondicional**, que é outra
conta (a `w = 2.0`: alcance 58,27% → teto 60,18%). O artefato que produzia tetos
— `REACHABILITY-2026-08-16.md` — é do modelo morto. O teto pooled tem de ser
recomputado sob o mecanismo medido antes de "sobrevive" virar afirmação final; a
margem (43,65% vs 30%) é grande o bastante para tornar a inversão improvável, e
pequena o bastante para não ser assumida.

## Fica em aberto para a v1.12

- *"Um slot, by construction"* foi medido sob o modelo morto. A designação é um
  chunk **por assinatura**; várias assinaturas podem impulsionar ao mesmo tempo, e
  `freshSlots = 2` limita a dois. Precisa ser re-medido, não re-argumentado.
- `Δ_cut = 0.043` continua sendo o multiplicador da dose e **não** é o spread dos
  slots (0,0951–0,2773) nem o gap adjacente (0,0038–0,0157). Como a escada de
  severidade agora dá o referente, `Δ_cut` pode ser reexpresso como fração do
  degrau **0,0250** — `w = 1.0` a S4 move 0,043, isto é **1,72 degraus**.
