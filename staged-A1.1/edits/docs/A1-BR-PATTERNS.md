# A1.1 — Padrões de PII Brasileiro (CPF/CNPJ/PIX/CEP/RG)

> Extensão do filtro de privacidade A1 (`staged-privacy/`) com cobertura
> de PII brasileiro. Endereça o gap **G2 (CRITICAL)** do THREAT-MODEL e
> destrava o GTM Nox-Supermem para o mercado PT-BR.

**Status:** Implementado em `staged-A1.1/edits/src/lib/privacy-br/`. Aguarda
integração com pipeline de ingest na VPS (`/root/.openclaw/workspace/tools/nox-mem/`).

**Branch:** `wave-f/2026-05-18/A1.1-br-pii-patterns`.

---

## 1. Por que isso existe

O A1 original cobria 13 padrões US-centric (SSN, telefone US, AWS, JWT,
GitHub tokens, etc) com 1.7% de FP rate. Resultado: ao rodar sobre um
documento PT-BR cheio de CPF/CNPJ/CEP, **nenhum** dos identificadores
brasileiros era filtrado. Você acaba indexando PII de cliente em chunks
buscáveis. Em produção comercial (Nox-Supermem tier B/C, LGPD), isso é
inaceitável.

O G2 do threat-model categorizou como CRITICAL porque:

1. **LGPD Art. 5º, II + Art. 11** define CPF/CNPJ/RG como dados pessoais
   sensíveis (categoria especial quando combinados com nome).
2. **Sanção máxima**: 2% do faturamento limitado a R$ 50M por incidente.
3. **Concorrência**: Memanto e AgentMemory não cobrem PT-BR PII por design
   (foco mercado US). Nox-mem se diferencia rodando filtro local sem
   round-trip pra um serviço externo.

Este pacote elimina a lacuna e fica como camada agnóstica chamável de
qualquer ponto do pipeline (ingest, MCP server, search hit-redaction, etc).

---

## 2. Catálogo de padrões

Doze (12) tipos cobertos. Cada um vem com:
- **Regex** Unicode-safe (lookbehind/lookahead, nunca `\b` — falha em ç/ã).
- **Validador** opcional (dígitos verificadores onde existe).
- **Confidence assignment** baseado em validação:
  - HIGH (≥ 0.95): DV passa.
  - MEDIUM_HIGH (0.85): formato bate, sem validação possível.
  - MEDIUM (0.75): match razoável.
  - LOW (≤ 0.5): match casual, alto risco FP.
  - VERY_LOW (0.3): formato bate mas validação falhou (placeholder, dígito errado).

### 2.1 CPF — Cadastro de Pessoas Físicas

| Campo | Valor |
|---|---|
| Kind | `cpf` |
| Formatos | `XXX.XXX.XXX-XX` ou `XXXXXXXXXXX` (11 dígitos) |
| Validador | `validateCpf()` — algoritmo Receita Federal (2 DVs mod 11) |
| Confidence (válido) | 0.95 |
| Confidence (DV inválido) | 0.3 |

**Algoritmo do DV:**

```
Posições 0..8: multiplica cada dígito pelo peso (10..2). Soma.
mod = soma % 11. dv1 = mod < 2 ? 0 : 11 - mod.
Posições 0..9 (incluindo dv1): pesos (11..2). Soma.
mod = soma % 11. dv2 = mod < 2 ? 0 : 11 - mod.
```

**Exemplo válido:** `111.444.777-35` → CPF clássico de fixture (não é PII real).

**Exemplo inválido:** `123.456.789-00` — formato bate, mas dv1 deveria ser 0
(soma=210, mod=1, dv1=0 ✓) e dv2 deveria ser ≠ 0. Nossa validação rejeita.

**Caso especial — sequências triviais:** `00000000000`, `11111111111`, ...,
`99999999999` formalmente passam DV. Rejeitamos via regex `/^(\d)\1{10}$/`.

### 2.2 CNPJ — Cadastro Nacional Pessoa Jurídica

