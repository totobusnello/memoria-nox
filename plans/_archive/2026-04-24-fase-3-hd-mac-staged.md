# Plan — Fase 3 HD Mac (abordagem staged revisada)

**Criado:** 2026-04-24 ~13:40 BRT
**Revisão da Fase 3 original:** em vez de rsync 22GB cru, ingestão staged por tipo de arquivo

---

## Discovery (2026-04-24)

Inventário `/Users/lab/Documents/`:

| Tipo | Qty | Tratamento |
|---|---|---|
| `.pdf` | 4432 | ⚠️ Precisa OCR/text-extract antes (nox-mem sem parser PDF) |
| `.docx` | 539 | ✅ Extraível via `pandoc` ou `mammoth` |
| `.md` | 11 | ✅ Direto ingestável |
| `.txt` | 0 | — |
| **Total texto relevante** | **982** | Staged em 3 tiers |

**Outros 4400+ files** são imagens, vídeos, zips, scans — não relevantes pra busca semântica sem processamento custoso.

---

## Tier 1 — Markdown + docx (staged now) — ~540 files

**Abordagem:**
1. Rsync filtrado apenas `*.md` + `*.docx` → `/root/.openclaw/workspace/memory/mac-docs/`
2. Converter `.docx` → `.md` via pandoc on-the-fly na VPS
3. Nox-mem watcher pega automaticamente (inotifywait)
4. Expected chunks: 500-2000 novos

**Estimativa tempo:** 5-10min transfer + 10-20min conversion + auto-ingest

## Tier 2 — PDF text-layer extraction (próxima sessão) — ~4432 files

**Abordagem:**
1. Rsync PDFs pra VPS `/root/.openclaw/workspace/memory/mac-pdfs-raw/`
2. Script Python usa `pdftotext` (poppler) pra cada PDF → `mac-pdfs-text/<slug>.md`
3. PDFs com text-layer OK (contratos, relatórios) → extração limpa
4. PDFs escaneados (fotos de boletos) → texto vazio → ignorar ou OCR Tier 3
5. Auto-ingest via watcher

**Estimativa tempo:** rsync ~30min + extraction ~1h + ingest ~10min

## Tier 3 — OCR para PDFs escaneados (sessão dedicada)

**Abordagem:**
1. Gemini 2.5 Flash tem vision capability
2. Script batch processa PDFs-sem-text-layer em lotes de 20
3. Cost: ~$0.0001/page × ~2000 pages = $0.20 total
4. Output: Markdown com texto OCR

**Custo:** baixo ($0.20-1.00)
**Tempo:** 1-2h processing
**ROI:** duvidoso se a maioria dos scanned PDFs forem boletos antigos

---

## Execução agora — apenas Tier 1

### Step 1 — Rsync filtrado

```bash
rsync -ahv --progress \
  --include='*/' \
  --include='*.md' --include='*.docx' \
  --exclude='*' \
  /Users/lab/Documents/ root@100.87.8.44:/root/.openclaw/workspace/memory/mac-docs/
```

### Step 2 — Pandoc conversion (.docx → .md) na VPS

```bash
ssh root@100.87.8.44 'which pandoc || apt-get install -y pandoc'
ssh root@100.87.8.44 '
  cd /root/.openclaw/workspace/memory/mac-docs/
  find . -name "*.docx" -print0 | while IFS= read -r -d "" f; do
    out="${f%.docx}.md"
    if [ ! -f "$out" ]; then
      pandoc "$f" -t gfm -o "$out" 2>/dev/null || echo "FAIL: $f"
    fi
  done
'
```

### Step 3 — Verify auto-ingest

Watcher pega em 15s por debounce. Chunks novos aparecem em `/api/health`.

---

## Tier 2 — Plan detalhado (executar próxima sessão)

### Script `scripts/pdf-text-extract.sh`

```bash
#!/bin/bash
# Extract text layer from PDFs. Skips scanned-only PDFs (empty output).
SRC=/root/.openclaw/workspace/memory/mac-pdfs-raw
DST=/root/.openclaw/workspace/memory/mac-pdfs-text
mkdir -p "$DST"
find "$SRC" -name "*.pdf" -print0 | while IFS= read -r -d "" f; do
  name=$(basename "$f" .pdf)
  out="$DST/${name}.md"
  [ -f "$out" ] && continue
  txt=$(pdftotext "$f" - 2>/dev/null)
  if [ -n "$txt" ] && [ $(echo "$txt" | wc -w) -gt 20 ]; then
    {
      echo "---"
      echo "source: $f"
      echo "type: pdf-extracted"
      echo "---"
      echo
      echo "$txt"
    } > "$out"
  fi
done
```

### Expected outcome

- ~2000-3000 PDFs com text-layer OK → markdown files criados
- ~1500-2500 PDFs scanned → ignorados (aguardam Tier 3 OCR)
- Auto-ingest via watcher: +5000-15000 chunks esperados

---

## Tier 3 — OCR Gemini (futuro)

Não executar sem decisão explícita. Custo monetário + compute considerável.

Pre-req: lista de PDFs Tier 2 que retornaram texto vazio ou <20 words.

---

## Status atual (2026-04-24 14:00 BRT)

- ✅ Discovery completo (22GB, breakdown por tipo)
- ✅ **Tier 1 EXECUTADO**: 550 files, 2697 chunks, 100% vectorized
- ⏸️ Tier 2 planejado (PDFs text-layer)
- ⏸️ Tier 3 deferred (OCR opcional)

## Tier 1 — Resultados reais

- Rsync: 550 files, 131MB em 20s (6.4MB/s)
- Pandoc conversion: 532/539 docx → md (98.7% success, 7 falhas silenciosas)
- Watcher auto-ingest disparou em paralelo (via modify events)
- Chunks criados: 2697 (média ~5 chunks/file)
- Vectorize: 2697/2697 em 161s via Gemini batchEmbedContents
- DB size: 121 → 170MB (+49MB)
- Search validado: "contrato mercos nuvini" retorna Term Sheet Forseti, NDAs, entity
- Backup preservado (backups/nox-mem-pre-source-archive-*.db de antes)

**Lesson**: Watcher **É** async e processa modify events do rsync corretamente — apenas demora alguns minutos até o debounce + pipeline completar. Force-ingest pré-watcher é redundante (e causa ENOENT em paths com espaço se shell splitting errado).

---

## 🎯 Comando para Toto executar (Tier 1)

Cole esse comando no terminal do Mac (`~/Claude/Projetos/memoria-nox/` ou qualquer dir):

```bash
rsync -ahv --progress --include='*/' --include='*.md' --include='*.docx' --exclude='*' /Users/lab/Documents/ root@100.87.8.44:/root/.openclaw/workspace/memory/mac-docs/
```

Expected: ~550 files, ~50-200MB, 2-5 minutos de transferência.

**Pós-rsync**, rodar (1 comando):

```bash
ssh root@100.87.8.44 'which pandoc || apt-get install -y pandoc; cd /root/.openclaw/workspace/memory/mac-docs/ && find . -name "*.docx" -print0 | while IFS= read -r -d "" f; do out="${f%.docx}.md"; [ -f "$out" ] || pandoc "$f" -t gfm -o "$out" 2>/dev/null || echo "FAIL: $f"; done; echo "DONE"'
```

Watcher auto-ingesta. Check health em 2min:

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq ".chunks.total, .sectionDistribution"'
```

Esperado: +500-2000 chunks.
