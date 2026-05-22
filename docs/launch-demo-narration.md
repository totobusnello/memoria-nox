# Launch Demo — Narration Script

**Companion de:** `docs/launch-demo-plan.md` (plano operacional — não modificar)
**Gravação agendada:** Sábado, 2026-05-30
**Duração alvo:** 60-90s CLI asciinema + 10-15s GIF F10 dashboard (assets separados)
**Audiência:** internacional, English primary

---

## §1 Approach Decision

### Opção A — Pure terminal, NO voiceover (recomendado)

Captions on-screen em momentos-chave via svg-term annotations ou overlay de texto no GIF final. Sem áudio sincronizado.

**Prós:** re-take sem refazer áudio; acessível (surdos + som desligado); sem eco/ruído ambiente; distribuição mais simples (GIF embeds em qualquer lugar).

**Contras:** sem voz pessoal; captions precisam ser curtos para caber no frame.

### Opção B — Voiceover (Toto grava áudio simultaneamente)

Script §3 abaixo. Gravar CLI + áudio em paralelo, sincronizar no post.

**Prós:** mais pessoal, mais impacto em apresentações.
**Contras:** re-take implica regravar áudio; sync drift se typing speed variar; setup mais complexo.

### Recomendação: **Opção A**

Sem áudio, captions alinhadas por timestamp. Mais fácil de regravar, mais acessível, funciona em qualquer contexto (GitHub README, HN, Twitter/X, LinkedIn).

---

## §2 Caption Track (Opção A) — timestamp-aligned

Cada caption deve aparecer em overlay ou como legenda no player. Texto curto, direto.

| Timestamp | Visual | Caption (EN) | Caption (PT-BR) |
|---|---|---|---|
| 0:00–0:05 | `$ nox-mem --help` | "26 commands. Hybrid memory built for LLM agents." | "26 comandos. Memória híbrida para agentes LLM." |
| 0:05–0:15 | `$ nox-mem search "G10 conditional mutex"` | "Hybrid search: FTS5 + sqlite-vec + RRF, pain-weighted." | "Busca híbrida: FTS5 + sqlite-vec + RRF, pain-weighted." |
| 0:15–0:25 | `$ curl /api/health \| jq .` | "68k+ chunks, 100% vec coverage, salience active." | "68k+ chunks, 100% vec, salience ativa." |
| 0:25–0:40 | `$ curl /api/answer -d '{"query":"..."}' \| jq .` | "Flagship: answer endpoint. Citations included, ~1.6s end-to-end." | "Flagship: endpoint answer. Citações inclusas, ~1.6s end-to-end." |
| 0:40–0:50 | `$ nox-mem stats --json \| jq '{chunks,entities,relations,coverage}'` | "Knowledge graph: 15k entities, 21k relations — built nightly." | "Knowledge graph: 15k entidades, 21k relações — construído nightly." |
| 0:50–1:05 | Browser: `/observability/health.html` | "Production observability dashboard. Live polling, real numbers." | "Dashboard de produção. Polling live, números reais." |
| 1:05–1:20 | Browser: `/observability/evals.html` scroll | "Eval dashboard: every G-gate published, every claim defensible." | "Dashboard de avaliação: cada G-gate publicado, cada claim defensável." |

**Regras de caption:**
- Máx. 60 caracteres por linha
- Aparece logo quando o comando inicia sua execução (não esperar output completo)
- Desaparece ~0.5s antes do próximo passo para não sobrepor
- Usar fonte branca com sombra preta ou background semitransparente para legibilidade em qualquer tema de terminal

---

## §3 Voiceover Track (Opção B fallback) — full script ~90s

Falar devagar. Cada parágrafo alinhado ao timestamp do passo correspondente. Pausas naturais entre frases.

**Prep:** ler o script completo em voz alta uma vez antes de gravar. Meta: 90 palavras por minuto (conversacional, não apresentação acelerada).

---

**[0:00–0:05] — Help screen**

> "This is nox-mem. Twenty-six commands. Open-source hybrid memory built for LLM agents."

---

**[0:05–0:15] — Search**

> "It uses three retrieval layers in parallel: keyword search via FTS5, semantic search via sqlite-vec, and result fusion via RRF. Pain-weighting surfaces what cost you more — critical incidents rank higher than routine notes."

---

**[0:15–0:25] — Health endpoint**

> "The production corpus: sixty-eight thousand chunks, one hundred percent vector coverage, salience scoring active. G10d conditional mutex deployed — per-category threshold tuning that recovered multi-hop recall."

---

**[0:25–0:40] — Answer endpoint**

> "The flagship feature: a production answer endpoint. Send a query, get a grounded response with citations — directly from your memory corpus. End-to-end latency around one-point-six seconds."

---

**[0:40–0:50] — Stats**

> "The knowledge graph: fifteen thousand entities, twenty-one thousand relations, rebuilt nightly via Gemini extraction. Your memory doesn't just store — it understands structure."

---

**[0:50–1:05] — Health dashboard**

