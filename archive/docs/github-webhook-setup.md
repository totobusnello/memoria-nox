# GitHub → OpenClaw Webhook Setup

## Resumo

GitHub Actions envia notificação de CI failure → VPS OpenClaw recebe → Forge investiga automaticamente.

## Componentes

1. **VPS:** Plugin `webhooks` ativo, route `github-ci` → sessão `forge`
2. **Firewall:** Porta 18789 aberta para GitHub IPs (192.30.252.0/22, 185.199.108.0/22, 140.82.112.0/20, 143.55.64.0/20)
3. **Auth:** Bearer token (secret em `/root/.openclaw/.env` como `GITHUB_WEBHOOK_SECRET`)
4. **GitHub:** Action workflow que converte evento → POST `create_flow`

## VPS Endpoint

```
POST http://187.77.234.79:18789/hooks/github
Authorization: Bearer <GITHUB_WEBHOOK_SECRET>
Content-Type: application/json

{
  "action": "create_flow",
  "goal": "<descrição do que aconteceu>",
  "status": "queued"
}
```

## GitHub Action Workflow

Adicionar em cada repo: `.github/workflows/notify-forge.yml`

```yaml
name: Notify Forge on CI Failure

on:
  workflow_run:
    workflows: ["CI", "Tests", "Build"]
    types: [completed]

jobs:
  notify-forge:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - name: Notify Forge
        run: |
          curl -s -X POST http://187.77.234.79:18789/hooks/github \
            -H 'Content-Type: application/json' \
            -H 'Authorization: Bearer ${{ secrets.OPENCLAW_WEBHOOK_SECRET }}' \
            -d "{
              \"action\": \"create_flow\",
              \"goal\": \"CI workflow '${{ github.event.workflow_run.name }}' failed on ${{ github.repository }} (branch: ${{ github.event.workflow_run.head_branch }}, commit: ${{ github.event.workflow_run.head_sha }}). Run URL: ${{ github.event.workflow_run.html_url }}. Investigate the failure, identify root cause, and suggest a fix.\",
              \"status\": \"queued\"
            }"
```

## Setup nos repos

1. Ir em cada repo → Settings → Secrets → Actions
2. Adicionar secret: `OPENCLAW_WEBHOOK_SECRET` = `72c4ed5d59905b82b74114c800b013124bbf7db9d2478052ad9eea822be5eff5`
3. Copiar `.github/workflows/notify-forge.yml` para o repo
4. Ajustar `workflows: ["CI", "Tests", "Build"]` para o nome real dos workflows do repo

## Repos para configurar

- [ ] totobusnello/nox-workspace
- [ ] totobusnello/agent-hub-dashboard
- [ ] totobusnello/Granix-App
- [ ] totobusnello/Frooty
- [ ] totobusnello/GalapagosApp

## Teste manual (na VPS)

```bash
curl -s -X POST http://127.0.0.1:18789/hooks/github \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer 72c4ed5d59905b82b74114c800b013124bbf7db9d2478052ad9eea822be5eff5' \
  -d '{"action":"create_flow","goal":"Test: CI failed. Ignore this.","status":"queued"}'
```

## Rollback

```bash
# Remover regras de firewall
ufw delete allow from 192.30.252.0/22 to any port 18789 proto tcp
ufw delete allow from 185.199.108.0/22 to any port 18789 proto tcp
ufw delete allow from 140.82.112.0/20 to any port 18789 proto tcp
ufw delete allow from 143.55.64.0/20 to any port 18789 proto tcp

# Desativar plugin
jq '.plugins.entries.webhooks.enabled = false' /root/.openclaw/openclaw.json > /tmp/oc.json && mv /tmp/oc.json /root/.openclaw/openclaw.json
```
