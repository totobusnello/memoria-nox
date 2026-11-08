**Eu não congelaria esta versão.** O contraste está correto, mas faltam garantias de integridade da execução e a interpretação proposta excede o que a comparação identifica.

Li integralmente os cinco arquivos no commit `78e66a2`, além das funções importadas relevantes. Fiz verificações sintéticas locais, sem chamadas pagas nem alterações. Não tenho como atestar que pertenço a uma família diferente da que escreveu o desenho: a autoria não está estabelecida nesses arquivos.

1. **[Alta] “Extrator mais forte” não é uma variável isolada pelo desenho.**

   O protocolo mantém família e geração, mas troca o modelo inteiro. Não há validação independente de superioridade de extração **com thinking desligado**, nem separação entre capacidade, obediência ao prompt, calibração de importância, verbosidade e compatibilidade com R3. O smoke mede custo e quantidade, não qualidade.

   Assim, uma interação negativa identifica uma diferença entre **esses dois sistemas configurados**, não demonstra que regras sejam uma “muleta para extrator fraco”. O leitor Gemini compartilhado também pode favorecer diferentemente as representações dos dois extratores; trocar a família do juiz não resolve isso.

   **Antes da tag:** tornar “força” uma interpretação hipotética e definir o estimando como interação entre *modelo/configuração* e critério.

   Referências: [PREREGISTRATION.md:8–14](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:8), [43–48](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:43), [150–156](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:150); [SMOKE-RESULT.md:95–105](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/SMOKE-RESULT.md:95).

2. **[Alta] Reutilização cria uma comparação entre extrações históricas e novas; o pareamento não elimina isso.**

   L_C0/L_C2 vêm do Paper 3; F_C0/F_C2 vêm da nova execução, predominantemente batch. Modelo fica associado a época e via de execução. Não afirmo que tenha ocorrido drift ou diferença batch/sync; afirmo que o desenho não consegue distingui-los de interação modelo×critério caso ocorram. L_P também é novo, tornando a interação de P especialmente assimétrica.

   A chave nova inclui modelo, configuração, prompt e bloco — isso está correto — mas o `seed` atribui essa chave a objetos históricos sem verificar versão/configuração de origem. A chave antiga não contém modelo. O recibo agrega versões sem apresentar sua distribuição por célula.

   **Antes da tag:** ou regenerar L_C0/L_C2 contemporaneamente, ou assumir explicitamente um estudo condicionado ao cache histórico, com auditoria de proveniência e uma ponte contemporânea pré-especificada. Reler e rejulgar elimina reutilização dos *desfechos*, mas não das extrações.

   Referências: [PREREGISTRATION.md:70–73](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:70); [e-run.py:78–80](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:78), [182–202](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:182), [408–414](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:408).

3. **[Alta] As 242 instâncias permitem uma extensão pareada, não uma nova confirmação independente do achado original.**

   Reutilizar instâncias não enviesa automaticamente a interação. O problema é condicionar a nova pergunta a uma vantagem já observada e reutilizar as extrações que contribuíram para ela. **Se** a decisão de investigar encolhimento foi motivada por uma realização excepcionalmente favorável a C2, regressão à média pode contribuir para I<0. Os arquivos não permitem quantificar isso nem demonstram seleção indevida.

   O IC cluster-robust não incorpora incerteza de seleção do estudo nem replicação das realizações estocásticas de extração. “A interação nunca foi medida” não torna a amostra intocada.

   **Antes da tag:** registrar a inferência como extensão prospectiva em amostra reutilizada, explicitar a população-alvo e restringir a frase “H_E1 confirmed” ao contraste operacional nesse desenho.

   Referências: [PREREGISTRATION.md:18–22](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:18), [70–82](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:70), [99–104](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:99).

4. **[Alta] A regra principal pode “confirmar encolhimento” porque F piorou C2.**

   Exemplo compatível com os controles: L_C2=0,82, L_C0=0,57; F_C2=0,55, F_C0=0,55. A interação é −25 pp, os pisos passam, mas F não recuperou C0: destruiu a vantagem ao piorar C2. Um controle de remoção também pode passar nesse cenário.

   A regra implementa corretamente a hipótese algébrica; o problema é associá-la à explicação de maior capacidade dispensando regras. Também falta distinguir convergência, reversão da vantagem e compressão por teto da acurácia.

   **Antes da tag:** pré-especificar e reportar F_C0−L_C0 e F_C2−L_C2, com intervalos, e separar o veredito estatístico da interpretação mecanística. Esses contrastes não constam da lista secundária.

   Referências: [PREREGISTRATION.md:77–95](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:77); [e-analyze.py:88–115](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-analyze.py:88).

