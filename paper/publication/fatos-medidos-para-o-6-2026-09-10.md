# Fatos medidos que entram no §6 quando as colunas fecharem

> Registro de 2026-09-10. **Nada aqui está no manuscrito ainda** — os números de qualidade
> (nDCG@10) não existem no momento da escrita. Este arquivo evita que os fatos operacionais
> se perdam entre a medição e a redação, que aqui são feitas por sessões diferentes.
>
> Medições da sessão par (domínio: adapters, harness, corridas). Redação minha (domínio:
> manuscrito). Fronteira acordada e registrada.

---

## 1. Zep — coluna PRESENTE, e o gatilho do §6.9

⚠️ **Quando o nDCG do Zep chegar, o §6.9 muda:** o parágrafo que diz *"três de cinco
competidores não produziram número"* passa a **dois**, e a nota de escopo datada inserida no
#510 sai. O Zep deixa a lista de non-runs. **Não fazer essa edição antes de o número
existir** — a nota atual já antecipa a transição e é verdadeira enquanto isso.

### Fan-out por sessão — o custo é da arquitetura de sessões, não do corpus

A busca do adapter varre **510 sessões por query**. Varredura de
`NOX_ZEP_SEARCH_WORKERS` medida 2026-09-10:

| workers | mediana por query |
|---:|---|
| 16 | 11,92 s |
| 48 | 4,16 s |
| **96** | **3,39 s** ← ótimo |
| 192 | 10,86 s **com falhas `[Errno 9] Bad file descriptor` e perda de sessões** |

Acima de 96 o servidor degrada **e perde sessões** — a curva não é monotônica, e o ponto de
inflexão é do pool do servidor, não do cliente.

🔴 **NÃO citar hora de parede no §6 por agora — o número move entre medições.**

| medição | queries/min | extrapolação | condição |
|---|---:|---|---|
| varredura (isolada) | ~17 | 2,34 h | máquina livre |
| log do Zep, ~19:50Z | 12,0 | 3,4 h | com a ingestão do EverOS a correr |
| **container, janela de 60 s, ~20:10Z** | **10,1** | **4,1 h** | 5.130 buscas/min ÷ 510 sessões; 0 erros, todas `200`, 272–370 ms por sessão |

Três medições, três números, e **não se sabe** se a diferença é contenção com a ingestão do
EverOS ou variação da carga. ⇒ A única duração publicável é a **real medida no `fecho` do
artefato**, quando existir. Até lá, o que está firme é a **varredura de workers**, que foi
medida em condição controlada — essa sim entra no §6.3.1.

⚠️ Isto substitui uma versão anterior deste arquivo que dizia *"se o §6 citar tempo, citar
3,4 h"*. Instrução retirada: era número de uma medição intermediária carregando ordem de
publicar.

### O caminho de embedding local existe — e nós o removemos por escolha

`eval/q4-comparison/compose/docker-compose.yml` **linha 25**, comentário literal:
*"ZEP_NLP_SERVER_URL removed — no NLP server in this stack."* Não há bloco `NLP` no
`zep-config.yaml`.

O Zep 0.27.2 **tem** embedding local (`Service: local` → `POST
{NLP.ServerURL}/embeddings/{message,document}`, container `zep-nlp`, sem chave — ver
`[^zep-stack]`). Este stack removeu-o para embedar com `text-embedding-3-small` a 1536d e
ficar comparável às outras colunas.

⇒ **A dependência de provedor pago na nossa medição do Zep é decisão nossa de
comparabilidade, não restrição do Zep.** Isso tem de ser dito na coluna, e move a tabela de
autonomia **em favor dele**.

## 2. Retenção por adapter — o confound (e) está incompleto

O §6.3.2 declara (e) com dois operandos. Faltam dois:

| coluna | retenção | estado |
|---|---:|---|
| nox-mem (rc4) | 6.822 | ✅ medido (`INSERT OR IGNORE`) |
| mem0 (rc4) | 6.830 | ✅ medido |
| Zep | 6.830 | ✅ medido (`COUNT(*) FROM message`) |
| **EverOS** | **?** | ⏳ o caso ainda não foi alcançado |

