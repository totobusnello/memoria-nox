# Submit-Day Runbook — arXiv Submission 2026-06-02
# NOX-Supermem: "The Pain Diary and Shadow Discipline"

> Audience: Toto, solo, possivelmente estressado. Sem memória de decisões anteriores necessária.
> Submit deadline: 14:00 ET = 17:00 BRT (encerramento da janela de mesmo dia).
> Se você submeter antes de 14:30 BRT: paper vai ao ar esta noite ~21:00 BRT.
> Se submeter depois das 14:30 BRT: paper vai ao ar no próximo dia útil.

---

## RESUMO RÁPIDO (leia isso primeiro)

1. Rode o pre-flight às ~09:00 BRT
2. Faça login no arXiv e confirme endorsement
3. Gere o tarball
4. Preencha o formulário arXiv
5. Submit antes das 14:30 BRT
6. Atualize CITATION.cff com o ID real

Cada seção abaixo é ~5 minutos. Você tem ~35 minutos de buffer até 14:30 BRT se começar às 09:00 BRT.

---

## §1 — Pre-flight Check (T-30 min | ~09:00 BRT)

### 1.1 Rode o smoke test

```bash
bash paper/publication/scripts/pre-flight-smoke-tests.sh
```

- Se qualquer item retornar **FAIL**: **STOP. Corrija. Re-rode o script antes de continuar.**
- Se todos retornarem **PASS**: continue para §1.2.

### 1.2 Verifique BEIR Table 8

- **VERIFY:** A integração do BEIR (TREC-COVID) deve ter rodado antes deste dia.
- Abra `paper/latex/main.tex` e localize Table 8 (BEIR section).
- Confirme que a linha TREC-COVID está preenchida (não `[PENDING]` ou vazia).
- Se estiver vazia: **STOP.** O script de integração BEIR não rodou. Verifique no VPS:
  ```bash
  ssh root@187.77.234.79 'tmux capture-pane -p -t beir-trec 2>/dev/null | tail -30'
  ```

### 1.3 Verifique o PDF final

1. Abra `paper/publication/latex/pain-shadow-memory-2026.pdf` no Preview.app.
2. **VERIFY:** Title page renderiza "The Pain Diary and Shadow Discipline..." corretamente.
3. **VERIFY:** 4 figuras presentes (figure1-system-overview, figure2-salience-pipeline, figure3-shadow-state-machine, figure4-kg-edge-typing).
4. **VERIFY:** Nenhum `??` ou `?` no texto (marcadores de referência quebrada).
5. **VERIFY:** nDCG@10 = 0.5213 ± 0.0004 aparece consistente no abstract e nas tabelas.

### 1.4 Verifique tamanho do PDF

```bash
ls -lh paper/publication/latex/pain-shadow-memory-2026.pdf
```

- **VERIFY:** Tamanho entre **500 KB e 50 MB**.
- Se < 500 KB: PDF pode estar incompleto ou corrompido. **STOP.**
- Se > 50 MB: arXiv rejeita. Você precisará otimizar figuras. **STOP.**

---

## §2 — Verificação da Conta arXiv (T-25 min | ~09:05 BRT)

### 2.1 Login

1. Abra `https://arxiv.org` no browser.
2. Clique em **"Log in"** (canto superior direito).
3. Entre com suas credenciais.

### 2.2 Confirme endorsement cs.IR

1. Após login: clique no seu nome → **"My account"**.
2. Localize a seção **"Endorsements"**.
3. **VERIFY:** `cs.IR` está listado como ativo/endorsed.
4. Se `cs.IR` **não está endorsado**: **STOP. Você não pode submeter hoje.** O processo de endorsement leva ~5 dias úteis. Envie email para `pre-arxiv-endorsement@arxiv.org` e reagende submit para quando endorsement chegar.

### 2.3 ORCID (opcional)

- Se você já tem ORCID registrado: anote o ID (formato `0000-0000-0000-0000`) — você vai usar no formulário.
- Se não tem ORCID: pule este item. Não é obrigatório para submissão.

---

## §3 — Build do Tarball de Submissão (T-20 min | ~09:10 BRT)

### 3.1 Entre no diretório LaTeX

```bash
cd /Users/lab/Claude/Projetos/memoria-nox/paper/publication/latex
```

