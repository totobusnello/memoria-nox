# Launch Demo Plan — asciinema CLI + F10 Dashboard GIF

**Gravação agendada:** Sábado, 2026-05-30 (slot ~1h)
**Launch:** Quarta, 2026-06-03
**Destino:** README hero + blog post

---

## §1 Goal

Gravar um clip de 60-90 segundos mostrando o nox-mem rodando em produção real — corpus de ~69k chunks, hybrid search ativo, salience deployed, flagship `/api/answer` respondendo com citações. Nada sintético: todas as queries serão executadas contra VPS `187.77.234.79:18802`.

Segundo asset: GIF de 10-15 segundos do F10 dashboard (`/observability/health.html`) mostrando polling ao vivo + delta numbers.

---

## §2 Demo flow (cravado — decisões tomadas antes de gravar)

Tempo total alvo: **~70 segundos**. Cada passo com `--idle-time-limit 1` (asciinema comprime pausas).

| # | Comando | Tempo esperado | Por quê |
|---|---------|---------------|---------|
| 1 | `nox-mem --help` | ~3s | Mostra os 26+ subcomandos; primeira impressão de maturidade do CLI |
| 2 | `nox-mem search "G10 conditional mutex"` | ~5s | Hybrid BM25+Gemini+RRF em corpus real; resultado com pain weight visível |
| 3 | `curl http://187.77.234.79:18802/api/health \| jq .` | ~5s | 69k chunks, vec 100%, salience active, KG stats — números que vendem |
| 4 | `curl -s -X POST http://187.77.234.79:18802/api/answer -H 'Content-Type: application/json' -d '{"query":"o que e G10d?"}' \| jq .` | ~10s | Feature flagship P1: resposta fundamentada com citações em ~1-2s |
| 5 | `nox-mem stats --json \| jq '{chunks,entities,relations,coverage}'` | ~5s | Fecha CLI com números de produção (KG entities/relations, coverage) |
| 6 | *(transição)* Abrir browser → `/observability/health.html` | ~10s | Mostra F10 dashboard polling ao vivo *(capturado separado como GIF)* |
| 7 | Scroll para `/observability/evals.html` | ~15s | Gate annotations, nDCG@10 D2=0.9126, benchmark numbers |

**Nota sobre §6-7:** o segmento de browser é capturado em clip separado (ver §5). O asciinema termina em `nox-mem stats`; o GIF do dashboard é asset independente.

---

## §3 Pre-record setup

Rodar **antes de iniciar a gravação** (preferencialmente num tmux dedicado):

```bash
# 1. Minimizar PS1 (sem path completo, sem hora, sem git branch)
export PS1='nox $ '

# 2. Limpar scrollback
clear

# 3. Verificar que VPS está healthy antes de gravar
curl -s http://187.77.234.79:18802/api/health | jq '{chunks: .total, coverage: .vectorCoverage, salience: .salience.mode}'

# 4. Verificar CLI disponível e versão
nox-mem --version

# 5. Definir tamanho do terminal
# Recomendado: 120×30 (README hero width > 80; permite output do jq sem truncar)
# Alternativa: 80×24 se README embed for coluna estreita
```

**Tamanho do terminal:** 120 colunas × 30 linhas. Permite que o output do `jq .` apareça sem wrapping feio. O README já usa `width="720"` no hero banner, então GIFs de 120 cols ficam bem.

**Fonte recomendada:** JetBrains Mono 14pt ou qualquer monospace com ligaduras (melhor legibilidade no GIF final).

---

## §4 Post-process pipeline (CLI asciinema → GIF)

### Opção A — agg (recomendado, mais simples)

```bash
# Gravar
asciinema rec demo.cast --idle-time-limit 1 --title "nox-mem demo"

# Converter para GIF
agg demo.cast docs/assets/demo-cli.gif \
  --theme dracula \
  --font-size 14 \
  --cols 120 \
  --rows 30

# Verificar tamanho (meta: <2MB para GitHub embed)
ls -lh docs/assets/demo-cli.gif
```

Se o GIF sair acima de 2MB, reduzir FPS:

```bash
agg demo.cast docs/assets/demo-cli.gif --fps-cap 15 --theme dracula --font-size 14
```

### Opção B — svg-term (inline SVG, menor)

```bash
npm install -g svg-term-cli
cat demo.cast | svg-term --out docs/assets/demo-cli.svg --window --width 120 --height 30
```

SVG é menor que GIF e não depende de GitHub LFS, mas não anima em todos os Markdown renderers. Verificar rendering em github.com antes de commitar.

### Decisão final

Usar **Opção A (agg → GIF)** como primário. Se `>2MB` após `--fps-cap 15`, usar Opção B como fallback e testar no README preview.

---

## §5 F10 dashboard GIF (browser)

