# memoria-nox OpenAPI Spec

> **Canonical spec:** [`docs/openapi.yaml`](../openapi.yaml) (root of `docs/`) — version `1.0.0-rc1`.

The file `docs/openapi/_legacy-wave-d.yaml` is a superseded snapshot (`1.0.0-wave-d`) kept for
reference only. Do not use it for SDK generation or tooling.

## SDK generation

### TypeScript

```bash
cd sdk/typescript
npm install
npx openapi-typescript ../../docs/openapi.yaml -o src/generated/types.ts
npm run build
```

### Python

```bash
cd sdk/python
pip install -e ".[dev]"
python -m build
```

## Spec version

`1.0.0-rc1` — covers Waves A–D plus F10 Observability endpoints.
