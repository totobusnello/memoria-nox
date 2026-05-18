# memoria-nox OpenAPI Spec

The OpenAPI 3.1 spec lives at `docs/openapi/openapi.yaml`.

## SDK generation

### TypeScript

```bash
cd sdk/typescript
npm install
npx openapi-typescript ../../docs/openapi/openapi.yaml -o src/generated/types.ts
npm run build
```

### Python

```bash
cd sdk/python
pip install -e ".[dev]"
python -m build
```

## Spec version

`1.0.0-wave-d` — covers Waves A through D (Core, Search, KG, P1/Answer, A2/Export-Import, P5/Viewer, L2/Conflicts, L3/Confidence, P2/Hooks).
