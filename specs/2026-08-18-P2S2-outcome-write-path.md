# P2S2 — write path de falha adjudicada (componente 1)

> **Estado:** spec. Nada implantado. Código vai por PR em `totobusnello/nox-workspace`;
> este documento vive no repo de pesquisa porque é decisão de desenho, não de produto.
>
> **Por que este componente vem primeiro:** roda nos **dois braços** (§2 trava a
> escrita como idêntica em controle e tratamento), então é **arm-blind por
> construção** e pode subir antes de existir qualquer noção de braço, sem gastar
> grau de liberdade nenhum. E ele produz a medição que hoje sustenta todo o resto
> sem ser medida: a **taxa real de episódios adjudicados por epoch**. Os
> `~396/epoch` do pré-registro são projeção; os cuts, o tamanho do pool
> competidor e todo alcance dependem dela.

## 0. Restrições verificadas em 2026-08-18, antes de escrever qualquer patch

O plano mandava checar três coisas. Resultado:

| verificação | resultado |
|---|---|
| Embedding dentro da transação impediria segurar o lock? | ❌ **Não é problema.** `src/ingest.ts` fecha a transação em `insertMany` (linha 169) e só **depois**, fora dela, chama `embedText` com `await` (linhas 180-201). `chunk + veredito` na mesma transação é viável. |
| Onde roda a adjudicação (define o modelo de ameaça)? | **No Mac** — `~/.paper2-verdicts` tem 134 arquivos no Mac e **não existe** na VPS. Logo a chamada atravessa o tailnet via `tailscale serve`, carrega `x-forwarded-for`, e o gate de token do `api-server.ts:120-127` **aplica**. |
| Precisa bump de `SCHEMA_VERSION`? | ❌ **Não.** Precedente no próprio código: `ensureBriefLog()` cria a tabela com `CREATE TABLE IF NOT EXISTS`, memoizado, zero `ALTER`, e `SCHEMA_VERSION` segue 18 de propósito (um processo com `dist` antigo lança se abrir DB mais novo, e a VPS tem API + watcher + MCP + crons no mesmo arquivo). Tabela nova segue esse padrão. |

⚠️ **Achado de segurança que muda o desenho.** O gate de token só morde quando há
`x-forwarded-for`; chamadas diretas de `localhost` **passam livres**, de propósito
(agentes, cron, watcher). Isto é aceitável para leitura. **Não é** para uma rota
que escreve o desfecho do estudo. Decisão: esta rota exige o token
**incondicionalmente**, independente de `x-forwarded-for`. Custa nada e fecha a
única porta por onde um write não autenticado entraria na tabela de desfecho.

## 1. O que muda em relação ao registrado, e por quê

O §2 diz que o veredito é escrito *"na mesma transação que o chunk"*. **Não é
implementável como está:** o veredito é um append em JSONL noutro host, e nenhuma
transação SQLite alcança isso.

**Conserto:** o veredito **consolidado** vira linha em `nox-mem.db`
(`p2_verdict`), escrita na mesma transação que o chunk. O JSONL mantém o papel de
saída bruta do painel e de artefato de cegamento pré-join. A invariante
`chunk ⟺ veredito` deixa de ser responsabilidade do handler e passa a ser
**propriedade do schema** — `CHECK` + trigger + uma query de auditoria.

## 2. Schema

```sql
CREATE TABLE IF NOT EXISTS p2_verdict (
  episode_id    TEXT PRIMARY KEY,          -- idempotência vive aqui
  severity      TEXT NOT NULL CHECK (severity IN ('S0','S1','S2','S3','S4')),
  sig_primary   TEXT NOT NULL,             -- assinatura, granularidade `primary`
  sig_coarse    TEXT,                      -- para o allowlist de escopo
  chunk_id      INTEGER NOT NULL,          -- o chunk escrito nesta transação
  panel_hash    TEXT NOT NULL,             -- sha256 do conjunto de vereditos brutos
  adjudicated_at TEXT NOT NULL,            -- instante do painel, do JSONL
  written_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_p2v_sig  ON p2_verdict(sig_primary);
CREATE INDEX IF NOT EXISTS idx_p2v_chunk ON p2_verdict(chunk_id);

-- invariante, direção veredito -> chunk: por trigger, não por handler
CREATE TRIGGER IF NOT EXISTS trg_p2v_chunk_existe
BEFORE INSERT ON p2_verdict
WHEN (SELECT COUNT(*) FROM chunks WHERE id = NEW.chunk_id) = 0
BEGIN SELECT RAISE(ABORT, 'p2_verdict.chunk_id inexistente'); END;
```

