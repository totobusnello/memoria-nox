# Congelamento do corpus de ações — 2026-07-29T09:46:09Z

> Fecha o item aberto declarado em `CALIBRATION-SEED.md`: *"declarar a seed não
> basta — a seed ordena um conjunto, e o conjunto se move."* Este documento
> congela o conjunto.

---

## O problema que isto resolve

O corpus de episódios é derivado de um arquivo vivo que cresce **~330 episódios
por dia**. Entre o pré-registro (2026-07-26) e a amostragem (2026-07-29) ele foi
de 4.560 para 5.547 episódios, e a taxonomia derivada do `sig()` foi junto:
**72 → 74** assinaturas primary, **162 → 168** fine. Um número publicado sobre
esse corpus expira sozinho entre a escrita e a submissão.

A seed do beacon torna a **amostragem** reprodutível. Sem congelar o conjunto
amostrado, ela ordena algo que já não existe.

## O que está congelado

| Artefato | SHA-256 |
|---|---|
| **Snapshot** `action-archive-20260729T094609Z.tar.gz` (107 MB) | `ba5fcc81f43cede6e40572236be984bc0cc5e450325b115e2b994f5a24cdf382` |
| **Manifesto** `corpus-manifest-20260729T094609Z.txt` (3.860 linhas) | `2fe8ba2b6a545a84c3a3ee09efe061126c74ee93c5d458eb3209076ade6c5638` |
| `extract_episodes.py` — implementação canônica do `sig()` | `e860357bd9f1fc0690ec8a817b7f6d23ac0c237882152d3a8714f7c0af7748b2` |
| `adjudication_prompt.md` (arquivo) | `3767fdb50e31ce41e3de8484501c056a48ccdfa3cc3e283f59e64a8d2c339bd7` |
| **Prompt enviado** aos painelistas (corpo extraído) | `5b22f02c1a557417fe874b98cdf8a3ad6441cada74d69ace8e54f82b3438b03e` |
| Commit que congela o `sig()` | `c0abe143df1ab6452cf83556b2bc442ec87319a0` (2026-07-26T16:27:28-03:00) |

⚠️ Os dois hashes do prompt **não são o mesmo objeto** e ambos importam:
`carregar_prompt()` extrai apenas o corpo entre o cabeçalho e o primeiro
comentário HTML, e é esse corpo que vai para os painelistas. O hash do arquivo
versiona o artefato; o do corpo versiona o que foi de fato enviado.

**Estado do corpus no congelamento:** 3.860 arquivos `.jsonl`, 409 MB não
comprimidos, distribuídos em 9 diretórios de agente.

## Como um terceiro verifica

O manifesto está **neste repositório** justamente para que a verificação não
exija baixar 107 MB. Ele lista o SHA-256 de cada um dos 3.860 arquivos:

```bash
# a partir do snapshot
tar xzf action-archive-20260729T094609Z.tar.gz
sha256sum -c corpus-manifest-20260729T094609Z.txt      # 3.860 OK esperados

# e o snapshot contra si mesmo
sha256sum action-archive-20260729T094609Z.tar.gz
```

O snapshot fica em `/var/backups/nox-mem/paper2-corpus/` com modo `0400`
(somente leitura, mesmo para o dono) e não é coberto por rotação automática.

## O que este congelamento NÃO resolve

1. **Não congela retroativamente.** Os números do pré-registro escritos em 26/07
   (4.560 episódios, 72/162 assinaturas) descrevem um corpus que já não existe.
   Quem reproduzir a partir deste snapshot obtém **5.547 episódios e 74/168
   assinaturas**, e essa divergência é esperada, não erro. Os números do §4.1
   foram atualizados para os deste snapshot.
2. **Não torna o arquivo imutável na origem.** `/var/lib/nox-mem/action-archive`
   continua crescendo. Congelamentos futuros precisam de novo snapshot e novo
   hash — este documento é datado de propósito.
3. ~~**Não resolve a procedência dos episódios `-tmp`.**~~ ✅ **VERIFICADO E FECHADO
   em 2026-07-29.** Os 1.615 arquivos (41,8%) sob `-tmp` **não contribuem episódio
   algum**: uma varredura de 400 deles encontrou **zero `tool_use`**. São sessões
   de compressão de memória (`queue-operation`, prompt de *"maximum non-destructive
   compression"*), sem ação executada.

   Duas hipóteses foram testadas e refutadas. **(a) Contaminação pelo painel:** o
   `run_panel.py` invoca os CLIs com `cwd="/tmp"`, e ~1.700 chamadas contra 1.615
   arquivos é uma coincidência que pedia verificação. Refutada pela distribuição
   temporal — os `-tmp` são uniformes em **~145/dia desde 18/07**, não concentrados
   em 28/07 quando o painel rodou. **(b) Problema de construto:** não existe, porque
   arquivo sem `tool_use` não vira episódio. O corpus de 5.547 episódios vem
   inteiramente dos nove diretórios nomeados de agente.

   O que fica: a contagem de **arquivos** do snapshot (3.860) supera em muito a de
   arquivos que **produzem episódios**. Os dois números medem coisas diferentes e
   não devem ser citados um pelo outro.

## Procedência

O arquivo é alimentado por `nox-archive-transcripts.sh` (cron `40 3,9,15,21`),
que espelha `/root/.claude/projects/` com `rsync` **sem** `--delete` — é por isso
que ele preserva episódios que o `prune-claude-sessions.sh` das 04:23 apaga da
origem. Em 27/07 esse mecanismo resgatou 311 arquivos que hoje só existem no
arquivo. O snapshot acima herda essa propriedade.
