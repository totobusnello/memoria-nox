# Parecer Codex — revisão adversarial da nota do Paper E (challenge)

receipt: /Users/lab/Claude/logs/adversary-receipts/adversary-receipt-codex-2026-11-08T150117-64583.txt
output_file: /var/folders/jb/zs54jg5x3ng6nyh7w2582jsr0000gn/T/adversary-bg/codex-2026-11-08T150117-64569.out

**Eu pediria revisão antes do depósito.** O resultado primário está corretamente declarado como inconclusivo, e os números estatísticos conferem. O problema é que o resumo e partes do §5 sugerem conclusões mais fortes do que esse resultado permite.

Li integralmente os cinco arquivos solicitados e também a revisão anterior do pré-registro. Abaixo, os caminhos abreviados são relativos a `paper-e-extractor/`. Esta é uma revisão documental; não uma auditoria independente das chamadas à API.

1. **[Alta] “The rules kept most of their value” não foi demonstrado.**

   A frase do resumo converte proximidade das estimativas pontuais em conclusão de preservação: [NOTE.md:23–27](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:23). O IC da interação permite uma redução de **12,3 pp**, além de aumento de **4,1 pp**; não houve margem registrada de equivalência, não inferioridade ou “maior parte preservada”. O próprio pré-registro proíbe ler IC contendo zero como evidência de vantagens iguais: [PREREGISTRATION.md:96–108](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:96).

   A vantagem positiva de C2 **dentro de flash** sustenta uma conclusão distinta: há um contraste secundário favorável a C2 nessa configuração. Não demonstra preservação relativa entre extratores.

   **Exigência:** substituir a frase por algo como: “C2 apresentou vantagem sobre C0 com flash; a mudança dessa vantagem entre os dois extratores permaneceu inconclusiva.”

2. **[Média] “The data rule out a loss of more than about 12 points” precisa de condições explícitas.**

   O limite vem corretamente do IC primário, mas “rule out” no resumo soa absoluto: [NOTE.md:26–27](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:26). Trata-se de exclusão **pelo intervalo nominal de 95% do juiz 1, sob a análise especificada**. O juiz 2 permite redução de **13,4 pp**: [analysis.txt:7–12](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:7).

   A nota menciona uma realização das destilações, mas omite a outra dependência explicitada no protocolo: blocos compartilhados entre históricos não incorporados aos erros-padrão. Compare [NOTE.md:160](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:160) com [PREREGISTRATION.md:162–170](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:162).

   **Exigência:** preferir “o IC primário vai de −12,3 a +4,1 pp” e restaurar as condições inferenciais. Não há base aqui para afirmar que os ICs estão errados; há base para exigir que seus limites sejam apresentados.

3. **[Alta] A decomposição do §5 é aritmeticamente correta, mas não identifica o mecanismo.**

   “Most of the small negative estimate comes from C0” funciona como descrição da **estimativa pontual**: −1,2 − 2,9 ≈ −4,1. O salto ocorre com “flash moved accuracy little” e a sugestão de que um extrator mais forte fez espontaneamente parte do trabalho das regras: [NOTE.md:135–140](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:135).

   Sob o juiz primário:

   - C0: **+2,9 [−3,5; +9,3] pp**;
   - C2: **−1,2 [−6,4; +4,0] pp**.

   Ambos permitem mudanças em direções opostas. “Pouco mudou” não é equivalência. Destacar que o IC do juiz 2 “just excludes 0” seleciona o resultado favorável de uma família secundária **sem correção de multiplicidade**: [analysis.txt:14–16](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:14), [PREREGISTRATION.md:103–109](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:103).

   A ressalva final “which the primary does not establish” ajuda, mas deixa uma narrativa mecanística privilegiada.

   **Exigência:** dizer que a decomposição é pontual, apresentar os dois ICs no parágrafo e tratar ganho de C0, perda de C2 e flutuação amostral como possibilidades não resolvidas.

