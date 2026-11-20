# Field recount for the note, 2026-11-20

Read-only recount of the two field figures in section 6 of `NOTE.md` that came from queries on the
production host, so that each has a source in this repository. Run by the author on 2026-11-20 at
21:48 UTC. Only counts were printed; no query text, reply or transcript content was read out.

## Agent transcripts after the deployment

Command, run in the agents' transcript root on the production host (`<agent-transcripts>`):

```sh
python3 - <<'PY'
import json, collections, os, datetime
cut = datetime.datetime(2026, 11, 8, 17, 45, tzinfo=datetime.timezone.utc).timestamp()
files = [os.path.join(r, f) for r, _, fs in os.walk('.') for f in fs
         if f.endswith('.jsonl') and os.path.getmtime(os.path.join(r, f)) > cut]
print('files_after_deploy', len(files))
c, per = collections.Counter(), collections.Counter()
for f in files:
    for line in open(f, errors='replace'):
        try: o = json.loads(line)
        except Exception: continue
        m = o.get('message') or {}
        cont = m.get('content') if isinstance(m, dict) else None
        if not isinstance(cont, list): continue
        for b in cont:
            if isinstance(b, dict) and b.get('type') == 'tool_use' \
                    and str(b.get('name', '')).startswith('mcp__nox-mem__'):
                c[b['name']] += 1; per[f.split('/')[1]] += 1
print('tool_counts', dict(c)); print('per_project_dir', dict(per))
PY
```

Output:

```
files_after_deploy 83
tool_counts {'mcp__nox-mem__nox_mem_search': 13, 'mcp__nox-mem__nox_mem_get': 1}
per_project_dir {'-root--openclaw-workspace-agents-lex': 14}
```

13 search calls and 1 full-text read, all from one agent (`lex`), whose weekly deadline sweep was
switched off on 2026-11-17 (openclaw-vps PR #89). The first count, on 2026-11-17, found the same 13
and 1 in 65 files; the 18 more files now are transcripts modified in the three days since, and none
of them adds a memory call.

## Server telemetry, MCP searches by caller

```sql
SELECT requesting_agent, COUNT(*) FROM search_telemetry
WHERE ts >= '2026-10-18' AND ts < '2026-11-18' GROUP BY 1;
```

Output (`sqlite3 -readonly` on `$NOX_DB_PATH`):

```
answer:unknown|3
cli:unknown|19
mcp:unknown|109
probe:diag-fts-26out|5
probe:kg-corpus-scope|110
probe:probe-reativacao|6
probe:semantic-canary|1490
```

109 MCP searches with an unknown caller. The draft of 2026-11-17 printed 108 from the same query
without the upper bound, run that afternoon: the last three `mcp:unknown` rows are at 14:32, 16:07
and 16:12 UTC on 2026-11-17, and none came after, so the first reading fell between the last two.
The bounded window gives the same 109 whenever it is run.
