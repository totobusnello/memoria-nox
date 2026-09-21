# Revisão adversarial dos dois manuscritos — 2026-09-21

Cinco vozes de famílias de treino distintas, lançadas em paralelo. Três no
`MANUSCRIPT-B.md` (o interventivo, escrito hoje), duas no `MANUSCRIPT.md` (o da
superfície, cuja lista de pendências pedia esta revisão desde 28/08).

> **Regra aplicada a todas:** achado que não bate com a fonte **não vira correção**.
> Cada afirmação factual foi conferida contra o ficheiro antes de qualquer edição. Isto
> não é desconfiança das vozes — é o que as torna úteis: uma voz que erra é informação
> sobre o prompt e sobre o transporte, e tratá-la como oráculo desperdiça as duas coisas.

---

## Paper B — três vozes, todas com recibo `exit: 0`

### DeepSeek V4-Pro — 8 achados, 5 aplicados

| achado | veredito | onde foi parar |
|---|---|---|
| H1b dito «inavaliável» quando é **trivialmente 1.0** sob o lock mantido | ✅ procede | §1 e §4.4 corrigidos |
| «não poderia detectar o próprio efeito» é absoluto demais | ✅ procede | abstract qualificado para H1c |
| critério trocado: §4.2 descarta H1a por sessão esparsa, §4.3 descarta H1 que **não** gira nela | ✅ procede, e é o mais forte | §4.3 reescrita em torno da identidade `H1 = H1a × H1c` |
| se o denominador mede ociosidade, `r̂`/ICC/`N` **herdam** o defeito | ✅ procede | §4.2, com a direção declarada desconhecida |
| números sem artefato nomeado sob promessa de rastreabilidade | ✅ procede, e **subestimou** | Apêndice B.1; dois nem tinham artefato |
| cabeçalho diz «revisão adversarial não feita» vs §6 diz que 6/7 vieram dela | ✅ ambiguidade real | cabeçalho distingue as duas revisões |
| §4.5 «jogada retórica»; não auditámos as outras projeções do mesmo documento | ⚠️ parcial | anotado; a auditoria não foi feita |
| classificação como «relatório de pós-morte» | opinião defensável | não alterado |

**Disparou dois achados nossos que ele não viu:** a análise ITT usa **20** clusters e não
19 (`09-02` teve 88 episódios e foi designado controlo; excluí-lo seria conditioning
pós-randomização), e a cobertura e o M10 **não tinham artefato nenhum** — eram script
ad-hoc nunca guardado.

### Grok 4.5 — 3 achados de severidade ALTA, todos aplicados

1. 🔑 **As duas estimativas de incerteza contradizem-se.** A `SPEC §3` pré-compromete
   *«nem a eliminação total das falhas repetidas é detectável a 80%»*; controlo = 0,0896,
   logo eliminação total = −0,0896; o IC95 é [−0,0560; +0,0086] e **exclui** esse valor
   por 0,0335. Para a spec valer, o IC precisaria de largura ≥ 0,0896; tem 0,0646 = **72%**.
   → nova **§4.1.1**, que reporta as duas, nomeia o defeito de cada uma e **não adjudica**.
2. **O caveat «intervalos otimistas» só aparecia onde o IC excluía zero.** Um método não é
   otimista seletivamente. → passa a valer para todos, inclusive o nulo.
3. **O bootstrap não reamostra o estrato B** — `E[Var_amostragem(B)]` ausente de todo
   intervalo; FPC ≈ 0,856. → nova **§4.4.1**. E a fórmula do estimador combinado, que o
   manuscrito omitia, foi escrita.

### GLM-5.3 — 7 condições para publicação; 5 aplicadas, 2 na working list

- 🔴 **O teste inferencial registado é re-randomização, não bootstrap** (`PREREG §5`,
  `SPEC §4`, 10.000 redesenhos). Substituído sem declarar. → **rodado**: controlo de
  300 padrões distintos em 300 réplicas reproduz a medição da spec; 9.941 distintos em
  10.000. **Contradiz o bootstrap em H1a** (p = 0,0855, não rejeita, onde o bootstrap
  excluía zero) e confirma H1c (p = 0,1603).
