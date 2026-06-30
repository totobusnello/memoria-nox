# Spot-check — Agent Identity Files Audit

**Data:** 2026-04-19 09:30 BRT
**Escopo:** 6 agentes × 7 arquivos canônicos
**Método:** medição de tamanho + md5sum + last-modified + diff manual de amostras

---

## Matriz de tamanhos (bytes)

| Agent  | SOUL    | IDENTITY | TEAM  | USER  | AGENTS  |
|--------|---------|----------|-------|-------|---------|
| nox    | 15591   | 925      | 773   | 2029  | 10916   |
| atlas  | 17890   | 1163     | 773   | 2029  | 10466   |
| boris  | 14921   | 1096     | 773   | 2029  | 10466   |
| cipher | 15080   | 1087     | 773   | 2029  | 10467   |
| forge  | 15574   | 1118     | 773   | 2029  | 12521   |
| lex    | 13794   | 2546     | 773   | 2029  | 10466   |

## Findings (por severidade)

### 🔴 CRITICAL — TEAM.md é stub idêntico em 6/6 agentes
- Todos 773 bytes; md5sum único (`6910bfc95a29d4144b7df758af33be9b`) em todos os 6.
- **Nunca foi customizado.** Confirma previsão do architect: usar TEAM.md como matcher viraria drift. Doutrina correta: matcher em `meta` table.
- **Ação:** deprecar TEAM.md OU reescrever como redirecionador pra `meta.dispatch_routing`.

### 🔴 HIGH — CHANNELS.md stale + 5/6 idênticos
- 5 agentes com mesmo stub (md5 `9630005f1a755428738eeac1404e27c0`); 1 customizado (não identificado qual).
- Todos com última modificação **2026-04-05** (14 dias atrás) enquanto `openclaw.json` evolui diariamente.
- **Ação:** gerar CHANNELS.md automaticamente do gateway config (cron); não editar manualmente.

### 🟡 MED — USER.md idêntico em 6/6
- Todos 2029 bytes; mesmo conteúdo (presumido — um único usuário Totó).
- **Ação:** consolidar em `shared/USER.md` com symlink nos agent dirs. Economiza 6× duplicação, fonte única.

### 🟡 MED — BOOTSTRAP.md ausente no Forge
- 5/6 agentes têm BOOTSTRAP.md (datados 2026-04-04); **Forge não tem**.
- Pode impactar boot flow do Forge.
- **Ação:** criar BOOTSTRAP.md pro Forge antes de ativar mesh.

### 🟢 LOW — SOULs diversos e atualizados
- MD5 únicos em todos 6 (14-18KB cada).
- Atualizados entre 2026-04-17 e 04-19 (vivos).
- **Ação:** nenhuma — SOUL é o SSoT funcional.

### 🟡 MED — IDENTITY.md com tamanhos variados
- 925B (nox) a 2546B (lex). Sugere conteúdo próprio por agente.
- Todos stale em 2026-04-05. Menos crítico que TEAM, mas merece revisão.
- **Ação:** spot-check manual pra decidir se mantém ou mescla em SOUL na 1.8b.

## Staleness global

| File            | Last modified (range) |
|-----------------|----------------------|
| SOUL.md         | 2026-04-17 a 2026-04-19 (vivo) |
| IDENTITY.md     | 2026-04-05 (14d stale) |
| TEAM.md         | 2026-04-05 (14d stale, stub) |
| USER.md         | 2026-04-05 (14d stale) |
| AGENTS.md       | 2026-04-05 (14d stale) |
| CHANNELS.md     | 2026-04-05 (14d stale) |
| BOOTSTRAP.md    | 2026-04-04 (15d stale — exceto Forge, ausente) |
| HEARTBEAT.md    | 2026-04-05 a 2026-04-13 (6-14d stale) — **já mapeado como gap** |

## Recomendações para Fase 1.8a / 1.8b

**Ação imediata (1.8a):**
- [ ] Criar `agents/forge/BOOTSTRAP.md` (tema "tem que existir antes do mesh")
- [ ] Aceitar TEAM.md como lápide — matcher vai em `meta` table
- [ ] Aceitar CHANNELS.md como stale — auto-gerar do openclaw.json em 1.8b

**Deferido (1.8b, pós-Path A):**
- [ ] Consolidar USER.md em `shared/USER.md` com symlinks
- [ ] Decidir: IDENTITY.md mescla em SOUL ou mantém separado?
- [ ] Deprecar TEAM.md formalmente (com redirect)

## Evidências brutas (para referência)

### TEAM.md hash (6/6 idênticos)
```
6910bfc95a29d4144b7df758af33be9b — nox, atlas, boris, cipher, forge, lex
```

### SOUL.md hashes (todos únicos)
```
14fa7c8bd98527ea9fa2a6b2aaf32f55  atlas
600d040421cf3035507b7a79569629ce  boris
9a61d0d5d8e904955c8c263ea283b457  cipher
4920d94cdc0a645b667505736059559c  forge
2f1ef033c5724c483b6867a42f108213  lex
53fa6388fe8456cfae8a31058db58a6d  nox
```