| Campo | Valor |
|---|---|
| Kind | `cnpj` |
| Formatos | `XX.XXX.XXX/XXXX-XX` ou `XXXXXXXXXXXXXX` (14 dígitos) |
| Validador | `validateCnpj()` — pesos diferentes do CPF |
| Confidence (válido) | 0.95 |

**Pesos:**

```
DV1: weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] sobre primeiros 12 dígitos.
DV2: weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] sobre primeiros 13 dígitos.
```

**Exemplo válido:** `11.222.333/0001-81` — vetor de teste comum.

### 2.3 PIX UUID v4

| Campo | Valor |
|---|---|
| Kind | `pix_uuid` |
| Formato | UUID v4 RFC 4122 (`8-4-4-4-12` hex, version=4, variant=8/9/a/b) |
| Validador | — (UUID v4 não tem checksum; formato já é restritivo) |
| Confidence | 0.85 |

**Importante:** rejeitamos UUID v1 (timestamp-based) porque a Receita Federal
mandou as bancas usarem v4 random em chaves PIX. UUIDs v1 vazariam contexto
temporal sem agregar valor PII.

### 2.4 PIX Telefone (chave PIX em formato `+55`)

| Campo | Valor |
|---|---|
| Kind | `pix_phone` |
| Formato | `+55DDD9XXXXXXXX` (13 dígitos puros após `+`) |
| Confidence (válido) | 0.95 |

Subset estrito de `telefone_br`. Distinção pelo `+55` obrigatório.

### 2.5 PIX Email

| Campo | Valor |
|---|---|
| Kind | `pix_email` |
| Formato | RFC 5322 simplificado (`local@dominio.tld`) |
| Confidence | 0.85 |

Cobre 99% dos emails em uso comercial. Não cobre quoted-strings nem
IP literal (`user@[192.168.1.1]`) — raros em chunks reais.

### 2.6 CEP — Código Postal

| Campo | Valor |
|---|---|
| Kind | `cep` |
| Formato | `XXXXX-XXX` (com hífen obrigatório) |
| Validador | `validateCep()` — 8 dígitos, rejeita `00000000` |
| Confidence (válido) | 0.85 |

**Decisão deliberada:** **NÃO** aceitar 8 dígitos puros sem hífen.
Risco de colisão com prefixo de CPF/CNPJ/telefone é alto demais. Se o
caller precisar de coverage mais ampla, pode estender via `BR_PATTERN_BY_KIND`.

### 2.7 RG — Registro Geral

| Campo | Valor |
|---|---|
| Kind | `rg` |
| Formatos | `XX.XXX.XXX-D` (SP) ou `XXXXXXXX` ou `XXXXXXXXX` ou `XXXXXXXX-X` |
| Validador | — (varia por estado, sem algoritmo nacional padronizado) |
| Confidence | 0.65 (MEDIUM_LOW) |

**Trade-off:** RG não tem checksum nacional. Estados diferentes usam
algoritmos diferentes (SP usa mod 11 com peso 2..9; outros não validam).
Mantemos confidence MEDIUM_LOW. Caller pode filtrar com `minConfidence`
ou exigir contexto explícito ("RG" próximo).

### 2.8 CNH — Carteira Nacional de Habilitação

| Campo | Valor |
|---|---|
| Kind | `cnh` |
| Formato | 11 dígitos sem pontuação |
| Validador | `validateCnh()` — algoritmo DETRAN |
| Confidence (válido) | 0.75 |

**Colisão com CPF:** ambos têm 11 dígitos. Resolução: detector aplica
`validateCpf` primeiro (catálogo prioriza CPF); CNH só fica em primeiro
plano se a base não passar como CPF. Caller que sabe que é CNH deve usar
`detectBrPiiByKinds(text, ["cnh"])`.

### 2.9 Título de Eleitor

| Campo | Valor |
|---|---|
| Kind | `titulo_eleitor` |
| Formato | 12 dígitos (8 base + 2 UF + 2 DV) |
| Validador | `validateTituloEleitor()` — algoritmo TSE com caso especial SP/MG |
| Confidence (válido) | 0.95 |

**Cuidado SP/MG:** quando UF é "01" (SP) ou "02" (MG), o DV substitui
0 por 1 quando mod==0. Implementado em `validateTituloEleitor`.