5. **[Alta] A trava da tag não congela o instrumento completo.**

   `FROZEN` contém apenas `e-run.py`, `e_prompts.py` e `e_batch.py`. Não protege o pré-registro, `e-analyze.py` ou os módulos do Paper 3 carregados do checkout corrente. Importar um arquivo cujo comentário menciona uma tag não equivale a importá-lo daquela tag. Só C2 tem um hash assertado em `e_prompts.py`.

   Portanto, serving, leitor, juízes ou cálculo do IC podem mudar sem impedir a fase paga. O manifesto é verificado; o conteúdo do dataset não recebe proteção equivalente.

   **Antes da tag:** verificar hashes de toda a cadeia executável, análise, protocolo e dados; registrar o commit resolvido da tag no recibo.

   Referências: [e-run.py:50–54](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:50), [104–110](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:104), [127–138](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:127); [e_prompts.py:14–16](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e_prompts.py:14), [29–31](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e_prompts.py:29); [e-analyze.py:28–32](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-analyze.py:28).

6. **[Alta] A análise não exige as 1.492 linhas nem os 40 controles prometidos.**

   Ela aceita quaisquer IDs presentes, intersecta as seis células e usa quantos controles encontrar. Não verifica manifesto, duplicatas, conjunto esperado ou recibo. Instâncias totalmente ausentes nem aparecem na lista de incompletas. Duplicatas sobrescrevem acurácias, mas entram repetidamente nas estatísticas de abstention/comprimento.

   **Verificação sintética:** quatro instâncias completas e apenas um controle produziram `interpret=True` e um veredito de encolhimento. Isso contradiz a promessa de não analisar antes de todas as linhas existirem.

   Exigir P para o contraste C0/C2 também permite que falhas de uma célula secundária selecionem a amostra primária.

   **Antes da tag:** validar exatamente o conjunto esperado de pares `(qid, cell)`, rejeitar duplicatas e fixar uma única política coerente para incompletude.

   Referências: [PREREGISTRATION.md:102–104](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:102), [124–125](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:124); [e-analyze.py:45–61](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-analyze.py:45), [74–86](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-analyze.py:74), [146–152](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-analyze.py:146).

7. **[Alta] Recuperação de falhas e relatório não implementam o protocolo.**

   São três divergências:

   - Resposta batch com JSON inválido é armazenada com `failed=True`; `todo_of` só retorna chaves ausentes. Portanto, essa falha **não recebe tentativa sync**.
   - Exceção de transporte no sync retorna sem cache. A leitura então aborta por ausência, em vez de servir vazio depois da passagem sync.
   - O recibo informa apenas falhas totais; não há contagem por extrator×critério nem aviso automático de >1% junto ao primário.

   Isso deixa tratamento desigual de falhas e pode converter problemas de formato em aparente efeito de critério.

   Referências: [PREREGISTRATION.md:122–133](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:122); [e-run.py:209–210](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:209), [260–264](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:260), [320–335](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:320), [370–373](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:370), [408–412](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:408).

8. **[Alta, operacional] US$160 não é um teto rígido; retomada pode recontar gastos.**

   No sync, as tarefas são enfileiradas no executor e a cobrança ocorre **depois** da chamada. A exceção de limite em um worker não cancela automaticamente as demais tarefas; a saída do executor espera o trabalho pendente. No batch, o limite reserva estimativas, não um máximo de cobrança.

   A ingestão cobra cada linha antes de concluir o chunk. Se interrompida, o chunk continua submetido e pode ser reingerido, cobrando novamente no ledger linhas já contabilizadas. Em sentido oposto, morte abrupta pode perder os gastos desde o último checkpoint. A acumulação é por `--out`, não global.

   **Antes da tag:** parada compartilhada antes de novas chamadas, cancelamento de pendências, contabilização idempotente por requisição e distinção explícita entre teto operacional estimado e cobrança efetiva.

   Referências: [PREREGISTRATION.md:127–129](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:127); [e-run.py:145–178](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:145), [248–307](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:248), [320–335](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:320); [lme-run.py:276–281](/Users/lab/Claude/Projetos/memoria-nox/paper3-construction/lme-run.py:276).

