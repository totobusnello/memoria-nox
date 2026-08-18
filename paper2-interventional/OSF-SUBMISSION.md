# Submissão OSF — checklist e metadados

> ### ✅ REGISTRADO — 2026-08-18T07:56:44Z, GUID `yf7d2`
>
> | | |
> |---|---|
> | URL | **https://osf.io/yf7d2/** |
> | `date_registered` | **2026-08-18T07:56:44.270663Z** — é este o timestamp externo que ancora o `T_seed_assign` |
> | Schema | **Open-Ended Registration** v3 (`5df83f7dd28338001ac0ab0d`), como este documento recomendava |
> | Anexos | `PREREG-v1.11-2026-08-17.pdf` (2.004.652 B) · `.html` (298.817 B) · `PREREG-DRAFT.md` (249.710 B) — sha256 dos três conferidos contra o local **e** contra o depósito do Zenodo |
> | Licença | CC-By Attribution 4.0 International; copyright holder Luiz Antonio Busnello, 2026 |
> | Subjects | Artificial Intelligence and Robotics · Applied Statistics (o OSF anexou os ancestrais) |
> | Embargo | **nenhum** — público imediato, conforme a recomendação abaixo |
> | Estado | arquivamento **concluído** 07:58:05Z; `pending_registration_approval: true` |
>
> ⏳ **Falta um clique seu, ou o prazo.** O OSF manda um e-mail de aprovação a cada admin. A janela é de **48 h** (da meia-noite do dia da submissão à meia-noite do segundo dia); se nenhum admin rejeitar, o registro é **aprovado automaticamente** e fica público. Não existe caminho de aprovação pela interface web — só o link do e-mail (documentação do OSF, `help.osf.io/article/330`). Aprovar pelo e-mail deixa público agora; não fazer nada deixa público no fim do prazo. **Rejeitar é a única ação que o descarta.**
>
> ⚠️ **A API v2 documenta sim a criação de registros** — a nota abaixo dizia que não e o caminho seria a web UI. Foi feito inteiramente por API: `POST /v2/draft_registrations/` → `PATCH` (título, descrição, licença, tags, subjects, `registration_responses`) → upload via WaterButler no draft node → `POST /v2/registrations/`. Duas armadilhas: `subjects` exige **lista simples de ids** (uma lista de caminhos hierárquicos dá 400), e registrar **falha com 400** sem ao menos um subject — nada disso aparece no formulário da UI.
>
> ⚠️ **Não mexer nos arquivos do draft node `g9qtx` durante o arquivamento.** A própria página avisa que qualquer alteração nessa janela causa falha de arquivamento e **perda do timestamp**. O arquivamento já terminou, então esse risco passou.
>
> **`T_seed_assign` NÃO foi declarado.** Ver o cabeçalho do `PREREG-DRAFT.md`: a decisão de 17/08 é sortear **depois** de congelar o mecanismo, e o mecanismo não está congelado (`staged/P2S2-outcome/` não construído, `NOX_EPOCH_SNAPSHOT` ainda em `shadow`).

---

> **Preparado 2026-08-15.** Tudo abaixo está pronto; **o envio é seu**, porque exige login e porque registrar é publicação externa e irreversível. ~~A API v2 do OSF não documenta criação de registros — o caminho é a web UI.~~ *(Corrigido em 18/08: foi tudo por API — ver o bloco acima.)*

## Template: **Open-Ended Registration**

É o template que aceita um documento já escrito como anexo, em vez de preencher um formulário estruturado. O outro candidato — *OSF Preregistration* — exigiria redigitar 124 KB em campos, com risco de divergir do original.

## Arquivos para anexar

| Arquivo | Onde | Nota |
|---|---|---|
| `PREREG-v1.11-2026-08-17.pdf` | scratchpad da sessão (1,9 MB, 85 pp) | **Anexo principal.** Emoji e símbolos convertidos para ASCII; gerado via Chrome headless a partir do HTML (a instalação LaTeX local está incompleta). Números travados conferidos no texto extraído |
| `PREREG-v1.11-2026-08-17.html` | scratchpad (290 KB) | Preserva tabelas e formatação melhor que o PDF; anexar como secundário se o OSF aceitar |
| `PREREG-DRAFT.md` | repo | O original. O PDF é derivado dele |

⚠️ **O que NÃO anexar:** nada de `~/.paper2-verdicts/` nem do `action-archive`. Os episódios carregam conteúdo real de trabalho. O registro aponta para hashes (`CORPUS-FREEZE.md`, `corpus-manifest-*.txt`), não para o corpus.

## Metadados sugeridos

**Título** — `DECISIONS.md` deixa dois candidatos e não trava nenhum. Para o registro (que não é o paper), o mais descritivo serve melhor:

> *Interventional Memory: A Pre-Registered Randomised Crossover Measuring Whether Agent Memory Changes Agent Behaviour*

**Descrição (abstract do registro):**

