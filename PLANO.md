# PLANO — papers-memoria

> Gerado pelo `dev-flow` em 2026-11-04 22h (BRT). Fonte de verdade do projeto entre sessões.
> Revisado em 2026-11-04 22h10 depois das vozes Codex e Kimi (seção Vozes).

## Objetivo

- **Problema:** o memoria-nox já mediu muito sobre memória de agente que não está publicado:
  como a régua de busca em PT-BR engana, o que o KG de fato guarda, e que a memória empurrada pelo
  brief não deixa traço no que os agentes escrevem. Essas medições vivem em `audits/`, com várias
  gerações de números, algumas superadas. Publicar exige primeiro dizer qual número vale e de onde
  ele vem. O Paper 3 deixou também uma pergunta aberta: o critério C2 muda o que a destilação
  produz no corpus de produção que o motivou?
- **Para quem:** quem avalia ou constrói memória de agente, e o roadmap do nox-mem, que decide gasto
  (extração de KG, busca, brief) por esses números.
- **Entrega mínima (critério de aceite):** o paper A depositado no Zenodo com DOI, com manifesto de
  proveniência e gates de paridade e de privacidade verdes, e card no labf.bio. Zenodo dá
  arquivamento e DOI, não revisão por pares; o paper diz isso.

## Os quatro papers

| | objeto | formato | o que já está medido, na versão que vale | o que falta |
|---|---|---|---|---|
| **A** | Avaliar busca numa memória viva em PT-BR | paper completo | gold por chunk id apodrece (61 de 85 ids mortos, 71,8%); gold v2 ancorado por trecho: 95 âncoras, 91 exatas, 4 ambíguas, 0 não resolvidas; juiz chamou de verbatim 48 de 139 citações que não estavam no chunk (34,5%); juiz não sustenta negativa; cobertura inicial do top-10 de 9,1% (50/548); régua v3 com top-10 inteiro julgado (57 queries): strict 0,2567, pooled 0,4394; o check de citação de 8 palavras custa 0,105 de kappa (0,5458 → 0,4412, 510 pares); ideal montado só com o que o ranking devolveu superestimava o nDCG do juiz delimitado (queda de −6,8% era −15,6%) | separar o que é retrospectivo do que é novo; queries novas reservadas (holdout) para a parte confirmatória; amostra humana cega; um corpus sintético pequeno em PT-BR para os testes de método (reingest, troca de id, edição, exclusão) |
| **B** | O que um KG extraído por LLM guarda | nota de dados, descritiva | fidelidade 0,900 (135/150, Wilson [0,842; 0,938]), com a ressalva de que a amostra foi gasta para definir os critérios; 59 das 150 relações amostradas usam predicado hapax (39,3%); 82,2% da evidência do grafo vem do cofre de documentos (14.592 de 17.753; 74,7% na amostra); 98,7% das relações nascidas em julho | censo atual; amostra nova, adjudicada de forma independente, se a nota for afirmar fidelidade |
| **C** | Nenhum traço textual da memória empurrada | nota de dados, estreita e datada | 7a: 0 de 12.782 pares expostos com traço (1.524 mensagens, três raízes de transcript); R1: 0 de 574 mensagens nos dois braços, detector com controle positivo de 287/300 e 300/300; 337 de 382 buscas eram a sonda canária e nenhuma era de agente (até 21/10); 7b: controle positivo 0/10, fase principal não rodou, valor plantado aparece na ação em 3 de 28 | nada obrigatório; a nota afirma «não detectamos traço textual nem mudança da primeira ação nestes protocolos», e cita o 23/10, em que um agente com tarefa que exigia busca fez 11 e 6 buscas por conta própria |
| **D** | Paper 3b: C2 no corpus de produção | a decidir com o resultado | Paper 3: C2 contra C0 na janela cheia, +24,8 a +27,3 pp entre juízes nas 242; H4 (manuscrito v1.1, §6.7): comitê de 4 juízes −5,8 pp [−10,4, −1,2] contra a evidência crua | estimando: C0 contra C2 nas MESMAS sessões, pareado; começa por replay offline de sessões congeladas, sem deploy; shadow vivo só se a pergunta exigir custo ou deriva em produção |

**Ordem.**
1. **Base comum:** resolver a exposição de privacidade, montar o manifesto de proveniência, definir
   os estimandos.
2. **A**, com holdout novo e a faixa de nDCG apresentada como sensibilidade ao protocolo.
3. **C**, estreita e datada.
4. **B**, depois de C: a leitura de «grafo de contrato» depende de qual consumidor existe, e o único
   consumidor medido (23/10) era uma tarefa sobre contratos.
5. **D**, em paralelo desde já, mas só como replay offline até haver protocolo escrito.

