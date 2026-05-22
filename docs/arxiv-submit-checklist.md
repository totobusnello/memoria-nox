# arXiv Submit Checklist — Ter 2026-06-02

> Sequenciamento D27: Ter arXiv submit → Qua 2026-06-03 LAUNCH coordenado.
> Paper: `paper/paper-tecnico-nox-mem.md` + companion `.docx`.

---

## §1 Pre-flight (Seg 2026-06-01)

- [ ] Paper `.md` revisão final — Q4 numbers cravados via run Sáb 05-24
- [ ] Conversão LaTeX local: `pandoc paper/paper-tecnico-nox-mem.md -o paper/paper.tex --bibliography paper/refs.bib`
- [ ] Compilar PDF localmente: `pdflatex paper/paper.tex` — zero erros antes de subir
- [ ] Arquivo `.bib` atualizado com todas as cites:
  - LightRAG (HKU EMNLP 2025)
  - EverMind-AI / EverOS
  - Mem0
  - Zep
  - Letta (ex-MemGPT)
  - agentmemory
  - LoCoMo benchmark
  - LongMemEval benchmark
- [ ] Figuras numeradas (`Figure 1`, `Figure 2` ...) com captions completos
- [ ] Tabelas formatadas como `booktabs` LaTeX (`\toprule`, `\midrule`, `\bottomrule`)
- [ ] Abstract `<= 300 words` — contar via `wc -w` no bloco de abstract
- [ ] Afiliação do autor: **Independent Researcher** (Toto Busnello — advisor/board, não C-level executivo)
- [ ] Email de contato: `lab@nuvini.com.br`
- [ ] Seção de reprodutibilidade: pointer para `github.com/totobusnello/memoria-nox` + license MIT
- [ ] Nenhum dado proprietário inline no paper (chunks/IDs de prod não aparecem em exemplos)

---

## §2 Dia de submissão (Ter 2026-06-02 ~9h ET = ~6h BRT)

- [ ] Login / criação de conta em `arxiv.org` (se ainda não existir)
- [ ] Verificar endorsement necessário:
  - Categoria primária: `cs.IR` (Information Retrieval)
  - Cross-list: `cs.LG` (Machine Learning)
  - Se sem endorser: solicitar via `arxiv.org/auth/show-endorsers?archive=cs&subject_class=IR`
- [ ] Upload do pacote de submissão:
  - `paper.tex` (fonte LaTeX principal)
  - `refs.bib` (bibliography)
  - Figuras em `.pdf` ou `.png` (300 dpi mínimo)
  - **Não** subir `.md` ou `.docx` — arXiv processa apenas LaTeX/PDF
- [ ] Preencher campos obrigatórios:
  - **Title**: exato, sem trailing period
  - **Abstract**: igual ao paper, sem LaTeX markup extra
  - **Authors**: Toto Busnello
  - **Primary category**: `cs.IR`
  - **Cross-list**: `cs.LG`
- [ ] Licença: **CC BY 4.0** (consistente com código MIT no repo)
- [ ] Campo **Comments**: `Code available at https://github.com/totobusnello/memoria-nox`
- [ ] Revisar preview PDF gerado pelo arXiv antes de confirmar
- [ ] Confirmar submissão → receber arXiv ID (formato `2606.XXXXX`)
- [ ] Anotar: submit Ter → paper aparece público **Qua manhã ET** (sincronizado com LAUNCH)

---

## §3 Pós-submit (Ter 06-02 tarde)

- [ ] Adicionar arXiv ID ao README hero (`[![arXiv](https://img.shields.io/badge/arXiv-2606.XXXXX-b31b1b)](https://arxiv.org/abs/2606.XXXXX)`)
- [ ] Atualizar draft do Twitter/X thread com link arXiv
- [ ] Atualizar draft HN "Show HN" com link arXiv
- [ ] Atualizar assets Product Hunt com link arXiv
- [ ] Confirmar que `CITATION.cff` no repo tem `arxiv_id: 2606.XXXXX`

---

## §4 Falhas comuns + recovery

| Problema | Causa provável | Recovery |
|---|---|---|
| LaTeX compile falha no arXiv | Pacote não disponível no TeX Live arXiv | Testar com `pdflatex` local primeiro; substituir pacote por equivalente padrão |
| Endorsement ausente | Conta nova sem histórico cs.IR | Solicitar via `arxiv.org/auth/show-endorsers?archive=cs&subject_class=IR`; pode levar 1-2 dias |
| Figura ausente no PDF | Caminho relativo errado no `.tex` | Resubmit (gratuito, mas reseta fila — chegar antes das 14h ET para mesma janela) |
| License mismatch | Campo licença errado no formulário | Re-upload com `CC BY 4.0` correto; confirmar antes de submit final |
| Abstract com LaTeX markup | arXiv exige plain text no campo abstract | Remover `\textbf`, `\emph`, `\cite` do campo; manter apenas no `.tex` |
| Cross-list rejeitado | Categoria secundária inconsistente com conteúdo | Limitar a `cs.IR` apenas se necessário |

---

## §5 Sequenciamento D27 — referência

```
Seg 2026-06-02  Pre-flight final (§1)
Ter 2026-06-02  arXiv submit ~6h BRT (§2) + pós-submit (§3)
Qua 2026-06-03  LAUNCH coordenado:
                  - arXiv paper live (aparece manhã ET)
                  - HN "Show HN" post
                  - Twitter/X thread
                  - Product Hunt launch
                  - Reddit r/MachineLearning + r/LocalLLaMA
                  - Trendshift listing update
```

> Se arXiv atrasar (ex: fila cheia, reject por formato), LAUNCH pode ser desacoplado — HN/Twitter não dependem do arXiv ID para rodar. Prioridade: não atrasar Qua por causa de arXiv.
