# Cross-Pillar Integration Tests — Wave G

> "Unit tests catch logic bugs. Integration tests at the seams catch the bugs unit tests miss."
> — Lesson from the AAD bug caught in Wave B+C round-trip test.

12 cross-pillar scenarios. 77 tests. Real in-memory SQLite (better-sqlite3). Zero mocks of the DB.

## Pilares combinados por cenário

| Cenário | Pilares | Foco | Testes |
|---|---|---|---|
| S1  | P1 + A1 + L4 | Ingest PII → search redacted → answer cita sem vazar | 6 |
| S2  | L2 + L3 | Conflito KG com gates de confiança + marca canônica | 8 |
| S3  | A3 + P1 | Fallback de provider sob carga concorrente + auth fast-fail | 5 |
| S4  | A2 + L4 + L2 + L3 | Round-trip export/import com KG + AAD regression | 10 |
| S5  | P2 + P1 | Pipeline de hooks → answer; PII drop vs redact | 6 |
| S6  | P5 + ingestion | Bus de eventos do viewer + flag NOX_VIEWER_SHOW_QUERY | 6 |
| S7  | L4 + L2 | Regex-first KG → conflito + audit trail | 5 |
| S8  | L3 + P1 | Ranking de confiança: disabled / shadow / active | 6 |
| S9  | op-audit + conflict_audit + ops_audit | Append-only enforcement (CWE-693) | 8 |
| S10 | A3 + ingest | Per-row provenance pra evitar corpus de embeddings mistos | 6 |
| S11 | P2 + A1 + A1.1 | Redaction US SSN + BR CPF; raw content NEVER em telemetria | 5 |
| S12 | export + import + search | Concorrência stress: 5 calls paralelos + lock simulation | 6 |

## Rodar

```bash
cd tests/cross-pillar
npm install
npm test
```

## Por que shims em vez de imports diretos

Os pilares staged (`staged-P1`, `staged-A2`, `staged-L2`, etc.) são pacotes TypeScript irmãos
com `rootDir` separado. Importar fonte `.ts` entre eles puxaria 9 árvores de módulos
sobrepostos no build do tsc — frágil e lento. A solução adotada:

- **`src/lib/schema.ts`** — schema canônico (v11+v19+v20+v21+v22) aplicado em SQLite `:memory:`.
- **`src/lib/pillar-shims.ts`** — cópias mínimas das funções puras de cada pilar (redact, extractEntityRefs, detectDirectConflicts, packArchive, applyConfidenceRanking, LLMFallbackChain, runHookPipeline, ViewerBus, withOpAudit). Cada shim cita o arquivo real do pilar como `Source:` no comentário.

Quando um pilar mergear pro main, o shim correspondente deve ser substituído por
import direto. Até lá, **drift no contrato real do pilar quebra esses testes alto e
claro** — exatamente a rede de proteção que Wave G existe pra prover.

## Bug-classes alvo

Cada cenário declara explicitamente a classe de bug que se propõe a pegar — sempre
um tipo de regressão que só vira detectável quando dois ou mais pilares se tocam:

- **S1**: PII vazando entre layer (ingest redige mas search/answer leem cópia pré-redação)
- **S2**: gate de confiança permitindo low-conf passar OU suprimindo audit
- **S3**: race em estado mutável do fallback chain (cooldown map, telemetria)
- **S4**: AAD desincronizado entre pack e unpack (o bug Wave B+C caçou)
- **S5**: telemetria de hooks gravando raw content por descuido de debug
- **S6**: flag de NOX_VIEWER_SHOW_QUERY invertida = vazamento por default
- **S7**: extraction_method mis-taggado após merge regex/LLM
- **S8**: shadow mode acidentalmente mudando ranking (defeats the whole point)
- **S9**: append-only quebrado por "cleanup" script ou crash mid-op
- **S10**: corpus de embeddings com dimensões mistas silenciosamente corrompido
- **S11**: A1.1 (CPF) nunca shippa e teste vira green sem cobrir
- **S12**: race em operações destrutivas simultâneas (CLAUDE.md regra #6)