## Fora do escopo

- Publicar texto do corpus privado, queries reais, nomes de arquivo do corpus ou endereço de host.
- Comparação com outros sistemas de memória (Paper 1).
- C2 ativo em produção; e o shadow vivo do D sem protocolo próprio e sem o seu ok.
- Afirmar «não uso» comportamental no C sem uma corrida com controle positivo válido.
- arXiv, salvo pedido seu.

## Intake

| Pergunta | Resposta |
|---|---|
| Tipo | pesquisa |
| Onde nasce | repo existente |
| Repo e caminho | `totobusnello/memoria-nox` (PÚBLICO) · `~/Claude/Projetos/memoria-nox`, uma pasta por paper (`paper-a-eval-ptbr/`, `datanote-kg/`, `datanote-pushed-memory/`, `paper3b-production/`) |
| Gerenciador | nenhum na raiz; Python 3 stdlib (`python3 -I`) e Node do nox-mem |
| Toca produção/cliente | `sim`, só pelo D, e só se o shadow vivo for aprovado; o replay offline não toca |
| Threat model | `não` para propriedade intelectual. Os riscos reais são **privacidade do corpus** (repo público, juiz externo) e **interferência em produção** (D), tratados como gates bloqueantes |
| O que sai | A: paper com números; B e C: notas descritivas; D: a decidir com o resultado |
| Ferramenta | Python e SQLite sobre backup `daily-main` descomprimido ou cópia `VACUUM INTO`; juiz pela Decisions API |
| Rota de publicação | Zenodo (scripts no padrão do Paper 3, publicação manual sua) + card no labf.bio com preview antes do merge |

## Gates

Cada um fica pronto quando passa no estado válido e reprova o infrator da coluna. Proveniência e
privacidade provados em 2026-11-04: os 12 testes passam com os gates intactos e os 12 casos de
infrator falham com os gates sabotados para sempre sair 0 (teste de mutação). Os outros se provam
no Setup de cada paper.

| Gate | Comando | rc esperado | Quando | Teste negativo: infrator | rc observado | Data |
|---|---|---|---|---|---|---|
| Proveniência | `python3 -I tools/provenance.py --check <pasta>`: cada número do texto tem entrada (afirmação, população, data, artefato, commit, `superseded_by`); falha se a fonte foi superada ou não existe | 0 | todo PR | citar 0,833 com `superseded_by`; número sem entrada; locator ausente; commit inexistente (`tools/tests/test_gates.py`) | 1 nos quatro | 2026-11-04 |
| Paridade | `python3 -I <pasta>/numbers.py --check`: recomputa cada número a partir de contagens | 0 | todo PR | trocar um número do texto | | |
| Privacidade antes do commit | `python3 -I tools/privacy-gate.py --staged`, chamado por `tools/hooks/pre-commit` (o hook global delega): linhas adicionadas de texto e blobs binários inteiros (PDF, membros de zip); arquivo concreto do cofre, do log de eventos do Mac ou de entidade de pessoa, host `srv`+6 dígitos, prefixo da tailnet, e 180 termos privados por hash (lista local, fora do repo) | 0 | todo commit, hook | um infrator de cada classe, cada um num repositório novo, mais zip e escape sem motivo (`tools/tests/test_gates.py`); e o JSON do KG que vazou: 116 bloqueios | 1 em todos | 2026-11-04 |
| Exportação por lista | os artefatos públicos saem só por `export.py`, com lista explícita de campos permitidos e ids aleatórios (nunca hash de query) | 0 | todo PR | acrescentar um campo de texto ao registro exportado | | |
| PDF | build + `check-layout.py`, zero glifos faltando | 0 | todo PR | inserir δ na fonte | | |
| Reanálise sem chave | `<runner>.py --analyze` reproduz o `.txt`; checksum de cada artefato no manifesto | 0 | todo PR | editar uma linha que muda o resultado | | |
| A: âncoras | `python3 eval/resolve-gold-anchors.py --db <snapshot> --gold <arquivo>`, contagem não vazia, ambíguas reportadas | 0 | antes da corrida | apontar um gold para trecho inexistente | | |
| D: não interferência | replay offline: roda C0 e C2 sobre banco de fixture e confere que nenhuma tabela, arquivo ou fila fora do diretório de saída mudou (hash antes e depois) | 0 | todo PR do D | fazer o C2 gravar em qualquer tabela do banco | | |

## Verificações manuais