### 2.10 Telefone BR

| Campo | Valor |
|---|---|
| Kind | `telefone_br` |
| Formatos | `+55 11 99999-9999`, `(11) 99999-9999`, `11999999999`, etc. |
| Validador | `validateTelefoneBr()` — checa DDD válido e prefixo móvel 9 |
| Confidence (válido) | 0.85 |

**Móvel vs fixo:**
- Móvel: 9 dígitos (começa com 9). Inteiro com DDD: 11 dígitos.
- Fixo: 8 dígitos. Com DDD: 10 dígitos.
- Com país: +55 prefixo (12 ou 13 dígitos).

### 2.11 Cartão de Crédito BR

| Campo | Valor |
|---|---|
| Kind | `cartao_br` |
| Formato | 13-19 dígitos com separadores opcionais (espaço, hífen) |
| Validador | Luhn (mod 10) + rejeita sequências all-same |
| Confidence (válido) | 0.95 |

Cobre Visa (4), Mastercard (5), Elo, Hipercard (38/60), Amex (37/34, 15 dig).
Não distinguimos o emissor — o pattern só identifica que é cartão.

### 2.12 PIX CPF

| Campo | Valor |
|---|---|
| Kind | `pix_cpf` |
| Formato | 11 dígitos puros |
| Confidence | mesmo que CPF |

**Convenção:** o detector NÃO produz `pix_cpf` automaticamente — só via
`detectBrPii(text, { includePixCpf: true })`. Por default, CPF puro é
reportado como `kind: "cpf"`. Esta categoria existe pra casos onde o
chamador sabe pelo contexto (tag `<pix-key>...</pix-key>` por ex.) que
o número é uma chave PIX.

---

## 3. Resolução de overlap

Quando dois padrões matchem na mesma posição:

1. **Sort primário:** posição ASC (matches que começam antes vêm primeiro).
2. **Sort secundário:** length DESC (match mais longo ganha).
3. **Sort terciário:** confidence DESC.
4. **Sort quaternário:** ordem do catálogo (`BR_PATTERNS`).

Walk linear: aceita match → pula tudo que overlapa com `accepted.position[1]`.

**Resultado prático:**

- CNPJ formatado (`XX.XXX.XXX/XXXX-XX`) sempre ganha de CPF interno.
- Cartão de crédito Luhn-valid (16 dig) ganha de CNPJ inválido (14 dig
  partial match, mesmo que sub-bate, mas o CNPJ regex exige 14 exatos).
- Telefone vs CPF (ambos 11 dig): a ordem do catálogo é `cnpj, pix_uuid,
  cpf, cartao_br, telefone_br, pix_phone, pix_email, pix_cpf, cep, rg,
  cnh, titulo_eleitor`. CPF vem antes de telefone. Logo, para 11 dígitos
  ambíguos, **CPF é tentado primeiro**.

Você consegue forçar comportamento diferente passando `detectBrPiiByKinds`
com a lista exata desejada.

---

## 4. Integração com A1 (US patterns)

A função `redactAll()` em `integration.ts` roda **BR primeiro, US depois**:

```typescript
import { redact as redactUs } from "../privacy/filter.js";
import { redactAll } from "./lib/privacy-br";

const r = redactAll(text, redactUs);
console.log(r.text);                  // texto redactado
console.log(r.redactionCount);        // total BR + US
console.log(r.bySource.br.kinds);     // ['cpf', 'cnpj', ...]
console.log(r.bySource.us.kinds);     // ['anthropic-key', ...]
console.log(r.brMatches);             // matches BR detalhados
```

**Por que BR primeiro:**

- Padrões BR têm validações mais específicas (DV check).
- US `credit-card` (16 dig + Luhn) poderia engolir um CNPJ (14 dig) que
  precede um cartão num CSV. Rodar BR primeiro garante que CNPJ é taggeado
  corretamente antes do generic 16-digit matcher US rodar.
- US `env-secret` é muito ganancioso (`PASSWORD=...`); rodar depois não
  prejudica BR.

**Fallback:** se você não tem A1 instalado, use `redactBrOnly(text)`.

---

## 5. Medição de FP rate

