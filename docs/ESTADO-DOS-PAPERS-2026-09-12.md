# Estado dos papers — 2026-09-12, 18h BRT

> **Para quem retoma.** Este arquivo é o mapa de *onde cada frente está e de quem é a
> bola*. Ele nasceu porque o mesmo rótulo — «Paper 0», «Paper 1», «Paper 2», «P2», «P4»,
> «B1» — designa **objetos diferentes** em três lugares: na fala do Toto, no repo
> `7_problems` e no repo `memoria-nox`. Essa colisão já custou três erros de atribuição
> documentados. Aqui os papers são nomeados **pelo objeto**, e a numeração vira tabela de
> tradução, não identidade.
>
> Fontes canônicas de cada frente ficam nomeadas em cada seção. Onde este arquivo e uma
> fonte discordarem, **a fonte ganha** — e a divergência é defeito a corrigir, não nuance.

---

## 1. A tabela de tradução

| como o Toto chama (12-09) | nome canônico | onde vive | o objeto |
|---|---|---|---|
| **paper 0** | «o paper do nox-mem» | `memoria-nox/paper/` | *nox-mem: Pain-Weighted Hybrid Memory for LLM Agents* |
| **paper 1** | **Paper 0** | `7_problems` | base-dependência do Unit Gap; refuta Thm 2 e Cor. 6 |
| **paper 2** | **P1** | `7_problems` | forced multiple reconvergence — **joint** com o Krinkin |
| **B1** | **B1** | `7_problems` | auditoria da database do Simplifier (SPbSAT) |
| **P2+P4** | **P2** | outline em `memoria-nox`, fila em `7_problems` | metodologia + *honesty-engineering* |
| *(sem rótulo na fala)* | **Paper 2 / Interventional** | `memoria-nox/paper2-interventional/` | memória interventiva — ensaio em curso na VPS |
| **stanford** | Stanford / Omri | `memoria-nox/docs/STANFORD-OUTREACH.md` | colaboração a definir |

🔴 **As três colisões que causam erro:**

1. **«Paper 0»** é o nox-mem na fala do Toto e é o **Unit Gap** no `7_problems`. Os dois
   têm histórico de arXiv, e é exatamente aí que a troca acontece — a recusa
   `submit/7771319` foi atribuída ao Unit Gap por quatro dias;
2. **«Paper 2»** é o *joint* com o Krinkin na fala do Toto e é o **Interventional
   Memory** em todos os registros do `memoria-nox`, inclusive nesta memória. Objetos sem
   relação nenhuma;
3. **«P2» e «P4»** são itens da fila de papers no `7_problems` **e** features do produto
   nox-mem no `docs/ROADMAP.md` (`P2` = auto-capture por hooks, `P4` = `nox-mem connect
   <ide>`). E «B1» é ainda um **teste** de guarda no `docs/HANDOFF.md`.

⇒ **Regra:** em prosa, nomear o objeto («o paper do nox-mem», «o do Unit Gap», «o joint
com o Krinkin»). O número só aparece acompanhado do repo.

---

## 2. As sete frentes, com a bola e o bloqueio

### 2.1 O paper do nox-mem — negado no arXiv, rota TMLR travada na conta

| item | estado |
|---|---|
| arXiv | ❌ **recusado 2026-09-03 16:09Z**, `MOD-103264`, submissão `submit/7771319`. Template genérico, **sem feedback item-a-item** |
| DOI | ✅ `10.5281/zenodo.22649269` |
| pacote TMLR | ✅ **pronto**: `paper/build/tmlr/tmlr.pdf`, **48 páginas**, 316.443 B, sha256 `68d88cfda67c308d…`; suplemento 63.287 B; gate de anonimato verde com controle positivo (8/8 padrões acusados na sentinela, 0 vazamentos no build limpo) |
| régua | **25.671 palavras · 55 obras · 2,14/mil · 1,49×** o maior aceito ⇒ densidade **dentro** da faixa dos aceitos (2,06–2,95) |
| 🔴 bloqueio | **conta OpenReview em moderação** — perfil `~Luiz_Antonio_Busnello1` |
| bola | **do OpenReview.** Depois dela, a submissão é do Toto |