| Verificação | Quem confere | Evidência | Última vez (data, PR) |
|---|---|---|---|
| Passe avoid-ai-writing antes das vozes e antes do depósito | Claude | diff no PR | |
| Precedência do pré-registro (A, D): push da tag antes da 1ª chamada, e queries do holdout nunca vistas antes | Claude, pelo activity log do GitHub | horários no texto | |
| Amostra humana cega dos pares discordantes (A) | você ou alguém que você indicar | planilha de rótulos fora do repo, só o kappa publicado | |
| O que vai para a Decisions API e onde ficam prompts e respostas | Claude, por escrito no protocolo | seção de dados do protocolo | |
| Preview do card no labf.bio | você | URL do preview | |
| Publicação no Zenodo | você | DOI público + `--readback` | |
| Shadow vivo do D, se houver | você aprova; Claude executa com limite de custo, de tempo e desligamento rápido | log do shadow e `/api/health` | |

## Etapa atual

Etapa: Work (paper A, parte prospectiva): H-A1 lido, H-A2 aguarda 18/11
Próximo passo: H-A2 no primeiro snapshot de 18/11 (cópia até 23/11; lembretes na agenda em 18/11
e 22/11); depois o texto do paper a partir de `paper-a-eval-ptbr/RESULTS.md`. Os itens abertos do README
foram resolvidos em 05/11 (Toto decidiu 1 a 3).
Feito em 05/11: tag `6c6879b` → `HOLDOUT-COMMITMENT.json` `54048e4` → score na VPS → amostra
humana → `HUMAN-COMMITMENT.json` `31d90b2` → leitura (saídas em `6120a37`). H-A1 se sustenta,
+0,1933 [+0,1421, +0,2464]; kappa humano × juiz 0,038, então o pooled não fica validado pelo
avaliador (§4).
Em paralelo desde 05/11 (Toto: «em paralelo os 2»): C, nota de dados em
`paper-c-pushed-memory/NOTE.md` (rascunho, proveniência 16 registros, 0 falhas), e o protocolo do D
(`paper-d-c2-production/`, rascunho, sem rodar nada pago).
PR em aberto: o da nota C · branch `paper-c-note`; o do protocolo D, quando o rascunho for revisado
Worktrees abertas: `~/Claude-worktrees/memoria-nox/paper-c-note`, `~/Claude-worktrees/memoria-nox/paper-d-protocol`
Último resultado dos gates: 2026-11-05 · proveniência do A 197 registros, 89 números, 0 falhas
(mutação: um número trocado no RESULTS reprova)

## Pendências

1. **BLOQUEANTE: há dados do corpus privado no repo público.** Conferido em 04/11:
   `audits/out/kg-s1-precision-2026-10-22.json` (desde `abf46ee`, 22/10) tem as 150 triplas da
   amostra, com nomes de entidades, citações literais e 112 caminhos para 82 documentos do cofre
   jurídico. `eval/golden-queries-v2.jsonl` (e v1, v3) tem as 66 queries com trechos literais do
   corpus e caminhos. **Feito em 04/11 (sua escolha «Tirar do main já»): PR #636, merge `379d64e`**,
   8 arquivos fora do `main`, no `.gitignore`, de volta ao disco local e com backup verificado em
   `~/Backups/memoria-nox-privado-2026-11-04/`. O v1 do golden set ficou (pré-registro do Paper 1).
   **Em aberto:** o histórico ainda os contém (reescrever é decisão sua), e o texto dos `audits/*.md`
   não foi varrido: isso é trabalho do gate de privacidade da base comum.
   **Achado no censo do gate (04/11):** o repo cita arquivos concretos de entidades de pessoas
   (`memory/entities/people/<slug>`, 76 menções) e, em 10 arquivos, caminhos concretos do cofre,
   do log de eventos do Mac ou nomes de host. O gate impede menções novas; as existentes ficam
   para a mesma decisão do histórico.
2. **A: holdout.** Escrever queries novas antes de ver qualquer ranking delas; sem isso a parte nova
   se chama «remedição de estabilidade», não confirmação.
3. **A: corpus sintético.** Pequeno, PT-BR, público, só para os testes de método. Os números de
   produção ficam como estudo de caso agregado.
4. **D: o `session-distill.ts` vive só na VPS.** Trazer o runner para um artefato versionado antes
   de qualquer experimento.
5. **Item 2 (GTM Phase 2):** memo separado; inclui tirar «retenção» da fala.

## Decisões