> Retrieval metrics score representation, not decision. This study measures whether the composition of an agent's memory changes what the agent *does*, using a fleet-wide randomised crossover on live production traffic rather than a curated benchmark. Epochs of 24 h are assigned to arms by a public randomness beacon whose round is declared before it exists; outcomes are adjudicated blind by a frozen multi-model panel; the primary outcome is repeated-failure density per session-hour. N = 234 epochs, powered for relative effects >= 30%, sized on the upper confidence limit of the intra-cluster correlation with an unequal-cluster design effect (cv-squared = 0.3833, a locked input measured over the same pilot window as every other sizing parameter). The treatment writes one memory chunk per adjudicated-failure episode, in both arms, and differs only in a serving-time salience boost, so the contrast isolates weighting from creation. The boost is applied to the two coverage slots and never to the eight primary ones — a registered restriction on where it acts, not a property discovered by measurement. What measurement establishes is how much of the failure population it can reach, and that turns out to be a property of the arm rather than of the design: the lowest dose reaches 58.27% of opportunities and the highest reaches all of them. Pooling the three dose arms, the primary contrast is bounded at an effect ceiling of 78.6%, and its weakest arm alone at 60.18% — both above the 30% effect it is powered to detect. These bounds are declared rather than discovered. All parameters were fixed on a historical corpus with no arm assignment, before any randomised epoch existed.

**Licença:** CC-BY 4.0 — mesma do repo, e o registro é para ser citado.

**Contributors:** decisão sua. Se o contato com Stanford evoluir, adicionar depois é possível; remover é mais difícil.

## A decisão que precisa ser tomada antes de clicar

**Embargo, ou público imediato?**

| | A favor | Contra |
|---|---|---|
| **Público imediato** (recomendado) | É o ponto inteiro do pré-registro: qualquer um pode verificar que o desenho precede os dados. Casa com a cadeia de seeds declaradas antes dos rounds. Fortalece a mensagem ao Stanford em 21/08 — mostrar registro público é mais forte que descrevê-lo | Expõe o desenho a quem quiser correr na frente. Dado que MemoryArena e Evo-Memory são de grupos com muito mais capacidade, isso não é hipotético |
| **Embargo** (OSF permite até 4 anos) | Protege a prioridade enquanto o estudo roda | Um pré-registro sob embargo não pode ser citado como evidência de precedência até abrir. Enfraquece exatamente o ativo que estamos construindo |

**Recomendação: público imediato.** A vantagem defensiva do embargo é pequena — o desenho já está num repo público desde julho, e o `git log` já é o carimbo de precedência. O que o OSF adiciona é o timestamp *externo*, e ele só vale se for verificável.

## Depois de registrar — a cadeia dispara

1. Anotar o **timestamp OSF** e o **GUID** do registro.
2. Declarar `T_seed_assign`: um instante UTC estritamente **posterior** ao timestamp OSF e **anterior** ao primeiro epoch de tratamento (§2, M4). Commitar no repo antes de o round drand correspondente existir — mesmo padrão das três seeds anteriores.
3. Primeiro epoch randomizado → fixa a data-limite de calendário (§3).
4. Atualizar `PREREG-DRAFT.md` com o GUID e os dois valores; o registro no OSF fica congelado, o repo continua sendo o espelho vivo.

## Verificações feitas antes de declarar v1.0

- [x] Todos os `[TO LOCK]` que exigiam análise, fechados (N, δ, p95; α já estava)
- [x] **17/08 — emenda v1.11, `N` 174 → 234.** Correção de erro, não reajuste de tamanho: o efeito de desenho vinha da fórmula de **cluster igual** (`1 + (m̄−1)×ρ`) num desenho cujos epochs vão de 1 a 115 sessões. Sob a fórmula correta (`cv²` = 0,3833, travado como **entrada**) o DE vai de 9,973754 para 13,482928 e o `N` no limite superior do ICC a MDE 30% vai para **234** (alocação 117/39/39/39, exata). Direção importa: a fórmula antiga **sub-dimensionava**, que é o que o lock (b) de 30/07 existe para proibir — logo 174 nunca satisfez o padrão sob o qual foi escrito. MDE inalterada em 30%; `r̂`, `p̂0`, ICC, `m̄`, `λ₀`, `δ`, banda de dose e alcance intocados. Emendado **antes** de qualquer epoch randomizado, de qualquer braço atribuído e do round do beacon
- [x] Números travados consistentes em todas as menções — corrigidas duas contradições reais: a tabela de riscos listava "MDE 20%" como mitigação, e o `N` estava dimensionado no **ponto** do ICC quando o lock (b) de 30/07 manda dimensionar no **limite superior**. Lock final: **N = 174, MDE 30%, limite superior** (e o valor histórico a 25% no ponto era 152, não 154)
- [x] Cabeçalho do documento atualizado de "DRAFT v0.3 (NOT LOCKED)" para "v1.0, READY TO REGISTER"
- [x] ~~PDF/HTML regerados em 15/08 12:08~~ (v1.1, superado pelo lock do `linked`) e conferidos no texto extraído: `174 randomized epochs`, `30% relative`, `36,67`, `7,45 s`, `65 206`, `0,1814`. Os arquivos v1.0 (com `154`/`25%`) foram apagados para não serem anexados por engano
- [x] Nenhum dado de episódio no repo público
- [x] Achados adversariais fechados: Kimi 3 GRAVE (1 corrigido por `N`, 1 declarado como irreparável — teto de dose, 1 corrigido) + 3 menores; Grok 3 BLOQUEIA + 8 CORRIGIR + 5 cosméticos
- [x] Controle positivo completado com o 5º painelista (`moonshot` S4 em 4/4), **não cego, declarado como tal**
- [x] `linked` travado como identidade + escrita nos dois braços (§2). Fechou o último termo indefinido; **nenhum número travado mudou** porque `r̂`/`p̂0`/ICC já tinham sido computados sob o modelo do §3
- [x] **PDF/HTML v1.3 gerados 13:52** e conferidos no texto extraído: `174 randomized epochs`, `The link is identity`, `BOTH arms`, `69.73%`, `0.7342`, `65 206`. Os v1.0 e v1.1 foram apagados
