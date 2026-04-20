# Changelog — 2026-04-11 (Sessão Toto + Claude Opus)

> Forge: documente essas mudanças no CLAUDE.md do nox-workspace, nos SOUL.md dos agentes relevantes, e no SESSION-STATE.md.

---

## 1. KG Extraction: Ollama → Gemini 2.5 Flash

**Arquivo alterado:** `/root/.openclaw/workspace/tools/nox-mem/src/kg-llm.ts`
**Backup:** `kg-llm.ts.bak-20260411`

### O que mudou
- Provider: Ollama llama3.2:3b (local, `http://localhost:11434`) → Gemini 2.5 Flash (API, `generativelanguage.googleapis.com`)
- API key: usa `GEMINI_API_KEY` (mesma dos embeddings, já em `.env`)
- Input: 1500 chars → 8000 chars (Gemini suporta 1M tokens)
- Output: regex parsing de JSON → `responseMimeType: "application/json"` + `responseSchema` nativo
- Thinking: `thinkingBudget: 0` (sem reasoning, só extração estruturada)
- `maxOutputTokens`: 1024 → 4096

### Novos tipos de entidade
Adicionados: `technology`, `document`, `decision`, `metric`
(Antes: person, project, agent, tool, concept, organization)

### Novas relações
Adicionadas: `invested_in`, `negotiated_with`, `approved`, `rejected`, `owns`
(Antes: works_on, decided, uses, depends_on, blocked_by, reviewed, created, manages, communicates_with)

### Limites aumentados
- Entidades por chunk: 10 → 20
- Relações por chunk: 8 → 15

### Logging (NOVO — antes era fail-silent)
- Tag: `[KG-LLM]` no `nox-mem.log`
- Levels: INFO (recovery), WARN (empty response), ERROR (API failure)
- Contador de falhas consecutivas
- Alerta stderr após 5 falhas seguidas

### Por que
Ollama estava `inactive (dead)` no systemd (disabled) desde ~março. KG congelado em 384 entidades sem ninguém perceber porque o catch retornava `{ entities: [], relations: [] }` silenciosamente. Gemini usa a mesma key dos embeddings, tem 500 RPM free tier, e produz extração superior.

### Resultado do primeiro build
- `kg-build --limit 1000`: 1489 entities + 348 relations processadas
- Mentions aumentaram 70-78% (Toto: 401→704, OpenClaw: 312→554)
- +8 relações novas descobertas
- Zero erros durante o build

### Teste de validação (novos tipos)
```
Input: "Toto invested R$2M in FII São Thiago. Sorensen approved the SEC 20-F filing for Nuvini at 8x EBITDA multiple."
Output: 12 entities (document: SEC 20-F, metric: EBITDA multiple, technology: Supabase), 9 relations (invested_in, approved, owns)
```

---

## 2. Watcher reativado

**Serviço:** `nox-mem-watcher.service`

### O que aconteceu
Watcher parou em 2026-04-08 10:53 e nunca reiniciou. Sem watcher, nenhum arquivo novo é ingerido automaticamente no nox-mem.

### Fix
```bash
systemctl restart nox-mem-watcher
```
Status: `active` confirmado.

### Ação necessária
Verificar por que o watcher não reiniciou sozinho (pode faltar `Restart=always` no unit file).

---

## 3. KG-SUMMARY.md para boot dos agentes

**Arquivo criado:** `/root/.openclaw/workspace/memory/KG-SUMMARY.md`

### O que é
Output do `nox-mem kg-stats` salvo como arquivo markdown. Contém: total de entidades, relações, breakdown por tipo, top 10 entidades com mentions.

### Automação
Adicionado ao `nightly-maintenance.sh` — gerado automaticamente após `kg-build` todo domingo:
```bash
node dist/index.js kg-stats > /root/.openclaw/workspace/memory/KG-SUMMARY.md
```

### Como usar
Agentes podem ler no boot para ter contexto do grafo de conhecimento sem custo de query.

