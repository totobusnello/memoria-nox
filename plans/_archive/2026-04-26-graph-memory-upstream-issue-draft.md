# graph-memory Upstream Issue Draft (B3-4)

**Status:** RASCUNHO — abrir como GitHub issue no repo upstream do graph-memory plugin quando Toto decidir.

**Repo upstream:** TBD (graph-memory plugin do OpenClaw — confirmar URL antes de abrir)

**Prioridade:** baixa (item #4 do backlog v1.6)

---

## Issue title

> Plugin startup log misleading — `provider=gemini` shown even when fallback to flash-lite is in effect

## Body

### Context

graph-memory plugin (loaded by OpenClaw v2026.4.23) prints on startup:

```
[plugins] [graph-memory] ready | db=/root/.openclaw/graph-memory.db | provider=gemini | model=gemini-2.5-flash-lite
[plugins] [graph-memory] FTS5 search mode (配置 embedding 可启用语义搜索)
```

The `provider=gemini | model=gemini-2.5-flash-lite` line reads correctly from `cfg.llm.baseURL` after our local patch (memory `feedback_graph_memory_startup_log_is_misleading`), but **upstream still hardcodes the model string at log-time** rather than inspecting the actual runtime config the doctor probe uses.

### Problem

In our experience (4+ months running graph-memory in production):

1. **Two reality channels:** the startup log claims one model; the doctor probe (separate process) reports another; `gm_messages` table writes a third (whatever Gemini actually returned).
2. **Triage cost:** when KG extraction starts failing, first instinct is to read the startup log → assume the model is wrong → restart gateway → no change. Real cause is upstream the doctor probe spawns a separate process with stale env vars.
3. **Patch fragility:** our local fix (`index.ts.bak-log-fix-*`) gets wiped on plugin reinstall (memory `feedback_models_auth_login_reinstalls_node_modules.md`).

### Reproduction

```bash
# In an environment where cfg.llm.baseURL = https://generativelanguage.googleapis.com
# and cfg.llm.model = gemini-2.5-flash-lite, but ENV var GEMINI_MODEL is unset:
systemctl restart openclaw-gateway
journalctl -u openclaw-gateway --since "1 minute ago" | grep graph-memory
# observe the [plugins] line shows model from cfg, but doctor probe (called separately)
# may show different model from ENV fallback
```

### Suggested fix (upstream)

1. Single source of truth for model string: read once at plugin load, store in plugin state, log from state
2. Doctor probe should read same state (not re-read env vars)
3. Optional: emit a single `[graph-memory] config: ${JSON.stringify(canonicalConfig)}` line at startup

### Workarounds we've documented

- Local patch `index.ts.bak-log-fix-*` (re-applied after every plugin reinstall)
- Auto-memory entry `feedback_graph_memory_startup_log_is_misleading.md` warns operators
- Validation procedure: always check `gm_messages` table directly (NOT log) when investigating extraction issues

### Environment

- OpenClaw v2026.4.23
- graph-memory plugin (version: TBD — `openclaw plugin list` should report)
- Node.js v22.22.2
- Linux kernel 6.x (Ubuntu 25.x)
- Gemini API (gemini-2.5-flash-lite)

### Related

- Internal incident: see `docs/INCIDENTS.md` (graph-memory cegueira semântica detection)
- Internal feedback: `feedback_graph_memory_startup_log_is_misleading.md`
- Internal feedback: `feedback_validate_features_with_db_not_logs.md`

---

## How to actually open this issue

1. Identify upstream repo URL: `openclaw plugin info graph-memory` ou `npm info @openclaw/plugin-graph-memory repository`
2. Search existing issues for similar reports (avoid dup)
3. Open issue with the body above (translate Chinese line to English: "(set embedding to enable semantic search)")
4. Tag as `bug` + `developer-experience` + `low-priority`
5. Link this draft file in commit closing the issue