**Sobre a régua:** medida em 12-09 ~18h com `paper/publication/scripts/reconta-regua-nosso-lado.py`,
controle positivo passando (`fa3d28e` devolve 24.111 vs 24.126 publicadas, delta −15).
⚠️ Uma medição de **mais cedo no mesmo dia** deu 27.489 palavras / 57 obras / 1,59×: era
**anterior ao #538**, que recontou o `paper/bibitem-census.json`. Não são duas verdades —
é um número velho. **Nunca citar estes três de memória; o instrumento sai `!=0` quando
não reproduz.**

**A apelação no arXiv é ativo de uso único e AINDA NÃO foi gasta.** A política diz *"When
an appeal is denied by appellate moderators, no further appeal is possible."* E a própria
recusa diz que reconsideram *"via appeal **if it is published in a conventional journal**
and you can provide a resolving DOI"*. Dos 6 precedentes levantados, **zero venceram sem
peer review**; a única vitória documentada (Abel C. H. Chen) veio **depois** de DOI de
conferência IEEE. ⇒ apelar antes de uma aceitação gasta o ativo no modo com 0/6.
Detalhe em `paper/publication/apelacao/00-ESTADO-2026-09-11.md`.

⚠️ **Aquele arquivo se intitula «Apelação do Paper 1»** e trata do paper do **nox-mem** —
é a colisão nº 1 em ação, dentro do nome do próprio arquivo.

### 2.2 O paper do Unit Gap (`7_problems` «Paper 0») — sob moderação, é o mais adiantado

- **submetido ao arXiv em 05-08**; 🟡 **sob moderação**, 38 dias em 12-09, confirmado pelo
  Luiz em 11-09. **Não houve recusa** — a que existia era do nox-mem;
- decisão aberta, do Toto: **journal e enquadramento** (`PLANO.md` item 1.8). O paper hoje
  se apresenta como refutação de um preprint que o autor **já retirou** (withdrawal v4 do
  `2603.08033`) — o argumento mais fraco que tem. O que um editor avalia é a
  **base-dependência** (gap 6 em AIG a `n=4`, ≤1 em XAG). Reenquadrar é redação, não
  pesquisa;
- bola: **do arXiv** para a moderação; **do Toto** para o venue.

### 2.3 O joint com o Krinkin (`7_problems` «P1») — pronto, bola dele

- **PRONTO**: 12 seções, **92 páginas**, 8 arquivos Lean sem `sorry`, gates verdes. Falta
  **leitura humana** do Toto;
- **a bola é do Krinkin desde 12-09 00h02 BRT** — resposta enviada com o PDF atual
  anexado; a cópia que ele tinha era de 01-09 e estava 541 inserções atrás;
- ele **já aceitou o paper conjunto 3×** (14-08, 31-08, 02-09): falta a **forma**, não o
  aceite;
- ⚠️ ponto aberto medido: `min_reconv(XOR_5) ∈ {2,3}` e **não fecha** — `r=3` SAT em três
  corridas, `r=2` **timeout** a 21.600 s de um cap de 6 h. **Timeout não é veredicto.** A
  rota para fechar é estrutural (Corolário 4), e não começou.

### 2.4 B1 — auditoria do Simplifier, condicionada ao Sasha

- material **pronto e reproduzível**: 614.187 entradas processadas, 587.801 ótimas,
  **10.449 melhoradas** (11.447 AND gates poupados), verificador independente
  10.449/10.449;
- ✅ **depositado e publicado no Zenodo**: versão `10.5281/zenodo.22726276`, concept
  `10.5281/zenodo.22725275`; ORCID no registro;
- ✅ e-mail ao **Sasha** (Alexander S. Kulikov, SPbSAT) **enviado** com o DOI;
- 🔴 **não falta pesquisa, falta saber que paper é.** Três desfechos dão três papers
  diferentes: (a) incorporam e creditam → nota curta ou nada; (b) propõem trabalho
  conjunto → coautoria e outro escopo; (c) silêncio → paper nosso, independente;
- bola: **do Sasha**. É o bloqueio mais caro da fila do `7_problems`.

### 2.5 P2 — metodologia + honesty-engineering

- ⚑ **P4 foi FUNDIDO no P2 em 12-09, decisão do Luiz.** Nunca foi paper separado: é a
  **contribuição nº 2** do outline do P2, «the honesty-engineering story». Público:
  **AI4Math**;