9. **[Média] P é uma comparação legítima de prompts, mas não uma ablação pura de regras.**

   P remove categorias/ignore da instrução inicial e acrescenta informação sobre a tarefa futura. Ao mesmo tempo, conserva as categorias no esquema JSON, a escala, o filtro e o limite de itens. Logo, “só propósito” é uma abreviação: ainda há restrições de seleção e representação.

   O smoke mostra P produzindo 4,30 unidades/bloco contra 2,98 em C2 para F. Não há controle de orçamento de memória; o serving importado concatena todas as unidades. Diferenças podem passar por quantidade, importância atribuída e carga imposta ao leitor. Isso faz parte do efeito total do prompt, mas não isola “deixar o modelo decidir”.

   **Antes da tag:** limitar a conclusão à política completa; se houver intenção mecanística, acrescentar diagnóstico pré-especificado de retenção e orçamento de memória.

   Referências: [e_prompts.py:18–27](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e_prompts.py:18); [PREREGISTRATION.md:50–61](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:50); [SMOKE-RESULT.md:95–99](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/SMOKE-RESULT.md:95); [lme-run.py:472–481](/Users/lab/Claude/Projetos/memoria-nox/paper3-construction/lme-run.py:472).

10. **[Média] Aceitar lista e objeto é justo; o parser não cumpre integralmente seu contrato.**

    A ampliação de formato é razoável e aplicada às novas chamadas dos dois extratores. Contudo, verifiquei que `{}` e `{"memories":false}` são aceitos como sucesso vazio; `importance:true` é retido porque `bool` é subtipo de `int`. Também não há validação de texto ou faixa da importância. Isso mascara falhas de esquema e pode produzir diferenças de retenção entre modelos.

    Os “até 0,06% dos blocos” não limitam a mudança de acurácia a 0,06%: poucos blocos podem conter evidência decisiva ou ser compartilhados por várias perguntas.

    **Antes da tag:** definir esquema válido, distinguir vazio legítimo de formato inválido e retirar qualquer leitura daquela porcentagem como garantia de impacto desprezível nos desfechos.

    Referências: [e_prompts.py:44–67](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e_prompts.py:44); [PREREGISTRATION.md:63–73](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:63); [SMOKE-RESULT.md:50–55](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/SMOKE-RESULT.md:50).

11. **[Média] Os controles não distinguem falha do instrumento de explicações alternativas.**

    Remover sessões de resposta só em F_C2 não verifica leakage nas demais condições nem a sensibilidade do leitor a mudanças factuais. Acertar após remoção pode refletir informação redundante em outras sessões; errar pode refletir simplesmente um pipeline degradado. Não há controle contrafactual de valor, remoção de sessões irrelevantes ou auditoria da evidência residual neste protocolo.

    “Se falha, é falha do instrumento” é mais forte do que o controle permite diagnosticar. O limite de quatro acertos em 40 também é uma regra operacional, não uma demonstração de taxa populacional ≤10%.

    **Antes da tag:** tratar falha como bloqueio conservador de interpretação, sem atribuir sua causa; especificar auditoria e, idealmente, controles correspondentes nos dois extratores.

    Referências: [PREREGISTRATION.md:88–95](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:88); [e-run.py:339–365](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:339); [e-analyze.py:74–101](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-analyze.py:74).

12. **[Média] A potência apresentada não corresponde integralmente ao teste cluster-robust planejado.**

    O cálculo usa variância e 242 instâncias, sem ajuste explícito pela estrutura de clusters. A análise usa componentes de sessões de resposta e quantil normal. Além disso, blocos de outras sessões podem compartilhar uma mesma extração cacheada entre perguntas: o agrupamento atual não cobre necessariamente toda a dependência do pipeline.

    Não demonstrei que os ICs serão estreitos demais; falta nos arquivos a verificação necessária para sustentar sua adequação e os valores de potência.

    **Antes da tag:** reportar número/tamanho dos clusters, avaliar sobreposição de blocos e qualificar os números de potência como aproximações sob as hipóteses declaradas.

    Referências: [PREREGISTRATION.md:99–113](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:99); [e-analyze.py:54–68](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-analyze.py:54); [lme-analyze.py:43–72](/Users/lab/Claude/Projetos/memoria-nox/paper3-construction/lme-analyze.py:43).

13. **[Média] A adoção de batches por nome não identifica univocamente a execução.**

    Os nomes são derivados de prefixos fixos, extrator e índice; não incluem identidade da execução ou hash do conteúdo. Outro `--out`, outro subconjunto pendente ou repetição do `batch-test` pode adotar um batch anterior de mesmo nome. O filtro por chave reduz a possibilidade de misturar respostas erradas, mas não garante completude nem contabilização correta.

    **Antes da tag:** usar identidade persistente da execução e hash do chunk, verificando correspondência antes de adotar.

    Referências: [e-run.py:213–238](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:213), [285–290](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:285), [435–436](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:435), [499](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/e-run.py:499).

O núcleo aproveitável é claro: seis células pareadas, contraste com sinal correto, controle por remoção implementado conforme a seleção de sessões e ausência de alegação de equivalência quando o IC inclui zero. **Eu liberaria a tag após corrigir as garantias de execução e reformular a conclusão como comparação condicionada entre pipelines específicos — mantendo “força do extrator” como explicação a investigar.**