| Data | Decisão | Por quê |
|---|---|---|
| 2026-11-04 | Os quatro papers, A primeiro | sua escolha na ideação |
| 2026-11-04 | B e C como notas descritivas | as vozes mostraram que nenhum dos dois sustenta afirmação mais forte com o que existe |
| 2026-11-04 | C passa a afirmar ausência de traço textual, datada; não «não uso» | 7a e R1 medem texto; 7b falhou o controle e teve sinal em 3/28; em 23/10 houve busca de agente |
| 2026-11-04 | Faixa de nDCG do A = v3 [0,2567 · 0,4394], descrita como sensibilidade ao protocolo de anotação | o plano anterior misturava piso da v2 com teto de outra versão, e nenhum dos dois é limite demonstrado |
| 2026-11-04 | D começa por replay offline pareado C0 × C2 | não toca produção e responde a mesma pergunta sobre o que a destilação produz |
| 2026-11-05 | D: só C0 × C2 (sem C1, sem C0 como construído); amostra humana cega de 60 obrigatória; pré-registro com tag antes do sorteio das sessões | escolha do Toto; o resultado decide a segunda onda do GTM, e o kappa 0,038 do A mostrou que juiz LLM sozinho não basta |
| 2026-11-04 | Zenodo + labf.bio | precedente dos Papers 1–3 |

## Vozes

| Data | Ponto | Vozes | Recibo / parecer | O que mudou |
|---|---|---|---|---|
| 2026-11-04 | fim do Plan, challenge | Codex gpt-6-astra (130 s), Kimi k3.1-pro (618 s) | recibos `adversary-receipt-codex-2026-11-04T215237-1793.txt` e `adversary-receipt-kimi-2026-11-04T215241-2301.txt`, `exit 0`, cwd do clone | todos os achados conferidos nos audits e confirmados, menos um: o «−5,8 pp é o contraste errado», das duas, vem de lerem o manuscrito v1.0 do `main`; −5,8 é o comitê da v1.5. Mudaram a tabela inteira de números, a ordem, o recorte de C, o desenho de D e os gates (proveniência, privacidade antes do push, exportação por lista). O Codex achou a exposição de privacidade |
| 2026-11-05 | pré-registro, challenge (1ª passada) | Codex gpt-6-astra, Kimi k3.1-pro | recibos `exit 0`, cwd do clone (cópia untracked, apagada) | as duas contra fixar; quotas por script, gold = id sorteado, contrato de entrada, bootstrap estratificado, n 60→120, H-A2 simétrico, amostra humana obrigatória. Detalhe no §8 do pré-registro |
| 2026-11-05 | pré-registro, review (2ª e 3ª passadas) | Codex gpt-6-astra, DeepSeek v4-pro | idem | contra fixar nas duas; tag executada em vez da árvore, leitura só depois da nota humana, cadeia de commits conferida antes de calcular, score e labels presos ao compromisso humano, H-A2 em dia fixo e por exposição |
| 2026-11-05 | pré-registro, review (4ª passada) | Codex gpt-6-astra, DeepSeek v4-pro | idem | controle que para no limiar exploratório, H-A2 lê o compromisso publicado, banco registrado na amostra humana, tag ≠ compromisso, planilha com BOM ou `;` |
| 2026-11-05 | diff da 4ª, review (5ª passada) | Codex gpt-6-astra | idem | toda falha do controle para a leitura, salvo a registrada; cada compromisso escrito uma vez, depois da tag. Toto: «fixa a tag» (16:51) |

## Lições

| Data | Lição | Para onde foi | Aplicado? |
|---|---|---|---|
| 2026-11-04 | Dois scripts de depósito gravam `SHA256SUMS` no mesmo diretório: build+fill de cada um em sequência | só aqui; vira gate se repetir | não |
| 2026-11-04 | O teste de mutação achou um defeito no próprio teste: sem commit, `git reset` não tira do stage, e do 2º infrator em diante cada caso passava pelo arquivo do anterior | só aqui (comentário no teste) | sim |
| 2026-11-04 | O gate de proveniência reprovou o próprio README do A por citar valores superados como história, e depois achou dois defeitos dele mesmo (trecho compartilhado entre registros; faixa como valor). Contar correções é o assunto do A, então o gate ganhou `history` explícito por registro | só aqui | sim |
| 2026-11-05 | Um audit inverteu a própria tabela («60% das golds não respondem» quando a tabela diz 57 de 95 ACEITAS), e o registro de proveniência herdou a frase, não a tabela. Nenhum gate pega isso: o locator casa com o texto errado. Só apareceu ao ler o audit por inteiro para resolver um item aberto | errata nos dois audits; registro superado | sim |
| 2026-11-05 | A proveniência marcava o número registrado da abstenção como «superado» pelo do juiz, gravando como fato uma interpretação («corrected») que os audits não fazem. Supersessão é decisão de leitura, não só de cronologia | só aqui | sim |
| 2026-11-04 | Plano montado a partir da MEMÓRIA herdou números superados (0,833; 0,44–0,51; 9.398; 523); a memória guarda a 1ª versão e o audit guarda a correção | memória (feedback) | sim |