- estado: **PERTO** — outline escrito, vive no `memoria-nox`;
- bola: **do Toto**, é decisão de prioridade.

### 2.6 Interventional Memory (`memoria-nox` «Paper 2») — ensaio em curso, não tocar

- pré-registro: OSF **`yf7d2`** · Zenodo v1.12 `10.5281/zenodo.22110203` (arquivos
  **imutáveis**; a contribuição é o **método**);
- 🔒 **o ensaio encerra 2026-09-20 22:51:23Z** e a dose desliga **2026-09-21 09:43Z**. Os
  19 designados **expiram todos juntos** em 20-09 22:51:23Z;
- **análise só depois do fecho.** PR **#452 segurado** até lá — ele muda a política de
  restart da VPS que roda o ensaio;
- ⛔ **a VPS de produção não hospeda nenhuma stack de benchmark antes de 21-09 09:43Z**;
- bola: **do calendário**.

### 2.7 Stanford — esperando resposta

- alvo: **Omri** et al., `arXiv:2606.06448`, correspondência em Stanford; e o survey TMLR
  `2602.06052v4` (James Zou, Wanjia Zhao), cuja §9.6 nomeia como direção aberta justamente
  o desenho que o Interventional pré-registra;
- mensagem **redigida** (`docs/STANFORD-OUTREACH.md`), aproximação **data-gated**, não
  date-gated;
- decisão registrada: **quando ele responder, fazemos um DOI**;
- bola: **do Omri**. Desfecho em aberto — colaboração ou paper próprio.

---

## 3. O ruído a limpar — cada peça com o conserto

| # | ruído | onde | conserto | de quem |
|---|---|---|---|---|
| R1 | 🔴 o branch `docs/krinkin-resposta-11-09` está **1 commit atrás da main** e sua cópia do `PLANO.md` ainda diz «Paper 0 ❌ rejeitado pelo arXiv em 11-09» | `7_problems` | **rebase/merge da main antes de integrar**, senão o merge **reintroduz** a falsidade corrigida hoje | sessão par / Toto |
| R2 | `PLANO.md` lista **P4 como paper separado** e **P2 como «não é paper autônomo»** | `7_problems` main, tabela de papers | alinhar à fila de 12-09: **P4 fundido no P2**, e o P2 **é** paper | precisa do ok do Toto (`7_problems` é read-only para mim) |
| R3 | o arquivo da apelação se chama «**Apelação do Paper 1**» e trata do **nox-mem** | `memoria-nox/paper/publication/apelacao/` | renomear, ou cabeçalho declarando o objeto | meu, com ok |
| R4 | `docs/ROADMAP.md` §8/§12 e `docs/VISION.md` v16 registram «**apelar primeiro, não submeter ao TMLR**» — decisão **invertida em 12-09** | `memoria-nox` | atualizar as duas | meu |
| R5 | memórias nomeadas `project_paper1_*` designam o paper do **nox-mem** | memória | já anotado; renomear na próxima escrita de cada uma | meu |
| R6 | `STATUS.md` diz «92 páginas» em duas células: uma descreve o **estado atual** (o build diz **94**) e está errada, a outra descreve o **envio de 01-09** e está certa | `7_problems` | edição **contextual**, nunca `sed` global | precisa do ok; arquivo em edição por sessão par |

---

## 4. O que está executável agora, sem decisão nova

1. **encurtar o §7** do paper do nox-mem: 1.866 → ~1.200 palavras, e podar prosa
   redundante em §5/§6. Ataca o único número que ainda incomoda (1,49× o maior aceito) sem
   tocar em resultado. ⚠️ O TMLR **não tem limite de páginas**, mas avisa que *"papers that
   are unusually long … are likely to result in reviewing delays"*;
2. **escrever o texto dos campos do formulário TMLR** (abstract, keywords, declaração de
   código/dados), para colar no dia em que a conta abrir;
3. **R4** — corrigir ROADMAP/VISION, que hoje dizem o contrário da decisão vigente.

Tudo o mais na lista espera **terceiros** (OpenReview, arXiv, Sasha, Krinkin, Omri) ou o
**calendário** (20-09).
