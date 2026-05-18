# nox-mem ROI Calculator

> Ferramenta de suporte à venda e onboarding. Responde as três perguntas mais frequentes antes da conversão.
>
> **Uso:** Compartilhar com prospects, embed na landing page, usar em DMs de suporte.
> **Audiência primária:** Developer ou profissional de conhecimento avaliando se vale a pena pagar vs se hospedar.
>
> **Cross-links:** `docs/cost-model.md` (dados brutos) · `docs/gtm/PRICING-STRATEGY.md` (decisões de tier)

---

## Pergunta 1: "Por que pagar hosted vs me hospedar?"

O custo *visível* do self-hosting é baixo. O custo *real* inclui tempo.

| Componente de custo | Self-host (VPS + DIY) | Nox-Supermem Hosted Pro |
|---|---|---|
| VPS Hostinger | $6–$11/mês | Incluído |
| Setup inicial (one-time) | 4h × seu valor/hora | 0 |
| Manutenção mensal (updates, monitoramento) | 1–2h/mês × seu valor/hora | 0 |
| Gemini API key (power user, 1k queries/dia) | ~$3/mês | Incluído |
| Backup + DR planning | 1–2h/mês × seu valor/hora | Incluído |
| Multi-device sync | 1h setup + $0 se rsync funcionar | Automático |
| Troubleshooting quando quebra | Variável | SLA gerenciado |
| **Total mensal (só infra)** | **~$10–$15** | **[H] ~$25–$40** |
| **Total com 2h/mês de tempo a $50/hr** | **~$110–$115** | **[H] ~$25–$40** |
| **Total com 2h/mês de tempo a $100/hr** | **~$210–$215** | **[H] ~$25–$40** |

**Conclusão rápida:** se o seu tempo vale mais de $15/hora, hosted já é financeiramente equivalente. Se vale $50+/hora, hosted é significativamente mais barato no custo total real.

### E se eu sei self-hostar bem e faço em 30 min?

Justo. Para o developer experiente que leva 30 min de setup e zero manutenção, o self-hosting faz sentido no OSS free tier. O hosted é para quem prefere usar o tempo em outras coisas — não para quem gosta de configurar infraestrutura.

---

## Pergunta 2: "Por que pagar vs usar o OSS gratuito?"

### Matriz de friction: OSS vs Hosted

| Ponto de friction | OSS (self-hosted) | Hosted Personal | Hosted Pro |
|---|---|---|---|
| Criar conta | Git clone + npm install + Node.js + Gemini key | 1 clique signup | 1 clique signup |
| Tempo até primeira query | 15–30 min (setup + configure) | 2–5 min | 2–5 min |
| Memória persistente entre dispositivos | Manual (rsync/SCP entre VPS e local) | Automático (cloud sync) | Automático |
| Atualizar versão | Git pull + npm install + restart | Automático | Automático |
| Backup se VPS cair | Você configura ou perde | Backup automático 30d | Backup automático 30d |
| Monitorar uptime | Você monitora ou fica sem memória | Monitorado | Monitorado |
| KG extraction nightly | Você configura cron | Configurado | Real-time |
| P5 viewer (dashboard) | Self-hospedar também | Incluído | Incluído |

### O "aha moment" que justifica pagar

Imagine: você está em uma reunião importante, tenta recuperar uma decisão técnica de 3 semanas atrás, e:
- **OSS self-hosted:** sua query funciona se o VPS está up, se o nox-mem-api está rodando, se você lembrou de vectorize os últimos chunks. Se qualquer coisa falhou nas últimas 24h, você não sabe.
- **Hosted Pro:** a query funciona. Pronto.

O valor não é o que você ganha — é o que você não perde.

---

## Pergunta 3: "Por que pagar nox-mem vs usar memanto?"

### Comparação direta de capacidades

| Capacidade | memanto (SaaS) | nox-mem Hosted Pro |
|---|---|---|
| **Dados são seus** | ❌ Ficam no servidor Moorcheh | ✅ Export a qualquer hora (A2) |
| **Você escolhe o provider de LLM** | ❌ Provider deles, decisão deles | ✅ Gemini/OpenAI/Anthropic/Voyage (A3) |
| **Open source** | ❌ Backend fechado | ✅ MIT — você pode auditar tudo |
| **Backup é um arquivo** | ❌ Depende da plataforma | ✅ `cp nox-mem.db backup.db` |
| **Pode migrar para self-host** | ❌ Impossível sem perder dados | ✅ Export + self-host = zero data loss |
| **Conveniente (hosted)** | ✅ SaaS | ✅ Hosted gerenciado |
| **Conflict detection** | ✅ (text-level, NLI) | 📋 L2 specced (SQL deterministic, mais preciso) |
| **Confidence/provenance** | ✅ em produção | 📋 L3 specced (gated on eval) |
| **Knowledge Graph** | ❓ (não divulgado) | ✅ 15.6k entities, 21.5k relations, SQL |
| **Eval benchmarks públicos** | Self-reported (não verificável) | Honest golden set n=80, publicar só quando ganhar |
| **Temporal decay** | Proprietário (não auditável) | ✅ salience = recency × pain × importance (código público) |

