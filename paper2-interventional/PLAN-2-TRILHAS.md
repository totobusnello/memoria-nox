# Plano — duas trilhas em paralelo

> **Data:** 2026-07-26 · **Estado:** P2S1 Chunk A e B fechados (T1–T5 em produção, modo `off`); §9 item 3 fechado com números medidos.
>
> Complementa `NEXT-STEPS.md` (que governa o **gate** do arXiv) e `specs/2026-07-25-P2S1-serving-side-snapshot.md` (que governa o mecanismo).

---

## O que mudou e por que agora cabem duas trilhas

Até 25/07 havia uma fila única: o mecanismo de snapshot era o **único bloqueador de engenharia** entre o desenho e o piloto. Ele está construído e em produção. Sobram três itens de engenharia — todos **mutuamente independentes** — e sete itens de decisão no §9 do pré-registro.

Isso permite paralelismo real. Mas as trilhas **não são independentes em dois pontos**, e é isso que o plano precisa acertar.

---

## Os dois acoplamentos que importam

**1. ~~O shadow (T6) produz o número que a curva de poder (§9.7) precisa.~~ — ERRADO, corrigido em 26/07.**

> **O que eu escrevi aqui estava errado.** A afirmação era que a rodada de shadow do T6 produziria a estimativa de variância que a curva de poder exige. Ao executar o T6 e reler o §9.7 lado a lado, não fecha: o item pede `r̂` (taxa de oportunidade por hora-sessão), `p̂0` (taxa condicional de repetição no controle) e **ICC** — todas quantidades de **desfecho**. O shadow roda sem braços vivos e sem desfecho; ele mede **exposição**, não resultado.
>
> O próprio prereg já dizia isso e eu não tinha cruzado: *"Pre-registered pilot (F5 fix). Before the pilot runs, we lock: the pilot's own metric definitions (`r̂`, `p̂0`, ICC estimate)…"*. As quantidades vêm do **piloto**, que é replay-only e está gated no arXiv.
>
> ⇒ **§9.7b é gated no piloto, não no T6.** T6 não destrava a curva de poder. O acoplamento que eu tinha desenhado não existe.

**O que o T6 produz de verdade — e é necessário por outro motivo: a dose.**

Quanto os dois braços diferem no que servem. Medido em 26/07: o brief só admite conteúdo novo pelos `freshSlots: 2`, e um chunk com `pain=1.0`/`importance=1.0` entrou em **1 de 10** briefs antes de ser expulso (nasce com `access_count=0`, e `access` pesa 0,20 na salience v2).

Dose perto de zero é achado forte **e ruim**: tratamento homeopático, e nenhum `N` salva o estudo. Isso entra no §9.7 como restrição de viabilidade — não como insumo da fórmula.

**2. O hash do pipeline congelado (§9.5) exige que a engenharia pare de mexer.**

O item 5 pede o commit do pipeline congelado e o hash do PAP. Congelar antes de T6/T7/T8 landarem significaria congelar algo que ainda vai mudar.

⇒ **§9.5 fecha depois da trilha A inteira.**

Fora esses dois, tudo mais corre em paralelo.

---

## O gate que continua valendo

`NEXT-STEPS.md`: *"nada de execução do Paper 2 começa antes do Paper 1 sair do hold"*.

Isso **não** bloqueia decisão nem escrita. Bloqueia o **piloto** — e o piloto é onde §9.7 termina (a função `f` tem que estar travada *antes* dele; `N_epochs` e calendário saem *dele*).

Estado do gate: arXiv `submit/7771319` em `on hold`, inquiry enviada 25/07, **não recontatar antes de ~08/08**.

⇒ §9.7 fecha em **duas metades**: a função `f` (decisão, agora) e os derivados (pós-piloto, gated).

---

## Trilha A — engenharia (fecha o P2S1)

Os três são independentes entre si e podem sair em qualquer ordem, ou juntos.