Os 8 ids ambíguos são todos do **LongMemEval**, que entra depois dos 5.882 do LoCoMo — na
ingestão em curso o par colidido ainda não chegou. `COUNT(*) == COUNT(DISTINCT doc_id)` hoje
é **consistente com as duas hipóteses**, logo não decide nada. Se o EverOS sobrescrever por
`doc_id` retém 6.822; se criar linha nova, 6.830.

### Piso de integridade de varredura — `ZEP_MAX_ERRO_SESSAO=0.01`

Instalado 2026-09-10: se **mais de 1%** das 510 sessões falhar a varredura, a corrida
**aborta** em vez de devolver nDCG.

A razão é a que interessa ao §6: uma query respondida a partir de 480 das 510 sessões tem
menos recall **por falha de varredura**, não por qualidade de retrieval — e sairia publicada
como qualidade do Zep. É a mesma classe do `0 hits` por espera não cumprida: nulo fabricado
por artefato de medição, indistinguível de resultado. ⇒ A coluna do Zep tem um **piso de
integridade declarado**, e isso vale uma frase no §6.3.1.

## 3. Referências que as colunas trazem

| referência | localizador | estado |
|---|---|---|
| Qwen3 Embedding/Reranker | `arXiv:2506.05176` | ✅ **já no manuscrito** como `[^qwen3embed]` (§7.2 F5) |
| EverOS / EverMemOS | `arXiv:2601.02163` | ✅ já em `[^everos]` |
| Zep | `arXiv:2501.13956` | ✅ já em `[^zep]` |
| `text-embedding-3-small` | doc da OpenAI | ❌ não é paper, não conta |
| `gemini-embedding-001` | relatório técnico | ⏳ não confirmado |

⇒ **As três com localizador já entraram.** O ganho de densidade das colunas novas é ~0, e
isso é bom saber antes de contar com ele: as ~22 referências que faltam **não** vêm daqui.

## 4. Forma do bloco do §6 — acordada

Duas peças, para que um corte futuro não obrigue a reescrever a medição:

- **(a)** tabela + recibo + número, autossuficientes, com `corpus_sha256`, contagens e
  versões **dentro**;
- **(b)** prosa explicativa em bloco contíguo, migrável para suplemento **sem levar número
  nenhum**.

Nenhum número embutido em frase de prosa. Foi o que fez o §5.5 custar caro no #508.

## 5. Hash do corpus — um só, construção declarada

```
corpus_sha256 = d150c703e3dd2d39ee067d6ad3b7c87f34447b86972758fb72b3a23618e32908
```

SHA-256 sobre a **concatenação dos bytes** de `cache/locomo.jsonl` e
`cache/longmemeval.jsonl`, nessa ordem (lexicográfica de caminho). 6.830 linhas,
14.139.763 caracteres. Os recibos do EverOS e do Zep carregam este campo com esta
construção, igualdade verificada.

## 6. Diferenças de pipeline a declarar ao lado dos números

1. **Espera de embedding do Zep é assíncrona.** O preflight espera 15 s. Sem espera, `0
   hits` mede a espera e não a busca — nulo fabricado por artefato de medição, do tipo que
   se publica sem perceber. ⚠️ A espera do adapter era **inerte** até 2026-09-10 (comparava
   total global de vetores contra o incremento da chamada e imprimia `embeddings ready:
   170/1`); consertada em `f318b88`.
2. **Fan-out por sessão** (Zep): custo e latência da busca crescem com o número de `conv_id`,
   não de documentos. 510 sessões.
3. **Assimetria do reranker** (EverOS): declarar ao lado da anterior — as duas são diferença
   de **pipeline**, não de qualidade.
4. **Suíte do Zep com 11 de 23 casos a falhar**, pré-existentes, por injeção de módulo que
   não alcança imports tardios. A evidência da coluna é o **preflight e a corrida**, não a
   suíte — e isso tem de estar escrito, porque um leitor que abra o repo e rode `pytest` acha
   vermelho, e vermelho não explicado lê-se como resultado inválido. Mesma razão que obrigou
   a disclosar o `output/zep.json` no §6.3.1.
