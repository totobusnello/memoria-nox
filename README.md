# memoria-nox

> Projeto que guia a evolução do **sistema de memória inteligente** (nox-mem) usado pelos 6 agentes AI do Totó na VPS, acessado via WhatsApp/Discord.

**Status atual:** v3.3 — 1.951 chunks 100% embedded, hybrid search funcional, autodefesa diária ativa. Ready para Fase 1.6.

---

## Por onde começar

### 🎯 Se abriu agora e quer saber o que fazer

1. Rode o check de saúde local:
   ```bash
   ~/Claude/Projetos/memoria-nox/scripts/check-nox-mem.sh
   ```

2. Abra o plano executável: [`plans/2026-04-19-unified-evolution-roadmap.md`](plans/2026-04-19-unified-evolution-roadmap.md)

3. Se quiser entender a visão antes: [`docs/nox-neural-memory.md`](docs/nox-neural-memory.md) (v12)

### 🚨 Se algo está quebrado

- Canary Discord `#nox-chief-of-staff` às 06:00 + Morning report às 06:30
- Detalhe de todos os fixes + rollback: [`plans/2026-04-18-tier0-tier1-session-log.md`](plans/2026-04-18-tier0-tier1-session-log.md)
- Audits técnicos: [`audits/`](audits/)

---

## Estrutura

```
memoria-nox/
├── README.md                                      ← você está aqui
├── CLAUDE.md                                      ← instruções pro Claude (v3.3)
│
├── plans/                                         ← EXECUÇÃO
│   ├── 2026-04-19-unified-evolution-roadmap.md   ← ⭐ source of truth
│   └── 2026-04-18-tier0-tier1-session-log.md     ← última sessão
│
├── docs/                                          ← VISÃO
│   └── nox-neural-memory.md                      ← v12 estratégica
│
├── audits/                                        ← DIAGNÓSTICO
│   ├── audit-2026-04-18-db-gaps-remediation.md   ← DB
│   ├── sre-deepening-2026-04-18.md               ← SRE/reliability
│   └── perf-baseline-2026-04-18.md               ← performance
│
├── specs/                                         ← ESPECIFICAÇÕES ATIVAS
│   └── 2026-04-12-self-evolving-hooks.md         ← Fase SEH (backlog)
│
├── scripts/                                       ← FERRAMENTAS
│   └── check-nox-mem.sh                          ← health check diário
│
└── archive/                                       ← HISTÓRICO (referência)
    ├── plans/                                     ← plans antigos (executados)
    ├── specs/                                     ← specs shipped
    ├── audits/                                    ← audits superseded
    ├── docs/                                      ← docs one-time (changelog, webhook setup)
    └── paper/                                     ← paper técnico (stale v3.0.0)
```

---

## Sistemas externos relacionados

| | Localização | Função |
|---|---|---|
| **Código nox-mem** | VPS `/root/.openclaw/workspace/tools/nox-mem/` | O sistema rodando |
| **Docs canonical** | VPS `/root/.openclaw/workspace/docs/` = GitHub `totobusnello/nox-workspace` | Doc estratégico espelhado aqui |
| **nox-supermem** | `~/Claude/Projetos/nox-supermem/` | Produto comercial (horizonte pós-Fase 4) |
| **Dashboard** | GitHub `totobusnello/agent-hub-dashboard` | UI do sistema |
| **Discord alerts** | `#nox-chief-of-staff` (webhook ativo) | Canary + morning report automáticos |

---

## Convenções

- **Specs e plans:** formato com checkbox tasks e chunk boundaries
- **Datas:** ISO (2026-04-19), sempre
- **Paths:** absolutos quando possível
- **Fonte da verdade de execução:** `plans/2026-04-19-unified-evolution-roadmap.md`
- **Fonte da verdade de visão:** `docs/nox-neural-memory.md`
- **Convenções do sistema rodando:** `CLAUDE.md`

---

## Contato / Ownership

- **Owner:** Toto Busnello
- **Bot alerts:** Discord `#nox-chief-of-staff` (Maestro#7017)
- **VPS SSH:** `ssh root@100.87.8.44` (Tailscale) ou `ssh root@187.77.234.79` (público)