---

## 4. Consolidation skip quando sem chunks novos

**Arquivo alterado:** `/root/.openclaw/scripts/nightly-maintenance.sh`

### O que mudou
Phase 2 (agent reindex + consolidate) agora verifica se há chunks novos antes de rodar:

```bash
NEW_CHUNKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM chunks WHERE created_at > datetime('now', '-2 days');" 2>/dev/null || echo "0")
if [ "$NEW_CHUNKS" -gt 0 ]; then
    # ... reindex + consolidate
else
    log "Phase 2: Skipped (odd day but 0 new chunks in last 2 days)"
fi
```

### Por que
Quando o gateway está down ou não há atividade, consolidation rodava processando zero chunks — gastando CPU e Gemini API calls desnecessários.

---

## 5. Documento Nox Neural Memory atualizado (v5 → v6)

**Arquivo:** `docs/nox-neural-memory.md` (renomeado de `projeto-nova-memoria.md`)
**Repo:** github.com/totobusnello/nox-workspace

### Mudanças estruturais
- Renomeado: "Projeto: Segundo Cérebro" → "Nox Neural Memory"
- Tabela "O que já temos" expandida com capabilities reais do nox-mem v3.2
- Seção "Decisões de Arquitetura" adicionada (5 decisões documentadas)
- Seção "Riscos e Mitigações" adicionada (6 riscos)
- Seção "Métricas de Sucesso por Fase" adicionada
- Fase 1.5 (KG migration) adicionada como concluída

### Decisões documentadas
1. **Query Strategy:** Nox decide pelo tipo de pergunta (não busca nos dois sistemas sempre)
2. **graphify vs nox-mem KG:** complementares (docs vs memória operacional)
3. **Path vault:** `/root/vault/` separado + symlink no workspace
4. **Obsidian:** view-only primeiro (5a), escrita condicional após validação (5b)
5. **KG extraction:** Gemini 2.5 Flash (migrado de Ollama)

### Renumeração das fases (pelo Toto, v6)
- Fathom → Fase 3.5 (paralela, opcional, não bloqueia)
- Obsidian view-only → Fase 4
- Obsidian write → Fase 4b (condicional)
- openclaw-memory-sync → Fase 5

---

## 6. Ollama — pode ser desabilitado permanentemente

**Serviço:** `ollama.service` (já está `inactive` e `disabled`)

### Status
- Não é mais usado por nenhum componente do nox-mem
- KG extraction migrado para Gemini 2.5 Flash
- Modelo llama3.2:3b não é referenciado em nenhum código ativo

### Recomendação
Pode ser removido do systemd para simplificar o stack. Comando:
```bash
systemctl disable ollama
# Opcionalmente: apt remove ollama (libera ~2GB de disco)
```

---

## Arquivos modificados na VPS

| Arquivo | Tipo de mudança |
|---|---|
| `/root/.openclaw/workspace/tools/nox-mem/src/kg-llm.ts` | Reescrito (Ollama → Gemini) |
| `/root/.openclaw/workspace/tools/nox-mem/src/kg-llm.ts.bak-20260411` | Backup do original |
| `/root/.openclaw/workspace/tools/nox-mem/dist/kg-llm.js` | Compilado (npx tsc) |
| `/root/.openclaw/scripts/nightly-maintenance.sh` | Editado (consolidation skip + KG-SUMMARY) |
| `/root/.openclaw/workspace/memory/KG-SUMMARY.md` | Criado (kg-stats output) |

## Arquivos modificados no GitHub

| Repo | Arquivo | Mudança |
|---|---|---|
| `nox-workspace` | `docs/nox-neural-memory.md` | v4→v6, renomeado, decisões consolidadas |
| `memoria-nox` | `CLAUDE.md` + `.claude/CLAUDE.md` | KG extraction → Gemini 2.5 Flash |

---

*Gerado por Claude Opus — sessão 2026-04-11 com Toto.*