⚠️ `severity` inclui `S0` de propósito: τ = S1 é o corte de *falha*, mas o painel
adjudica `S0` e §5 exige reportar a terceira categoria. Gravar S0 mantém o
denominador auditável em vez de reconstruído.

## 3. Metadata no chunk — adição à tabela de campos travados

`episode_id` **sozinho não basta**: a designação agrupa por assinatura, e chunk
não carrega assinatura hoje. O `metadata` JSON do chunk recebe:

```json
{"p2": {"episode_id": "...", "sig_primary": "...", "severity": "S2"}}
```

Declarável e declarado: **não entra em termo nenhum de salience**. É a chave de
join que a regra de designação precisa e que o `episode_id` puro não dá.

## 4. `sig()` tem UMA implementação, em Python

A assinatura é calculada **uma vez**, pelo pipeline congelado `c0abe143`, no lado
Python. O TypeScript **só testa pertinência** contra o allowlist; nunca recomputa.
Duas implementações de `sig()` escreveriam a população errada em silêncio, e
"silêncio" é o modo de falha que esta semana já produziu três vezes.

## 5. Rota

`POST /internal/paper2/adjudicated-failure`

- **Flag:** `NOX_P2_WRITE_PATH=on`. Ausente ⇒ 404, indistinguível de rota inexistente.
- **Auth:** `Bearer $NOX_API_TOKEN` **sempre** (ver §0).
- **Idempotente** por `episode_id`: `INSERT ... ON CONFLICT DO NOTHING`; segunda
  chamada devolve `200 {"duplicate": true}` sem escrever.
- **Arm-blind por construção:** o handler não lê, não recebe e não pode resolver
  braço. Verificável por inspeção — nenhum import de artefato de atribuição.
- **Uma transação:** insere o chunk (via `ingestEntityFile`, para herdar
  `section`/`retention_days`), insere o `p2_verdict`, commita. Embedding **fora**
  da transação, depois do commit, como o `ingest.ts` já faz.
- `source_file` = `memory/entities/lessons/<episode_id>.md`, travado no §2 para
  cair no sub-pool global (janela de 30 d).

## 6. Verificação — tarefas

- [ ] Teste golden: com `NOX_P2_WRITE_PATH` **off**, briefs byte-idênticos ao pré-patch
- [ ] Invariante por SQL, depositável: `SELECT COUNT(*) FROM p2_verdict v LEFT JOIN chunks c ON c.id=v.chunk_id WHERE c.id IS NULL` = 0
- [ ] Invariante reversa (auditoria): todo chunk com `metadata->>'$.p2.episode_id'` tem linha em `p2_verdict`
- [ ] Idempotência: mesma chamada 2× ⇒ 1 chunk, 1 veredito
- [ ] Trigger morde: insert com `chunk_id` inexistente aborta
- [ ] Token: chamada sem `Bearer` ⇒ 401, **inclusive de localhost**
- [ ] Flag off ⇒ 404
- [ ] Log NDJSON append-only por escrita (`pruneEpochs(keep=3)` destrói o snapshot físico em 3 dias, então o log tem de bastar sozinho para replay)

## 7. O que este componente mede, e que hoje é chute

- [ ] **Episódios adjudicados por epoch** — os `~396` são projeção do §9. Todo cut
      medido em `CUTS-MEASURED-2026-08-18.json` depende dela.
- [ ] Distribuição de severidade **realizada** contra as shares registradas
      (S1 69,73% · S2 29,62% · S3 0,58% · S4 0,08%)
- [ ] Latência da escrita, para saber se cabe no caminho de adjudicação

## 8. O que este componente NÃO faz

Não despacha braço, não aplica boost, não lê `ASSIGNMENT.json`, não tem noção de
epoch de tratamento. São os componentes 2 e 3, e ambos dependem da decisão de
desenho ainda aberta (dose absoluta vs relativa ao cut do agente — ver
`CUTS-MEASURED-2026-08-18.json`).

---

## 9. ⚠️ Lendo o `ingest-entity.ts` para escrever o patch, cinco correções — e uma delas derruba uma afirmação REGISTRADA

Nada abaixo veio de reconstrução: é leitura do código na VPS mais medição no
corpus real, em 2026-08-18.

### (a) A afirmação verificada na v1.10 está errada, e o número certo vem de outra linha

O cabeçalho da v1.10 — hoje publicado no Zenodo e anexado ao registro OSF — diz:

> *"`COALESCE(importance,0) >= 0.7 OR COALESCE(pain,0) >= 0.7` — **passes**:
> verified that the ingest path populates the `importance` column via
> `inferImportance(chunk_type)`, so the written chunk carries 0.90"*

`inferChunkTypeFromPath()` reconhece **só** `entities/agents/`,
`entities/projects/`, `entities/people/` e `entities/systems/`. **Não existe caso
para `lessons/`** — cai no `return "other"`. E `inferImportance("other")` =
`FALLBACK_IMPORTANCE` = **0,40**, não 0,90.

Medido nos 168 chunks reais de `memory/entities/lessons/`:

| chunk_type | importance | pain | n | passa o gate |
|---|---|---|---|---|
| `other` | **0,40** | 0,20 | **126** | **0** |
| `other` | 0,90 | 0,20 | 41 | 41 |
| `other` | 0,90 | 0,70 | 1 | 1 |

O 0,90 existe, mas vem de **outra linha**: `compiledImportance =
Math.max(importance, 0.9)`, que se aplica **só à seção `compiled`**. A verificação
nomeou o mecanismo errado e acertou o número por sorte, para 1 chunk de N.

**Consequência de desenho:** por episódio, **apenas o chunk `compiled` entra no
pool de cobertura**. Frontmatter e timeline nascem com 0,40 e são invisíveis ao
caminho de cobertura. O write path tem de garantir seção `compiled`, e o
`p2_verdict.chunk_id` tem de apontar para **ela**, não para o primeiro chunk.

### (b) `pain` NÃO é a severidade adjudicada — é heurística de keyword no texto

O §2 registra `pain` como *"the adjudicated severity of the episode (S1→0.25 …
S4→1.0)"* e diz que é **"the treatment's carrier"**. O ingest escreve
`inferPain(chunkType, texto)` = `PAIN_BY_TYPE["other"] ?? 0.2`, mais 0,5 se o
texto casar `HIGH_PAIN_PATTERN`. Ou seja: **o carrier do tratamento seria um
regex sobre prosa.** É a mesma classe de
`feedback_pain_column_is_topical_not_episodic` (um documento *sobre* falha pontua
como falha).

**O patch tem de escrever `pain` explicitamente**, sobrepondo `inferPain`, dentro
da mesma transação. Sem isso o mecanismo carrega o sinal errado em silêncio.

### (c) A transação registrada exige extrair um núcleo síncrono

`ingestEntityFile` é `async`, e transação do better-sqlite3 **não pode** conter
`await`. Mas o corpo **não tem nenhum `await`** — o `async` é vestigial. Então a
extração é barata: expor `ingestEntityFileSync(content, relPath, db, overrides)`
e deixar o wrapper `async` chamando-a. Aí o handler faz UMA transação com o chunk
e o veredito, e embeda depois do commit, como o `ingest.ts` já faz.

### (d) Um episódio produz N chunks, não 1

Frontmatter + compiled + timeline. `p2_verdict.chunk_id` singular no §2 deste spec
está errado: aponta para o chunk `compiled` (o único que passa o gate), e a
invariante reversa audita por `source_file`, não por `chunk_id`.

### (e) Re-ingest apaga e o trigger cascateia

`ingestEntityFile` faz `DELETE FROM chunks WHERE source_file = ?` para ser
idempotente — e `trg_chunks_delete_cascade` limpa os vetores. Isso dá
idempotência de graça, mas deixaria `p2_verdict.chunk_id` pendurado. O
`p2_verdict` é keyed por `episode_id`, então re-ingest do mesmo episódio tem de
**re-apontar** o `chunk_id` na mesma transação, não inserir linha nova.

## 10. O que isto muda no que já está registrado

| | |
|---|---|
| Afirmação de que o chunk carrega `importance = 0.90` via `inferImportance` | **falsa**; o 0,90 vem do `Math.max` do compiled, e só nele |
| `pain` = severidade adjudicada | **não é o que o ingest escreve**; exige override explícito |
| `chunk_type` do chunk escrito | será `"other"`, nunca `"lesson"` |
| Alcance / `w_min` / salience em `serving_model.py` | **inalterados** — o modelo passa `importance` e `retention_days` explícitos, e ambos conferem com o medido (0,90 no compiled, 180 d) |

Ou seja: a matemática de salience sobrevive; o que não sobrevive é a descrição de
**como** o chunk chega a ela. As duas primeiras linhas entram na emenda v1.12,
junto com a decisão de dose absoluta vs relativa.