> "F10 observability: a live-polling dashboard showing corpus state in production. Delta numbers, coverage drift alerts, API latency — all from a single page."

---

**[1:05–1:20] — Evals dashboard**

> "Every tuning decision — every G-gate — is published in the eval dashboard with its nDCG@10 delta. D2 baseline: 0.9126. Every claim has receipts. If you build LLM agents and want memory that gets out of the way — nox-mem is open source, MIT licensed, link below."

---

## §4 F10 Dashboard GIF — narration (asset separado)

GIF de 10-15s capturado à parte do asciinema. Três momentos-chave:

### Frame 1 — 0:00–0:04: Health dashboard carregando

**O que aparece:** `/observability/health.html` abre, polling indicators piscam, chunk count e vector coverage visíveis.

**Caption (EN):** "Live corpus state: 68k+ chunks, 100% vec coverage."
**Caption (PT-BR):** "Estado do corpus ao vivo: 68k+ chunks, 100% vec."

**Voiceover (se Opção B):** "Production health at a glance — polling every thirty seconds."

---

### Frame 2 — 0:04–0:10: Evals dashboard scroll

**O que aparece:** `/observability/evals.html` com anotações G-series visíveis no gráfico nDCG@10 (G8, G9, G10, G10b, G10c, G10d).

**Caption (EN):** "Every eval gate annotated — nDCG@10 D2 = 0.9126."
**Caption (PT-BR):** "Cada gate anotado — nDCG@10 D2 = 0.9126."

**Voiceover (se Opção B):** "Every tuning decision leaves a mark — annotated gates, reproducible deltas."

---

### Frame 3 — 0:10–0:14: Click em anotação G10d

**O que aparece:** tooltip ou detail panel de G10d mostrando delta nDCG, threshold=2, categoria breakdown.

**Caption (EN):** "G10d ACTIVE-T2: per-category mutex recovered multi-hop recall."
**Caption (PT-BR):** "G10d ACTIVE-T2: mutex por categoria recuperou recall multi-hop."

**Voiceover (se Opção B):** "Every claim has receipts."

---

## §5 Title Cards — intro/outro para asciinema

Implementar via `echo` + `sleep` no início e fim do cast, ou via edição do `.cast` com `asciinema-edit` (se disponível).

### Intro (1.5s)

```
nox-mem · pain-weighted hybrid memory · open source
```

Exibir centralizado no terminal com cor de destaque (bold white ou cyan) antes do primeiro comando.

```bash
# Exemplo de implementação no script de gravação
echo -e "\033[1;36m  nox-mem · pain-weighted hybrid memory · open source\033[0m"
sleep 1.5
clear
```

### Outro (2s)

```
github.com/totobusnello/memoria-nox · MIT
```

Exibir ao final, após `nox-mem stats`, antes de encerrar a gravação.

```bash
echo ""
echo -e "\033[1;37m  github.com/totobusnello/memoria-nox · MIT\033[0m"
sleep 2
```

---

## §6 Dicas para o dia da gravação — Sábado, 2026-05-30

### Antes de começar

- Sala silenciosa (se Opção B): testar microfone com 30s de áudio, ouvir playback para detectar eco ou hum de fundo
- Fechar Slack, notificações do sistema, qualquer app que possa gerar popup em tela
- Confirmar VPS online: `curl -s http://187.77.234.79:18802/api/health | jq .total`
- Ajustar terminal para 120×30, fonte JetBrains Mono 14pt
- Definir `export PS1='nox $ '` antes de iniciar asciinema

### Durante a gravação

- **Mínimo 3 takes** — escolher o melhor no post
- Digitar devagar e deliberadamente — velocidade real, não acelerada
- Se errar comando: `Ctrl+C`, pausa de 2s, redigitar — não reiniciar o cast inteiro
- Verificar que cada saída de comando aparece completa antes de avançar para o próximo

### Verificação de caption drift

- Exportar take candidato como GIF
- Rever frame a frame: cada caption deve aparecer dentro de 0.3s do início do visual correspondente
- Regravar qualquer passo onde drift for maior que 0.3s — não ajustar no post se evitável

### Exportação final

Exportar em dois formatos, decidir no post qual vai para o README:

| Formato | Comando | Tamanho esperado | Uso |
|---|---|---|---|
| GIF com captions | `agg demo.cast demo-cli.gif --theme dracula` | 1-3MB | GitHub README hero |
| SVG sem captions | `svg-term < demo.cast > demo-cli.svg` | <500KB | Blog post embed |

Se GIF > 2MB: adicionar `--fps-cap 15` ao comando `agg`.

### GIF do F10 dashboard

Capturar separado via Gifski ou macOS QuickTime → Gifski:
- Abrir `/observability/health.html` em janela sem toolbars (Chrome kiosk mode: `--app=URL`)
- Gravar 15s de tela, exportar via Gifski com `--fps 10 --quality 85`
- Meta de tamanho: <1MB

---

*Documento companion de `docs/launch-demo-plan.md`. Para alterar o flow de comandos, editar o plano operacional — não este arquivo.*