### 3.2 Gere o tarball

```bash
bash arxiv-package.sh arxiv-submit-2026-06-02.tar.gz
```

Se o script `arxiv-package.sh` não existir, use o comando manual:

```bash
tar -czf arxiv-submit-2026-06-02.tar.gz \
  main.tex refs.bib neurips_2024.sty figures/*.pdf
```

### 3.3 Verifique o conteúdo do tarball

```bash
tar -tzf arxiv-submit-2026-06-02.tar.gz
```

Saída esperada — deve conter exatamente estes arquivos (ou similar):

```
main.tex
sec_abstract.tex
sec_1_3.tex
sec_4_7.tex
refs.bib
neurips_2024.sty
figures/figure1.pdf
figures/figure2.pdf
figures/figure3.pdf
figures/figure4.pdf
```

- **VERIFY:** Nenhum arquivo `.aux`, `.log`, `.bbl`, `.blg` no tarball.
- **VERIFY:** Todos os 4 PDFs de figuras presentes em `figures/`.
- **VERIFY:** Tamanho do tarball ~800–900 KB (se for muito maior, verifique se figuras raster PNG entraram por engano).

```bash
ls -lh arxiv-submit-2026-06-02.tar.gz
```

---

## §4 — Preenchimento do Formulário arXiv (T-15 min | ~09:15 BRT)

### 4.1 Inicie nova submissão

Abra: `https://arxiv.org/submit/new`

### 4.2 Licença

No dropdown de licença, selecione:

```
Creative Commons Attribution 4.0 International (CC BY 4.0)
```

### 4.3 Categoria primária

- **Primary archive:** `Computer Science`
- **Primary category:** `cs.IR` (Information Retrieval)

### 4.4 Cross-list

Adicione as três categorias (campo "Add cross-list"):

```
cs.CL
cs.AI
cs.DB
```

### 4.5 Título

Cole exatamente (90 chars):

```
The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents
```

### 4.6 Autores

- **Name:** `Luiz Antonio Busnello` (consistente com o LaTeX após 2026-05-05; nome formal acadêmico)
- **Affiliation:** `Curious Tech Entrepreneur, São Paulo, Brazil`
- **Email:** `lab@generantis.com.br`
- **ORCID** (se tiver): cole o ID. Se não tiver: deixe em branco.

### 4.7 Abstract

**Caminho recomendado (canonical):** abra `paper/publication/latex/sec_abstract.tex` e copie o conteúdo **DENTRO** de `\begin{abstract}...\end{abstract}` (sem as tags begin/end). arXiv aceita LaTeX inline math (`$\Delta$`, `$\pm$`, `$[-0.014, +0.034]$`, `$\times$`) e renderiza corretamente — preserva CIs, símbolos, tudo. ~1900 chars stripped, fits no limite 1920.

**Confira que zero `\cite{...}` tags restem:** verificado em 2026-05-05 que `sec_abstract.tex` tem zero `\cite` calls. Se algum entrar em revisão futura, converter para parênteses inline antes do paste (ex: `\cite{kohavi2020trustworthy,chapelle2012interleaved}` → `(Kohavi 2020; Chapelle 2012)`).

**Fallback (se arXiv renderer rejeitar inline LaTeX):** use a versão plain-text em `paper/publication/arxiv-submit-metadata.md` §3 (1997 chars). Se exceder 1920 chars, drop a frase final "Operational discipline is at least as important as embedding sophistication." (~85 chars saved).

> Texto canonical: `paper/publication/latex/sec_abstract.tex` (paper-internal source of truth).
> Plain-text espelho: `paper/publication/paper-abstract.md` (entre os separadores `---`).

### 4.8 Comments

Cole exatamente:

```
31 pages, 4 figures, 16 tables. Public repository: github.com/totobusnello/memoria-nox. Reproducibility kit includes evaluation harness, BM25/E5 baseline adapters, BEIR TREC-COVID adapter, LOCOMO adapter, and 60-query golden set. Solo author, 3-month production system. License: MIT.
```

(Fonte: `arxiv-submit-metadata.md` §4)

### 4.9 Keywords

Cole exatamente (ponto-e-vírgula como separador):