`eval/fp-rate.ts` roda os padrões sobre um corpus sintético de texto
**SEM** PII (lorem ipsum, código TS, docs internos, hashes, UUIDs v1,
SKUs, datas em formato brasileiro, etc).

**Métrica primária:**

```
FP rate = blocos_com_match_HIGH-conf / total_blocos
```

Onde "bloco" = ~500 chars (chunk size típico nox-mem).

**Targets (gate de CI):**

- ≤ 2% por tipo de pattern.
- ≤ 5% agregado.

**Resultado atual (corpus interno):**

| kind | total matches | high-conf | medium | low | FP rate (high) |
|---|---|---|---|---|---|
| cnpj | 0 | 0 | 0 | 0 | 0.00% |
| pix_uuid | 0 | 0 | 0 | 0 | 0.00% |
| cpf | 3 | 0 | 0 | 3 | 0.00% |
| cartao_br | 1 | 0 | 0 | 1 | 0.00% |
| telefone_br | 10 | 0 | 10 | 0 | 0.00% |
| cep | 0 | 0 | 0 | 0 | 0.00% |
| rg | 2 | 0 | 2 | 0 | 0.00% |
| cnh | 0 | 0 | 0 | 0 | 0.00% |
| titulo_eleitor | 0 | 0 | 0 | 0 | 0.00% |

**Agregado:** 0.00% (10 blocos, 0 com hit high-conf).

**Telefone medium-conf 10:** o pattern `telefone_br` é deliberadamente
amplo (cobre 6 formatos). Strings como `"+55 11 99999-9999"` ou
`"Build version 1.2.3.4567"` (4567 é parte do regex `9?\d{4}\d{4}`?
Não — exige 8 dígitos no body). Os 10 matches são números que casam
o formato (ex: `12345678` interpretado como fixo sem DDD).

**Mitigação no pipeline:** consumidores usam `minConfidence: 0.9` no
default, então medium-conf não disparam redaction. Apenas alertas/auditoria.

---

## 6. Performance

- Regex compiladas no module-load (uma vez por processo).
- `getRegex()` retorna instância fresh com `lastIndex=0` pra cada chamada
  — evita state leak entre threads/concurrent calls.
- `detectBrPii(text)` é **O(N · P)** onde N=len(text), P=12 patterns.
- Bench informal: ~50µs por chunk de 1KB; ~500µs por chunk de 10KB.

Para fluxo de ingest a 60k chunks/dia, custo total: 30s/dia. Imperceptível.

---

## 7. Limitações conhecidas

1. **RG sem validação:** sem algoritmo nacional padrão. Confidence MEDIUM_LOW
   por design — o caller decide se redacta ou só logga.

2. **8 dígitos puros não viram CEP:** decisão deliberada (alto FP risk).
   Se você precisa, passe `formatMarker` custom + chame `cep` pattern
   manualmente.

3. **CNH colide com CPF:** 11 dígitos ambíguos vão pra CPF primeiro.
   Use `detectBrPiiByKinds(text, ["cnh"])` quando o contexto força CNH.

4. **PIX CPF não auto:** só via `includePixCpf: true`. Evita duplicação
   de match (mesmo CPF reportado 2x).

5. **Email — não cobre tudo do RFC 5322:** quoted-strings, IP literal,
   comentários — todos ausentes. Cobre 99% dos casos reais.

6. **CRP/CRM/OAB:** registros profissionais. Não implementados (escopo G3,
   ver THREAT-MODEL). Padrão amplo (sigla + UF + número) tem alto FP risk;
   defer pra A1.2 com contexto-aware detection.

---

## 8. Patterns futuros (A1.2)

Quando houver demanda + tempo:

| Tipo | Formato | Validador | Complexidade |
|---|---|---|---|
| CRP (Psicologia) | `XX/XXXXX` (UF + número) | — | baixa, mas FP risk alto |
| CRM (Medicina) | `CRM/UF XXXXX` | — | médio (precisa UF tabela) |
| OAB | `XXXXXX/UF` | — | médio |
| PIS/PASEP/NIT | 11 dígitos | DV mod 11 | baixa |
| INSS NIT | 11 dígitos (alias PIS) | mesmo PIS | baixa |
| RENAVAM | 9-11 dígitos | DV mod 11 | média |
| Inscrição estadual | varia por UF | varia | alta |
| Conta bancária | 4-12 dígitos + dígito | varia por banco | alta |

