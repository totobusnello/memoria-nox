# P6 — Mobile sync (Flutter)

> **Status:** Phase 1 kickoff — Flutter scaffold + Dart A1 PII filter port + Tailscale connection manager + local-only capture.
> **Spec:** [`specs/2026-05-18-P6-mobile-sync.md`](../specs/2026-05-18-P6-mobile-sync.md) (merged via PR #82).
> **Pillar:** P — Product UX.
> **Tagline:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

---

## O que é

App mobile **Flutter** (iOS 14+ / Android 8.0+ / API 26+) que conversa com a sua VPS nox-mem via tunel **Tailscale** (zero infra de terceiros) e mantém um **DB local SQLCipher** para captura offline.

Princípios não-negociáveis:

- **Sem SaaS** — Tailscale é P2P (WireGuard); nenhum servidor relay nosso toca os dados.
- **Sem chaves embutidas** — BYO key (herda A4).
- **A1 + A1.1 PII filter** roda no device antes de qualquer upload (port-for-port das 13 US + 12 BR patterns).
- **SQLCipher mandatório** — nada de SQLite plaintext no device.

---

## Phase 1 MVP — escopo deste kickoff

| # | Tarefa | Status |
|---|--------|--------|
| T1 | Flutter project skeleton (`pubspec.yaml`, iOS/Android targets) | scaffold pronto |
| T2 | Dart port do A1+A1.1 PII filter (`packages/nox_privacy/`) | 13 US + 12 BR patterns + tests |
| T3 | Local SQLCipher DB (`app/lib/db/`) | schema mirror simplificado + migration system |
| T4 | Tailscale connection manager (`app/lib/sync/tailscale_manager.dart`) | online/offline state machine + IP resolution |
| T5 | Local-only capture (`app/lib/capture/`) | manual paste + share intent + camera/OCR stubs |
| T6 | Sync protocol design (`docs/SYNC-PROTOCOL.md`) | delta sync bidirecional + conflict resolution |
| T7 | UI skeleton (`app/lib/ui/`) | main + capture + settings (sem search/answer) |
| T8 | Tests | 30+ unit, 10+ widget, 5+ integration stubs |
| T9 | README + docs | este arquivo + cross-link spec |

### Phase 2 (search UI) e Phase 3 (answer UI + full sync) ficam para kickoffs futuros.

---

## Setup local

Pré-requisitos:

- Flutter SDK ≥ 3.16
- Xcode 15+ (iOS) ou Android Studio (Android)
- Tailscale instalado e logado no Tailnet do usuário
- nox-mem-api rodando na VPS, alcançável via Tailscale IP (porta 18802)

Passos:

```bash
cd staged-P6-mobile/app
flutter pub get
flutter analyze
flutter test
# iOS:
cd ios && pod install && cd ..
flutter run -d <ios-device>
# Android:
flutter run -d <android-device>
```

Configuração inicial dentro do app (tela de Settings):

1. URL da VPS no Tailnet (ex: `http://100.x.y.z:18802`)
2. Bearer token (`NOX_API_TOKEN` gerado na VPS)
3. Toggle "Habilitar captura"

A passphrase do SQLCipher é derivada via `scrypt(N=2^14)` do device-unlock + um salt persistido no Secure Enclave / Android Keystore.

---

## Phase 2 + Phase 3 roadmap

| Fase | Foco | Estimativa |
|------|------|------------|
| **Phase 2** | UI search (UC-2) + UI sync status + conflict triage | ~10 dias |
| **Phase 3** | UI answer (P1 primitive, online) + full delta sync + voice capture (UC-4) | ~11 dias |
| **v2+ (deferred)** | Embeddings on-device, push notifications, widget, Watch app, OCR (E12 gate) | TBD |

---

## Cross-links

- Spec completa: [`specs/2026-05-18-P6-mobile-sync.md`](../specs/2026-05-18-P6-mobile-sync.md)
- A1 US patterns: [`staged-privacy/edits/privacy/patterns.ts`](../staged-privacy/edits/privacy/patterns.ts)
- A1.1 BR patterns: [`staged-A1.1/edits/src/lib/privacy-br/`](../staged-A1.1/edits/src/lib/privacy-br/)
- A2 archive (delta sync inspiration): [`staged-A2/edits/src/lib/archive/`](../staged-A2/edits/src/lib/archive/)
- P2 hooks pipeline: [`staged-P2/edits/docs/HOOKS.md`](../staged-P2/edits/docs/HOOKS.md)
- SDK TypeScript reference: [`sdk/typescript/`](../sdk/typescript/)

---

## Regra de ouro

Se for adicionar uma feature que **manda dado para qualquer servidor que não seja a VPS do usuário**, pare. Isso quebra o moat de autonomia que é o ponto inteiro do projeto.