```
agent memory; retrieval-augmented generation; knowledge graph; hybrid retrieval; pain-weighted salience; shadow discipline; multi-agent systems; operational discipline; SQLite-based RAG; production memory system
```

(Fonte: `arxiv-submit-metadata.md` §7)

### 4.10 Upload do source

1. No campo de upload: selecione **"LaTeX (with bibliography)"**.
2. Faça upload do arquivo: `arxiv-submit-2026-06-02.tar.gz`
3. Aguarde o processamento do arXiv (~3–5 minutos). O arXiv recompila o source no servidor.

### 4.11 Verifique o preview PDF gerado pelo arXiv

Após o processamento, o arXiv exibe um preview do PDF compilado. **VERIFIQUE todos os itens abaixo:**

- **VERIFY:** Title page renderiza corretamente com o título completo.
- **VERIFY:** Todos os 4 figuras presentes (verifique páginas 5–29 do preview).
- **VERIFY:** Bibliography completa — sem entradas truncadas.
- **VERIFY:** Nenhum marcador `??` no texto.
- **VERIFY:** Abstract formatado corretamente na página 1.

Se o preview parecer correto em todos os pontos: vá para §6.

Se houver problema no preview: vá para §5.

---

## §5 — Se o Compile arXiv Falhar (contingência)

O arXiv tem compilador próprio. Erros comuns e correções:

### Package ausente

- Sintoma: erro tipo `! LaTeX Error: File 'XYZ.sty' not found.`
- Causa: o arXiv tem pacotes diferentes do TinyTeX local.
- Fix: adicione `\usepackage{XYZ}` em `main.tex`, re-gere o tarball (§3), re-faça o upload.

### Figura ausente

- Sintoma: erro tipo `! LaTeX Error: File 'figures/fig-XYZ.pdf' not found.`
- Causa: o PDF da figura não entrou no tarball, ou o path está errado.
- Fix: verifique `tar -tzf arxiv-submit-2026-06-02.tar.gz | grep figures`. Se a figura estiver faltando, re-gere o tarball. Se o path estiver errado, corrija em `main.tex`.

### Erro BibTeX

- Sintoma: citações aparecem como `[?]` ou erros de `bibtex` no log.
- Causa: `refs.bib` não entrou no tarball, ou há citação órfã.
- Fix: confirme que `refs.bib` aparece em `tar -tzf`. Se não aparecer: re-gere o tarball. Se aparecer: abra o log de erro do arXiv e localize a citação problemática.

### Timeout de compilação

- Sintoma: arXiv reporta que a compilação excedeu o limite de tempo (~5 min).
- Causa: o paper tem problema estrutural (loop, figura muito pesada, pacote com bug).
- Fix: reduza tamanho das figuras; verifique loops de `\input{}` em `main.tex`. Este é um erro raro — se acontecer, entre em contato com `help@arxiv.org`.

### Após corrigir qualquer erro acima

1. Re-gere o tarball (§3).
2. No formulário arXiv: use o botão **"Replace"** ou **"Edit"** para fazer novo upload.
3. Aguarde novo processamento (~3–5 min).
4. Verifique o preview novamente.

---

## §6 — Submit + Confirmação (T-5 min | ~09:55 BRT ou antes das 14:30 BRT)

### 6.1 Submit

1. Clique em **"Submit"**.
2. Leia e aceite os termos (agreeing to arXiv submission terms).
3. Confirme o submit.

### 6.2 Anote o paper ID

O arXiv envia um email de confirmação com o paper ID no formato:

```
2606.NNNNN
```

(Exemplo: `2606.04821`)

Anote este ID — você vai precisar dele nos próximos passos.

### 6.3 Janela de anúncio

| Horário de submit | Paper aparece no arXiv |
|---|---|
| Antes de 14:30 BRT (13:30 ET) | Esta noite ~21:00 BRT |
| Depois de 14:30 BRT | Próximo dia útil |

> Nota BRT: O BRT é UTC-3. A janela arXiv encerra às **14:00 ET** = **17:00 BRT** (com margem segura: 14:30 BRT).

---

## §7 — Pós-Submit Imediato (T+5 min a T+1h)

### 7.1 Atualize CITATION.cff

Abra `CITATION.cff` na raiz do repo. Localize as duas linhas TBD e substitua pelo ID real:

```yaml
# Antes:
arxiv-id: "TBD-arXiv:XXXX.XXXXX"
url: "TBD"

# Depois (substitua NNNNN pelo número real):
arxiv-id: "arXiv:2606.NNNNN"
url: "https://arxiv.org/abs/2606.NNNNN"
```

Também atualize a data de release se necessário:

```yaml
date-released: "2026-06-02"
```

### 7.2 Commit e push

```bash
git add CITATION.cff
git commit -m "post-submit: update CITATION.cff with arXiv ID 2606.NNNNN"
git push
```

**VERIFY:** `git push` retornou sem erro. Confirme no GitHub que o commit está lá.

---

## §8 — Dia da Distribuição (dia seguinte ao anúncio arXiv)

### 8.1 Confirme o paper ao vivo

1. Abra `https://arxiv.org/abs/2606.NNNNN` (substitua pelo ID real).
2. **VERIFY:** Título correto na página.
3. **VERIFY:** PDF baixa e abre normalmente.
4. Leia o PDF gerado pelo arXiv — confirme visualmente figuras, tabelas, referências.

### 8.2 Blog posts

Consulte `paper/publication/distribution/PLATFORM-METADATA.md` para os textos prontos.

Ordem de publicação (drip strategy — não simultâneo):

1. **Substack** (mesmo dia do arXiv announcement, 06-02 noite) — newsletter pra subs primeiro
2. **dev.to** (06-03 manhã BRT) — audiência técnica, code snippets
3. **LinkedIn** (06-04 manhã BRT) — profissional, lessons-learned format

Drip evita auto-canibalização do tráfego e dá 3 ondas distintas em vez de 1 picada única.

### 8.3 Hacker News

- Submit às **09:00 ET** (10:00 BRT em Apr-Out / 11:00 BRT em Nov-Mar) no dia seguinte ao anúncio arXiv.
- URL: link para o arXiv abstract (`https://arxiv.org/abs/2606.NNNNN`).
- Título HN: use o título exato do paper.

---

## §9 — Rollback (se algo der errado após submit)

### Se você percebeu um erro crítico logo após submeter

- **Não entre em pânico.** O arXiv tem mecanismo de replace que preserva o paper ID.
- Prazo para withdraw sem consequências: **4 dias após submit**.

### Replace (correção de conteúdo)

1. Login no arXiv → "My submissions".
2. Localize o paper → clique em **"Replace"**.
3. Faça upload do novo tarball corrigido.
4. O paper ID permanece o mesmo. A versão anterior fica acessível como `v1`.

### Withdraw (remoção)

- Use apenas se houver erro grave que não pode ser corrigido via replace.
- Acesse "My submissions" → "Withdraw".
- Papers withdrawn ainda ficam com um registro (o ID permanece, mas sem conteúdo).

---

## §10 — Contatos de Emergência / Fallback

| Situação | Contato |
|---|---|
| Qualquer problema técnico arXiv | `help@arxiv.org` (resposta em 24–48h) |
| Problemas de endorsement | `pre-arxiv-endorsement@arxiv.org` |
| Dúvida sobre categorias | `https://arxiv.org/help/prep` |

> Nota: o suporte do arXiv é lento. Se você encontrar blocker em submit-day, tente resolver pelos mecanismos do próprio formulário antes de esperar resposta de email.

---

## Apêndice — Referência Rápida de Metadados

Para conferência rápida sem abrir outros arquivos:

| Campo | Valor |
|---|---|
| Título | The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents |
| Autor | Luiz Antonio Busnello |
| Afiliação | Curious Tech Entrepreneur, São Paulo, Brazil |
| Email | lab@generantis.com.br |
| Categoria primária | cs.IR |
| Cross-list | cs.CL, cs.AI, cs.DB |
| Licença | CC BY 4.0 |
| Repositório | https://github.com/totobusnello/memoria-nox |
| nDCG@10 | 0.5213 ± 0.0004 (n=50, 3-run mean) |
| Chunks | 61,257 |

Fonte canônica de todos os metadados: `paper/publication/arxiv-submit-metadata.md`

---

*Runbook gerado em 2026-05-04. Atualizar se qualquer metadado mudar antes de 2026-06-02.*