### Perguntas que você deveria fazer antes de escolher memanto

1. **"Posso exportar todos os meus dados se quiser sair?"** — Se a resposta não for "sim, formato aberto, a qualquer hora", isso é lock-in.
2. **"Onde ficam meus dados fisicamente?"** — Se a resposta for vaga ("nossos servidores seguros"), você não tem controle.
3. **"Como funciona o conflict detection deles?"** — Text-level NLI tem taxa de falso positivo. SQL em KG é determinístico. Pedir evidência.
4. **"O que acontece com meus dados se a empresa fechar?"** — Com nox-mem, o SQLite está na sua máquina. Com SaaS, depende do plano de contingência deles.

### Quando memanto é a escolha certa

Honestamente: se você não quer self-host nunca, não se importa com portabilidade de dados, e quer uma UX polida com suporte dedicado hoje — memanto pode ser adequado enquanto o Nox-Supermem hosted ainda está sendo construído.

Nox-mem é a escolha certa se você valoriza: autonomia de dados, transparência de código, ou a opção de migrar para self-host a qualquer momento sem perder nada.

---

## Calculadora rápida de ROI — "Qual tier faz sentido para mim?"

Responda as perguntas:

**1. Você tem skill para configurar um VPS e rodar um processo Node.js?**
- Sim → Free OSS é uma opção válida para você
- Não → Personal ou Pro hosted são o caminho

**2. Você está disposto a gastar 4h de setup + 1h/mês de manutenção?**
- Sim (e valorizo a experiência) → OSS
- Não → Personal hosted paga pelo seu tempo

**3. Qual o volume de uso que você espera?**
- < 500 queries/dia, < 50k chunks → Personal
- 500–5k queries/dia, 50k–250k chunks → Pro
- > 5k queries/dia ou time → Team
- Automações + enterprise → Enterprise

**4. Você vai compartilhar memória com um time?**
- Não → Personal ou Pro
- Sim → Team

**5. Você precisa garantia de uptime (SLA) ou suporte rápido?**
- Não → qualquer tier (o SLA informal é melhor que VPS DIY)
- Sim (uso em produção business) → Pro ou Enterprise

### Tabela de decisão rápida

| Perfil | Tier recomendado | Custo hipotético |
|---|---|---|
| Developer curioso | Free OSS | $0 (paga provider) |
| Professional usando diariamente | Personal | [H] $9–$15/mês |
| Power user, uso intenso | Pro | [H] $25–$40/mês |
| Time pequeno (3–10 pessoas) | Team | [H] $20–$35/usuário/mês |
| Empresa / automações | Enterprise | Custom |

---

## Cálculo de payback — "Quando esse investimento se paga?"

Para um profissional que usa nox-mem para trabalho (consultor, engenheiro, gerente de produto):

**Premissa conservadora:** nox-mem economiza 15 minutos por dia em recuperar informação que você teria que procurar manualmente (email, Notion, Slack, Git, WhatsApp).

```
15 min/dia × 20 dias úteis/mês = 5h/mês economizadas
5h × R$ 150/h (valor hora conservador) = R$ 750/mês de valor
Custo Personal hosted hipotético: R$ 60/mês
ROI: R$ 750 / R$ 60 = 12.5× mensal
Payback: imediato (primeiro mês)
```

Para uma perspectiva mais conservadora (5 min/dia, valor hora R$ 80):

```
5 min/dia × 20 dias = 1.67h/mês
1.67h × R$ 80/h = R$ 133/mês de valor
Custo: R$ 60/mês
ROI: 2.2× — ainda positivo
```

**Nota:** esses cálculos são estimativas para tomada de decisão. O valor real depende de como você usa a ferramenta.

---

*Gerado 2026-05-18 (Wave H). Preços marcados com [H] são hipotéticos — Toto decide os valores finais.*
*Cross-links: `docs/cost-model.md` · `docs/gtm/PRICING-STRATEGY.md` · `docs/COMPETITIVE-POSITIONING.md`*
