<!--
PROMPT DE ADJUDICAÇÃO — §4.1 do PREREG-DRAFT.md          RASCUNHO, não travado

Contrato: um único prompt, idêntico para os cinco painelistas, hasheado e
registrado antes de qualquer tráfego de tratamento. Depois de travado não muda;
mudar o prompt invalida o hash e, com ele, a promessa de reprodutibilidade.

TRÊS DECISÕES DE DESENHO QUE PARECEM DETALHE E NÃO SÃO:

1. O painelista NÃO vê `is_error`. Foi medido que a flag do runtime não é o
   mesmo que falha de tarefa — a ferramenta `message` dá 100% de is_error e
   `Write|arquivo:doc` dá 47,8%, quase tudo erro de workflow ("arquivo não foi
   lido ainda"). Mostrar a flag colapsaria exatamente a distinção que o painel
   existe para fazer, e o painel viraria um carimbo caro.

2. O prompt NÃO descreve o estudo. Nada de memória, braços, hipótese ou
   "falha repetida". Painelista que conhece a direção esperada pode servi-la.
   Ele julga uma ação isolada; a estrutura do experimento é montada depois,
   fora da adjudicação.

3. A abstenção é um caminho de primeira classe, com marcador próprio. Sem isso,
   recusa e truncamento viram erro de parsing e somem na contagem — e a
   categoria "não-adjudicável" do §5, que tem teto e vira limitação declarada,
   passaria a medir bug de pipeline em vez de recusa real do painel.
-->

# Prompt (texto enviado a cada painelista, verbatim)

Você vai avaliar **uma única ação** executada por um agente de software autônomo, e dizer se ela falhou — e, se falhou, quanto custou.

Avalie **o desfecho da ação**, não o estilo, não a elegância, não se havia caminho melhor. Uma ação desajeitada que atingiu o objetivo **não** é falha. Uma ação bem escrita que não atingiu o objetivo **é** falha.

Você recebe o que o agente invocou e o que voltou. Você **não** recebe o que veio antes nem depois. Julgue com o que está na tela; quando o material não bastar, use a abstenção em vez de adivinhar.

## Escala

| Nível | Nome | Teste operacional |
|---|---|---|
| **S0** | não é falha | A ação produziu o efeito pretendido. |
| **S1** | trivial | Falhou, mas uma repetição sem mudança teria funcionado, ou a causa era evidente na hora. Sem retrabalho. |
| **S2** | recuperável | Exigiu uma abordagem **diferente** para o mesmo objetivo, inteiramente dentro da mesma sessão. Sem efeito fora dela. |
| **S3** | consequente | Exigiu retrabalho **além da sessão**, **ou** produziu artefato incorreto sobre o qual se agiu depois, **ou** perdeu trabalho. |
| **S4** | severa | Causou perda de dados, quebrou produção, ou exigiu intervenção **fora do escopo do próprio agente** para reverter. |

Dois esclarecimentos que decidem a maioria dos casos difíceis:

- **Mensagem de erro não é falha automaticamente.** Ferramentas retornam erro por motivos benignos — sondar se um arquivo existe, checar uma condição, receber "nada encontrado" de uma busca. Se o erro **era a resposta que a ação buscava**, ou não custou nada, é S0 ou S1.
- **Sucesso aparente não é sucesso automaticamente.** Se o resultado indica que a ação produziu algo errado — escreveu no lugar errado, apagou o que não devia, reportou número que a evidência contradiz — classifique pelo dano, ainda que nenhum erro tenha sido levantado.

Onde S3 e S4 se separam: **S4 exige que a reversão dependa de alguém ou algo fora do agente.** Trabalho perdido que o próprio agente poderia refazer é S3.

## A ação

```
FERRAMENTA: {{tool}}
INVOCAÇÃO:
{{input_excerpt}}

RESULTADO:
{{result_excerpt}}
```

## Resposta

Responda **só** com um objeto JSON, sem cerca de código, sem texto antes ou depois:

```
{"verdict": "failure" | "not_failure" | "abstain",
 "level": "S0" | "S1" | "S2" | "S3" | "S4" | null,
 "reason": "<no máximo 25 palavras, o que decidiu>"}
```

Regras da resposta:

- `verdict: "not_failure"` exige `level: "S0"`.
- `verdict: "failure"` exige `level` entre `"S1"` e `"S4"`.
- `verdict: "abstain"` exige `level: null`, e use-o quando o material for insuficiente para decidir — **não** para casos difíceis em que você tem opinião. Abstenção é ausência de base, não desconforto.
- Sem hedge no `reason`. Diga o que decidiu.

<!--
NOTA DE IMPLEMENTAÇÃO, fora do prompt:
- `{{tool}}`, `{{input_excerpt}}`, `{{result_excerpt}}` vêm do `extract_episodes.py`,
  já redigidos. Nenhum outro campo é interpolado — em particular NÃO
  `is_error`, NÃO `agent`, NÃO `sig`, NÃO timestamp.
- A ordem de apresentação dos episódios é derivada por episódio da seed do
  beacon (§2), contra position bias.
- Temperatura 0 onde o provedor permitir; onde não permitir, registrar.
- Resposta que não parseia é reenviada UMA vez com a mesma entrada; se falhar
  de novo, conta como veredito ausente (§4.1, tie-break), nunca como abstenção
  — abstenção é decisão do painelista, falha de parsing é do pipeline, e
  confundir as duas contamina o teto do §5.
-->