4. **[Alta] P não é “só propósito”, e “got most of the way to the rules” carece de critério inferencial.**

   O resumo diz que P “only states” a finalidade; a introdução repete “says only”; o §5 atribui o ganho a “stating the purpose”: [NOTE.md:16–17](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:16), [NOTE.md:40–42](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:40), [NOTE.md:142–145](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:142).

   O protocolo explicitamente diz que P **não é ablação pura**: mantém categorias, escala, filtro e teto, remove listas e acrescenta finalidade. O contraste compara políticas completas, incluindo quantidade de memória: [PREREGISTRATION.md:70–84](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:70).

   Além disso, P−C2 com flash é **−3,7 [−9,4; +1,9] pp**. A expressão “came within 3.7 points” descreve apenas a estimativa, não um limite garantido de proximidade. A nota acerta ao negar equivalência, mas deveria dizer que o IC continua compatível com desvantagem de 9,4 pp: [analysis.txt:17](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:17).

   **Exigência:** descrever P como política alternativa completa e limitar a conclusão ao seu contraste observado. Para atribuir o efeito especificamente à finalidade, seriam necessários outros controles, inclusive de orçamento de memória.

5. **[Alta] “Stronger” e “model size” continuam funcionando como explicações estabelecidas.**

   A ressalva de modelos configurados existe em [NOTE.md:150–154](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:150), mas o resumo conclui sobre “this step of model size”, e o §5 retorna a “stronger extractor”: [NOTE.md:26](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:26), [NOTE.md:139](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:139).

   O pré-registro é mais preciso: nada medido estabelece superioridade de extração do flash **com thinking desligado**; os smokes mediram custo e unidades, não qualidade. O estimando compara modelos configurados, sem isolar força: [PREREGISTRATION.md:19–22](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:19), [PREREGISTRATION.md:62–68](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:62).

   **Exigência:** usar “nessas duas configurações” no resumo e restaurar a ausência de validação independente de superioridade. Uma conclusão sobre força exige evidência adicional.

6. **[Média] Reuso e regressão à média estão presentes; “reproduced” precisa carregar essa restrição.**

   Aqui não cabe acusar omissão: [NOTE.md:46–50](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:46) explicita ambos adequadamente. Entretanto, “the earlier +24.8 reproduced” no resumo e “the earlier contrast also reproduced” no §5 podem ser lidos como confirmação independente: [NOTE.md:24](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:24), [NOTE.md:132–133](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:132).

   **Exigência:** escrever “a nova execução nas mesmas perguntas produziu contraste semelhante”. Regenerar memórias, respostas e notas resolve a reutilização de artefatos, mas não torna a amostra nova. Também não se deve afirmar que regressão à média efetivamente causou a interação: o protocolo a apresenta como possibilidade condicional.

7. **[Média] A ressalva sobre a família do leitor foi suavizada.**

   A nota informa a família compartilhada e imediatamente destaca concordância entre juízes: [NOTE.md:155–157](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:155). Falta a consequência expressa no protocolo: o leitor pode favorecer a representação de um extrator, e **trocar a família do juiz não resolve isso**: [PREREGISTRATION.md:222–224](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:222).

   **Exigência:** restaurar essa frase. Dois juízes avaliam respostas produzidas pelo mesmo leitor; não constituem replicação entre leitores.