| # | O quê | Produz | Risco |
|---|---|---|---|
| **T6** | Shadow sobre N boundaries, sem tráfego real. Verificar os 6 critérios do §6 — sobretudo brief-do-snapshot **byte-idêntico** ao brief-do-live congelado no mesmo instante. | Validação do mecanismo **+ a variância que §9.7 precisa** | Médio: a comparação "live congelado no mesmo instante" é a parte sutil — na prática, comparar imediatamente após o snapshot, antes de qualquer write |
| **T7** | Erro do M2 (filtro lógico `created_at <=`) contra o M1 (snapshot físico): quantos chunks divergiriam por epoch. | O número que decide se M2 é fallback aceitável — **entra no prereg como declaração** | Baixo: é medição sobre dados que já existem |
| **T8** | Ensaios de falha: snapshot corrompido, disco cheio, `vec0` ausente. Confirmar degradação para o snapshot anterior, nunca servir vazio. | Confiança no fail-open que já está codificado | Baixo: o caminho já existe e tem teste unitário; falta o ensaio ponta a ponta |

**T10** (degrade para Route 1) está **morto por K1 ter passado** — fica como fallback documentado, não como trabalho.

---

## Trilha B — decisões do pré-registro (§9)

Sete itens. A coluna que importa é **quem decide**: cinco precisam de você, dois eu entrego em rascunho.

| # | Item | Quem decide | Nota |
|---|---|---|---|
| **4** | Valor de `W_OUTCOME` (0.15 proposto) + allowlist de low-stakes | **Toto** | É trade-off de sensibilidade: peso alto amplifica desfecho raro, baixo dilui. Posso trazer o cenário numérico dos dois lados |
| **5** | Taxonomia do `sig()` + commit do pipeline congelado + hash do PAP sintético | Misto | Taxonomia é desenho; hash é mecânico. **Gated na trilha A** |
| **6** | Limiares: severidade (0.5) e Fleiss' κ (≥0.75) | **Toto** | κ 0.75 é convencional-forte; 0.6 é aceito em muita literatura. Escolha afeta quanto do painel vira não-adjudicável |
| **7a** | Função-piloto `f` — **travada antes do piloto** | **Toto** | Bloqueia o piloto inteiro |
| **7b** | `N_epochs`, MDE (20%), fim de calendário, curva de poder | Derivado | **Gated em T6** (variância) **e no arXiv** (execução) |
| **8** | Piso de cobertura (95%), teto de não-adjudicável (10%), winsorização (p95) | **Toto** | Números convencionais; vale confirmar se servem ao seu apetite de risco |
| **9** | Apêndice A (figuras H3) + Apêndice B (matemática dos bounds) | **Eu rascunho** | Apêndice B é a matemática de Aronow–Samii que já está decidida; é redação |
| **10** | Declaração de ética/IRB | **Eu rascunho** | Simplificada: sem sujeitos humanos, sem contribuidores humanos |

---

## Ordem recomendada

**Agora, em paralelo:**

- **A:** T7 e T8 (independentes, baratos, sem gate)
- **B:** §9.9 e §9.10 (eu rascunho, você revisa)

**Em seguida:**

- **A:** T6 — é o mais pesado e o que destrava §9.7b
- **B:** §9.4, §9.6, §9.8 e §9.7a — as quatro decisões que são suas. Rendem mais numa conversa que num PR

**Por último:**

- §9.5 (congelar pipeline + hash) — depois que a trilha A parar de mexer
- §9.7b (curva de poder) — depois de T6
- Piloto — gated no arXiv ID

---

## O que este plano NÃO resolve

O caminho crítico do **paper** não é engenharia: são as quatro decisões suas (§9.4, 6, 7a, 8). Se elas não saírem, a trilha A termina e o pré-registro continua sem poder ser travado.

E o piloto continua gated em coisa fora do nosso controle — a moderação do arXiv.