- 🔴 **A sensibilidade pré-comprometida é remover TODOS os parciais em bloco** (`SPEC
  §9.1`); reportámos «sem `09-14`», escolhida depois de ver o dado. → rodada e reportada
  primeiro. A registada é **mais** favorável ao nosso argumento que a post-hoc.
- 🔴 **Controles de instrumento não reportados** → dois rodados (positivo 11/11, dual
  negativo 8/8, sobre a janela completa); o terceiro declarado não executável.
- **Ancorámos a alocação em drand e o log de decisões em nada.** → §1.1 separa o que
  qualquer um verifica do que exige confiar em nós.
- **Regra de paragem não declarada**, e a questão de factibilidade: designação fixa em
  26/08 contra janela de frescor de 30 d pode tornar `N = 234` inviável por construção.
  → nova §3.0; a medição fica na working list.
- Overclaim «we knew this ten days before» — nove epochs eram projeção. → corrigido.
- Off-by-one alegado em «nineteen epochs … 0,32–0,97 h»: **falso positivo**, e a razão é
  interessante — o GLM assumiu 19 epochs analisáveis, que era o nosso próprio erro. Com
  20, a frase está certa.

---

## Paper A — uma voz inválida, uma pendente

### Codex (OpenAI) — parecer MAJORITARIAMENTE INVÁLIDO

🔴 **O parecer descreve um documento que não é este.** Quatro afirmações factuais,
conferidas uma a uma contra `MANUSCRIPT.md`:

| o parecer afirma | o ficheiro |
|---|---|
| *«não há seção §4.3.1 no documento lido»* | existe, **linha 596** |
| *«§4.3 trata de exposição por canal»* | §4.3 é o carrossel; exposição é §4.1 |
| *«§5.7.2 apresenta o teste `freshSlots`»* | o teste está no §4.3.1, linha 675 |
| *«o paper alega cobertura = 100%»* do corpus vivo | o 100% é do **pool elegível de 108 chunks**, nunca do corpus |

O achado que ele classificava como mais grave — *«a conclusão cobertura = 100% está errada
por denominador errado»* — é sobre uma alegação **que o paper não faz**. Um parecer cujas
citações não resolvem não é evidência sobre o manuscrito.

**O que sobrevive, porque não depende de citação:**

- **os sete filtros em série não são desagregados.** O §4.1 mede exposição total e o
  §4.3.1 atribui a não-exposição do **canal de cobertura** a padrões de caminho. O **pool
  principal** — 8 dos 10 slots — não recebe a mesma decomposição. A alegação «política,
  não capacidade» é sustentada para o canal e assumida para o principal. Vale uma seção,
  e está por fazer.
- **`freshSlots` só foi testado em 0 e 2.** Fora de escopo: o teto do §5 é dedutivo sobre
  o comparador, não empírico sobre os slots. Registado e não acionado.
- **generalização de sistema único** — já respondida pelo §4.5, terceiro marcador
  (*«um sistema, um corpus, um operador»*), escrito antes desta revisão.

### Kimi (Moonshot) — em execução

---

## O que esta rodada custou e o que devolveu

**Devolveu:** duas análises **registadas** que não tinham sido corridas e agora estão
corridas; uma contradição entre as nossas duas medidas de incerteza; a troca silenciosa de
uma sensibilidade pré-comprometida por uma post-hoc; e a distinção entre um controlo
**não executado** e um controlo **falhado**, que evitou publicar um alarme falso sobre o
próprio instrumento.

**Custou:** um parecer inteiro inválido por leitura errada, que teria produzido pelo menos
uma correção falsa se aceite ao pé da letra.

🔑 **A assimetria é o argumento a favor do método**, não contra: verificar cada citação
custou minutos; aceitar a do Codex teria posto no paper uma afirmação sobre um denominador
que o paper nunca usou.