8. **[Média] A nota não apresenta integralmente o relatório previsto nos §§4 e 6.**

   Há uma diferença importante entre **omissão na nota** e **ausência na análise**:

   | Exigência registrada | Situação na nota | Evidência disponível |
   |---|---|---|
   | Todos os contrastes secundários, com ICs sob ambos os juízes | Falta a interação de P; juiz 2 aparece apenas com estimativas | [NOTE.md:109–119](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:109); [analysis.txt:14–22](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:14) |
   | Falhas e unidades/bloco por extrator × critério | Só total, P/flash-lite e duas médias de C0 aparecem | [analysis.txt:24–30](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:24) |
   | Acurácia, abstenção e comprimento por célula; acurácia por tipo | Faltam abstenção e resultados por tipo | [NOTE.md:121–126](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:121); [analysis.txt:32–49](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:32) |

   As obrigações estão em [PREREGISTRATION.md:108–115](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:108) e [PREREGISTRATION.md:138–142](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:138).

   A interação omitida de P é **+4,1 [−4,3; +12,6] pp**, juiz 1, e **+0,8 [−7,0; +8,7] pp**, juiz 2. Sua ausência importa porque a narrativa destaca a aparente melhora relativa de P com flash.

   **Exigência:** incluir os resultados ou um suplemento explicitamente incorporado à nota, além de declarar “secundários, sem testes reivindicados e sem correção de multiplicidade”. Os arquivos de análise cumprem essas partes; não classificaria isso como análise registrada não executada.

9. **[Média] Os controles passaram, mas sua abrangência foi encurtada.**

   Valores, limiares e decisão estão corretos: [NOTE.md:95–97](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:95), [analysis.txt:3–5](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:3).

   Falta informar que a remoção é um critério operacional em 40 instâncias, não estima taxa populacional, não testa vazamento nas outras células e não verifica sensibilidade a fatos alterados: [PREREGISTRATION.md:119–127](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:119).

   **Exigência:** restaurar esses limites. “Both controls passed” autoriza interpretar o primário pela regra registrada; não valida todas as explicações posteriores.

10. **[Baixa] A cronologia e a prestação de custos precisam de precisão.**

   “Frozen before any paid call” omite “of this run”: [NOTE.md:18–19](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:18). Houve **US$ 2,10 antes da tag**, explicitamente registrados: [PREREGISTRATION.md:207–216](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:207). `RESULT.md` usa corretamente “before any paid call of the run”: [RESULT.md:3–4](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/RESULT.md:3).

   O protocolo também exige reportar estimativa do ledger **e fatura real**, enquanto nota e resultado apresentam apenas custo a preço de tabela: [PREREGISTRATION.md:195–200](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:195), [NOTE.md:90](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:90), [RESULT.md:17](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/RESULT.md:17).

   **Exigência:** corrigir a cronologia e fornecer a reconciliação financeira, ou declarar explicitamente sua indisponibilidade.

**Conferência numérica — item (c).** Não encontrei divergência nos valores publicados de interação, contrastes, ICs, acurácias, medianas, unidades/bloco citadas, controles ou potência. Em particular:

- As tabelas de [NOTE.md:103–126](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/NOTE.md:103) conferem com [analysis.txt:8–38](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/runs/confirm-2026-11-08/analysis.txt:8).
- A potência de 9,4–12,2 pp confere com [PREREGISTRATION.md:146–156](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PREREGISTRATION.md:146).
- O custo de US$ 150,55 corresponde ao arredondamento de 150,5455 documentado em [PROVENANCE.json:107–113](/Users/lab/Claude/Projetos/memoria-nox/paper-e-extractor/PROVENANCE.json:107).

A divergência factual identificada é a abrangência temporal de “any paid call”, acima. As demais objeções são de inferência, completude ou enquadramento — não números trocados.

**Para aceitar o resumo**, exigiria corrigir os achados de alta severidade e incorporar as ressalvas e resultados omitidos. Não exigiria nova corrida para publicar uma extensão descritiva cuidadosamente delimitada. Exigiria evidência adicional para manter conclusões sobre força, mecanismo, equivalência ou preservação da maior parte da vantagem.

Uma conclusão defensável seria:

> Nesta extensão pareada nas mesmas 242 perguntas, a interação entre critério e configuração do extrator foi −4,1 pp (IC95% −12,3 a +4,1), inconclusiva. O contraste secundário C2−C0 com flash foi +21,1 pp (+14,8 a +27,4). P−C2 com flash foi −3,7 pp (−9,4 a +1,9), sem estabelecer equivalência. Os resultados comparam políticas completas nessas configurações e sob um único leitor; não isolam força do extrator.