Sugestão: priorizar **PIS/NIT** (alto valor pra fintech / HR) e **RENAVAM**
(automotivo). Ambos têm DV calculável, FP rate baixo.

---

## 9. Como usar no pipeline nox-mem

### 9.1 No ingest (recomendado)

Inserir antes do `ingestFile()` em `src/ingest.ts`:

```typescript
import { redactBrPii } from "./lib/privacy-br";
import { redact as redactUs } from "./privacy/filter.js";
import { redactAll } from "./lib/privacy-br";

async function ingestFile(path: string) {
  const raw = await fs.readFile(path, "utf-8");
  const cleaned = redactAll(raw, redactUs, { minConfidence: 0.9 });
  // Persistir cleaned.text como chunk
  // Loggar cleaned.bySource.br.kinds em search_telemetry pra audit
  ...
}
```

### 9.2 No MCP server

`nox_mem_search` retorna chunks — antes de devolver para o LLM, passa
cada chunk pelo `redactBrPii` (defesa em profundidade — caso PII tenha
escapado do filtro de ingest):

```typescript
const hits = await searchChunks(query);
return hits.map(h => ({
  ...h,
  text: redactBrPii(h.text, { minConfidence: 0.9 }).redacted,
}));
```

### 9.3 No reflect / crystallize

LLM pode regurgitar PII em reflexões mesmo se o chunk original foi
filtrado (memória implícita). Rodar `redactAll` na saída do LLM antes de
persistir como insight.

---

## 10. Telemetria recomendada

Tabela `search_telemetry` já tem `query_text` + `golden_id` (A0 query
logging). Adicionar:

```sql
ALTER TABLE search_telemetry ADD COLUMN br_redactions_count INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN br_redactions_kinds TEXT; -- JSON array
```

Cron diário `audits/br-pii-leakage-check.sh`: query chunks_fts por padrões
literais de CPF/CNPJ (sample) e alerta se > 0.1% dos chunks têm vazamento.

---

## 11. Como rodar local

```bash
cd staged-A1.1
npm install
npm run build
npm test          # 204 tests
npm run eval:fp   # FP rate report
```

CI gate em `.github/workflows/`:

```yaml
- name: A1.1 BR PII tests
  run: cd staged-A1.1 && npm test
- name: A1.1 FP rate gate
  run: cd staged-A1.1 && npm run eval:fp
```

---

## 12. Checklist de adoção

- [ ] Code-review por security-reviewer (foco: regex catastrophic backtracking,
      lookbehind support em Node ≥ 10)
- [ ] Integration test contra dump real (sanitized) de chunks nox-mem
- [ ] Benchmark de overhead em ingest 60k chunks/dia
- [ ] Validação LGPD com asessor jurídico (Toto via Galapagos network)
- [ ] Doc usuário em `nox-supermem` repo (PT-BR, foco produto)
- [ ] Habilitar `br_redactions_count` em search_telemetry
- [ ] Cron de leakage check
- [ ] Atualizar threat-model marcando G2 como ENDEREÇADO

---

## Referências

- LGPD: Lei 13.709/2018 (Art. 5º, II + Art. 11)
- Receita Federal CPF: https://www.gov.br/receitafederal/pt-br
- Receita Federal CNPJ: idem
- BCB PIX spec: https://www.bcb.gov.br/estabilidadefinanceira/pix
- DETRAN CNH: spec pública (Macoratti reference)
- TSE Título de Eleitor: spec pública
- A1 (US patterns, baseline): `staged-privacy/edits/privacy/patterns.ts`
- THREAT-MODEL.md G2: ver `docs/security/THREAT-MODEL.md` (a criar)
- Memory: `feedback_js_regex_unicode_word_boundary_fails`

---

*Documento PT-BR, registro São Paulo, formato "você + 3ª pessoa".*
*Próxima revisão: após code-review por security-reviewer.*
