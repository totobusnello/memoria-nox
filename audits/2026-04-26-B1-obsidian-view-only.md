# B1 Fase 4 — Obsidian View-Only (2026-04-26)

**Status:** ✅ DONE em ~50min reais (estimativa: 1h). **Destrava Fase P (productização NOX-Supermem).**

**Trigger:** Roadmap v1.6 listava B1 como "POST-GATE 2026-05-02+", mas decidimos antecipar pré-gate (sistema estável, gate é 04-30, nada que mude até lá).

---

## Goal & Decisão arquitetural

**Goal:** visualizar segundo cérebro como galáxia 3D no Mac, **read-only**, zero risco de corrupção.

**Decisão chave:** roadmap original previa `graphify-out/obsidian/` gerado por `graphify`, mas:
- `graphify` CLI **não está instalado** na VPS
- `graphify-out/` está vazio
- Construir generator novo é mais simples que instalar+configurar graphify

**Approach:** Python script standalone (`/root/.openclaw/scripts/export-obsidian-vault.py`, 430 LOC). Lê `memory/entities/*.md` + `kg_entities`/`kg_relations` do nox-mem.db. Gera vault em `/root/ObsidianVault-build/`. Cron diário 02:30 BRT (post-backup-all). rsync VPS→Mac via Tailscale (script local em `scripts/sync-obsidian-vault.sh`).

**Por que NÃO TS subcommand `nox-mem export-obsidian`:** Generator não toca o nox-mem.db de forma destrutiva (só READ), não precisa do withOpAudit/safeRestore stack, e iterar visualização é mais rápido em Python solto. Pode virar TS subcommand depois se justificar (Wave 2+).

---

## Vault structure

```
ObsidianVault/
├── .obsidian/
│   ├── app.json           (frontmatter visible, no markdown links)
│   ├── core-plugins.json  (12 core plugins enabled)
│   └── graph.json         (3D-friendly: tag color groups, link distance 250, repel 12)
├── README.md              (intro + plugin install + sync instructions)
├── Entities/
│   ├── Projects/    (12 .md de memory/entities/projects/)
│   ├── Decisions/   (127 .md)
│   ├── Lessons/     (42 .md)
│   ├── Agents/      (1 .md — nox)
│   └── Systems/     (1 .md — nox-mem)
└── Knowledge Graph/
    ├── _index.md            (top 30 entities, relations breakdown, Dataview queries)
    └── by-type/
        ├── project.md       (per-type tables: name, mentions, first/last seen)
        ├── decision.md
        ├── lesson.md
        ├── person.md
        ├── agent.md
        ├── organization.md
        ├── document.md
        ├── tool.md
        ├── technology.md
        ├── location.md
        ├── currency.md
        ├── date.md
        └── device.md
```

**Total:** 199 .md files, 880KB on disk.

---

## Wikilinks generation

Pipeline:
1. **First pass:** parse 183 entity files, register slugs → vault paths
2. **Second pass:** build `wmap = {entity_slug.lower() → vault_path}` from entity files + KG entities (longest names first to avoid substring shadowing)
3. **Third pass:** rewrite each entity body, wrapping known names with `[[target|display]]` — but **skip** code blocks, existing wikilinks, markdown links, HTML comments

**Coverage:** 183 wikilink keys (entity files only — KG-only entities like "Toto", "OpenClaw" não têm files reais, viram ghost notes em Obsidian, esperado).

---

## Cron + sync

**VPS cron (added 04-26):**
```
30 2 * * * /usr/bin/python3 /root/.openclaw/scripts/export-obsidian-vault.py >> /var/log/nox-obsidian-export.log 2>&1
```
Roda 02:30 BRT (após `backup-all.sh` 02:00). Idempotente — sempre wipea e regenera. `/var/log/nox-obsidian-export.log` coberto pelo `/etc/logrotate.d/nox` glob.

**Mac sync script:** `scripts/sync-obsidian-vault.sh` (no repo memoria-nox). rsync via Tailscale `root@100.87.8.44`, exclui `.obsidian/workspace*.json` e `cache` pra preservar UI state local. Pode virar launchd plist no futuro pra sync automático manhã.

---

## Plugins recomendados (manual install Mac)

1. **Dataview** — tabelas dinâmicas em `Knowledge Graph/_index.md`
2. **Graph Analysis** — centrality scores em entidades (descobre hub nodes)
3. **BRAT** (Beta Reviewers) → install **3D Graph** via BRAT (https://github.com/AlexW00/obsidian-3d-graph) — galáxia 3D rotacionável
4. **Core Graph plugin** já habilitado via `.obsidian/core-plugins.json`

---

## Smoke tests (5/5 passaram)

| # | Teste | Resultado |
|---|---|---|
| 1 | Generator roda sem error | ✅ "DONE — 199 .md files, 221.6 KB total" |
| 2 | Vault structure correta (Entities/{5 dirs} + Knowledge Graph + .obsidian) | ✅ |
| 3 | Entity files com frontmatter Obsidian + tags + aliases | ✅ (nuvini.md: name/type/tags/description/status/category) |
| 4 | KG index gerado com Dataview queries | ✅ (top 30 + relations breakdown + DQL blocks) |
| 5 | rsync VPS→Mac via Tailscale | ✅ "199 .md files in /Users/lab/ObsidianVault/" |

---

## Files criados/modificados hoje (B1)

**VPS:**
- `/root/.openclaw/scripts/export-obsidian-vault.py` (NOVO, 430 LOC)
- `/root/ObsidianVault-build/` (NOVO, 199 .md)
- crontab entry 02:30 BRT
- `/var/log/nox-obsidian-export.log` (será criado no primeiro cron run)

**Repo memoria-nox (Mac):**
- `scripts/sync-obsidian-vault.sh` (NOVO, executable)
- `audits/2026-04-26-B1-obsidian-view-only.md` (este doc)
- `~/ObsidianVault/` (sincronizado, fora do repo)

---

## Estado pós-B1

| Item | Status |
|---|---|
| Fase 4 Obsidian view-only | ✅ DONE 04-26 (era POST-GATE 05-02+) |
| Fase P productização | 🔓 destravada — depende de "Fase 4 estável 30d" agora |
| Tier 2 PDFs (B2) | ⏳ ainda POST-GATE (paralelo após gate) |
| Backlog B3 | ⏳ ainda POST-GATE |

---

## Próximos passos sugeridos

1. **Toto: instalar Obsidian + 4 plugins** (5min) → abrir `~/ObsidianVault/` → conferir grafo
2. **Validar que cron 02:30 BRT roda amanhã** (`tail /var/log/nox-obsidian-export.log` 04-27 manhã)
3. **Setup launchd plist no Mac** pra puxar auto às 03:00 BRT (15min, opcional)
4. **Aguardar gate 04-30 salience** sem mexer em mais nada

---

## Critérios de "Fase 4 estável" (30d até pode iniciar Fase P)

- [ ] Cron diário roda sem erro 7 dias seguidos
- [ ] Sync Mac sem corrupção (zero edits acidentais sobrevivendo regen)
- [ ] Toto usou o vault pelo menos 3x na semana pra explorar contexto
- [ ] Grafo 3D mostra clusters reais (projetos/pessoas/decisões agrupados)
- [ ] Zero falsos negativos em busca Obsidian que nox-mem encontraria

Quando todos ✅ por 30d → unblocked Fase P (productização NOX-Supermem).