Asset separado do asciinema. Mostra polling ao vivo com delta numbers em `/observability/health.html`.

### Ferramentas (macOS)

```bash
# Opção 1: Kap (GUI, gratuito) — recomendado
# https://getkap.co — gravar área da tela, exportar GIF/MP4

# Opção 2: peek (Linux) ou gifski + QuickTime (macOS)
# No macOS: gravar .mov com QuickTime Player → converter
brew install gifski
gifski --fps 10 --width 800 -o docs/assets/demo-dashboard.gif -- *.png
# (exportar frames do .mov via ffmpeg primeiro)

# Opção 3: ffmpeg direto (se souber o window ID)
# Mais complexo — usar Kap como primeira opção
```

### Script do clip (10-15s)

1. Abrir `http://187.77.234.79:18802/observability/health.html`
2. Aguardar 1 ciclo de polling completo (barra de progresso girando → atualização de números)
3. Zoom a 100%, janela sem outras abas visíveis
4. Gravar 10-15s mostrando: total chunks, vector coverage, último ingest, salience mode = active

**Meta:** < 1MB (clip curto, 10fps suficiente)

### Embed no README

```html
<!-- logo após os stat badges atuais, antes de "Quick start" -->
<p align="center">
  <img src="docs/assets/demo-cli.gif" alt="nox-mem CLI demo" width="720">
</p>

<p align="center">
  <img src="docs/assets/demo-dashboard.gif" alt="F10 observability dashboard" width="600">
</p>
```

---

## §6 Checklist de gravação (run-day Sábado 2026-05-30)

### Pré-gravação (~15 min)

- [ ] VPS healthy: `curl http://187.77.234.79:18802/api/health | jq .` retorna `total > 68000` e `vectorCoverage.percentage == 100`
- [ ] nox-mem CLI disponível no PATH: `nox-mem --version` sem erro
- [ ] Browser zoom em 100%, F10 dashboard carregando sem erros de console
- [ ] PS1 minimal configurado (`nox $ `)
- [ ] Terminal em 120×30, fonte legível ≥13pt
- [ ] `asciinema` instalado: `brew install asciinema`
- [ ] `agg` instalado: `brew install asciinema-agg`
- [ ] Kap instalado para dashboard GIF (ou `gifski` como fallback)
- [ ] Fazer **test run completo** (~5 min) — rodar o flow inteiro sem gravar; confirmar outputs satisfatórios
- [ ] Verificar que queries retornam resultados reais (ex: `nox-mem search "G10"` → resultados com pain weight visível)

### Gravação (~30 min)

- [ ] Take 1: gravar flow completo sem parar
- [ ] Rever take 1: verificar legibilidade, timing, nenhum erro de digitação
- [ ] Take 2 (mínimo): se Take 1 tiver pause longo ou typo, regravar
- [ ] Take 3 se necessário (critério: erro de comando, timeout na VPS, output truncado feio)
- [ ] Escolher melhor take → salvar como `demo.cast`

### Dashboard GIF (~15 min)

- [ ] Abrir Kap (ou ferramenta escolhida), selecionar área do dashboard
- [ ] Gravar 12-15s mostrando 1 ciclo de polling completo
- [ ] Exportar como GIF < 1MB
- [ ] Salvar como `demo-dashboard.gif`

### Post-process (~15 min)

- [ ] `agg demo.cast docs/assets/demo-cli.gif --fps-cap 20 --theme dracula --cols 120 --rows 30`
- [ ] Verificar tamanho: `ls -lh docs/assets/demo-cli.gif` → deve ser < 2MB
- [ ] Se > 2MB: reprocessar com `--fps-cap 15` ou Opção B (SVG)
- [ ] Testar embed local: abrir README.md no browser / VS Code preview
- [ ] `git add docs/assets/` + commit + push + PR de assets
- [ ] Verificar rendering no github.com antes de merge

---

## §7 Tempo estimado

| Fase | Tempo |
|------|-------|
| Setup + test run | 15 min |
| Gravação (3 takes + review) | 30 min |
| Dashboard GIF | 15 min |
| Post-process + tamanho + verificação | 15 min |
| Buffer (VPS lentidão / retake extra) | 15 min |
| **Total** | **~90 min** |

---

## §8 Destino dos assets

```
docs/assets/
  demo-cli.gif          ← asciinema → agg GIF (primário)
  demo-cli.svg          ← svg-term fallback (se GIF > 2MB)
  demo-dashboard.gif    ← F10 browser GIF
  demo.cast             ← raw asciinema recording (referência; não embed)
```

Todos commitados em `docs/assets/` (não usar Git LFS — GIFs < 2MB estão dentro do limite de 100MB do GitHub Free). Embed no README após merge dos assets.

---

*Plano criado 2026-05-21. Assets gravados em 2026-05-30. Embed no README antes do launch 2026-06-03.*
